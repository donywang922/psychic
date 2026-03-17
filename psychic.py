import ctypes
import os
import socket
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from locales import DEFAULT_LOCALES

def get_app_dir():
    """获取程序的真实所在目录（完美兼容 PyInstaller 单文件打包和 py 源码运行）"""
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包后的 exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是直接运行的 .py 脚本
        return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

# --- 1. 全局配置与默认文件生成 ---
IPC_PORT = 14514

# 将相对路径强行绑定到程序所在的绝对路径上
API_KEY_FILE = os.path.join(APP_DIR, "api_key.txt")

style_config = {
    "bg_main": "#fcfcfc",  # 纯净主背景
    "bg_textarea": "#f5f5f5",  # 灰色文本域
    "bg_cmd": "#e0f0ff",  # 蓝色指令板块
    "fg_main": "#222222",  # 主要文字
    "fg_gray": "#777777",  # 引用路径文字
    "primary": "#0078D7",  # 主题色（发送、运行按钮）
    "border_input": "#cccccc",  # 输入框边框
    "font_main": ("Microsoft YaHei", 10),
    "font_bold": ("Microsoft YaHei", 10, "bold"),
    "font_cmd": ("Consolas", 9),
    "padx": 15,
    "pady": 10
}
md = None


# --- 2. 语言管理器 ---
def is_zh_os():
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return (lang_id & 0x03FF) == 0x04
    except:
        return False


class LangManager:
    def __init__(self, locales):
        self.locales = locales
        self.current_lang = "zh" if is_zh_os() else "en"
        if self.current_lang not in self.locales:
            self.current_lang = "en"

    def get(self, key, **kwargs):
        text: str = self.locales.get(self.current_lang, {}).get(key, f"[{key}]")
        if kwargs:
            text = text.format(**kwargs)
        return text


def load_environment():
    if not os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            f.write("YOUR_GEMINI_API_KEY_HERE")
    with open(API_KEY_FILE, "r", encoding="utf-8") as f:
        key = f.read().strip()
    return key


lang = LangManager(DEFAULT_LOCALES)
t = lang.get


class Response(BaseModel):
    lang: Optional[str] = Field(description=t('command_lang'))
    code: Optional[str] = Field(description=t('command_code'))
    description: Optional[str] = Field(description=t('command_description'))


class Explain(BaseModel):
    text: str = Field(description=t('explain_text'))


list_dir = types.FunctionDeclaration(name="list_dir", description=t('list_dir_desc'),
                                     parameters=types.Schema(type=types.Type.OBJECT, properties={
                                         "path": types.Schema(type=types.Type.STRING,
                                                              description=t('list_dir_path_desc')),
                                     }))


def tool_list_dir(path):
    try:
        return os.listdir(path)[:50]
    except Exception as e:
        return e


read_file = types.FunctionDeclaration(name="read_file", description=t('read_file_desc'),
                                      parameters=types.Schema(type=types.Type.OBJECT, properties={
                                          "path": types.Schema(type=types.Type.STRING,
                                                               description=t('read_file_path_desc')),
                                      }))


def tool_read_file(path):
    global md
    ext = path.lower()
    content = ""
    try:
        # 1. 常规文本格式处理
        if ext.endswith(('.txt', '.csv', '.md', '.py', '.json', '.log', '.ini', '.bat')):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(2000)

        elif ext.endswith(('.docx', '.xlsx', '.xls', '.doc', '.pptx', '.pdf')):
            if md is None:
                from markitdown import MarkItDown
                md = MarkItDown()
            result = md.convert(path)
            content = result.text_content[:2000]
        return content
    except Exception as e:
        return e


class Gemini:
    def __init__(self, files, logger):
        self.logger = logger
        current_key = load_environment()
        self.model_name = "gemini-3.1-flash-lite-preview"

        if "|" in current_key:
            parts = current_key.split("|")
            current_key = parts[0].strip()
            self.model_name = parts[1].strip()

        self.gemini = genai.Client(api_key=current_key)
        tools = types.Tool(function_declarations=[list_dir, read_file])
        self.config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=t("sys_prompt", files=files),
            response_json_schema=Response.model_json_schema()
        )

    def generate_content(self, contents):
        return self.gemini.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=self.config,
        )

    def call(self, contents):
        # return Response(lang='powershell', code='echo "1"', description='123')
        response = self.generate_content(contents=contents)

        # 【修复1】使用 any() 检查 response 的所有 parts 中是否包含任意一个 function_call
        while any(part.function_call for part in response.candidates[0].content.parts):
            function_responses = []

            # 遍历所有的 parts，完美处理模型的并发调用 (Parallel Tool Calling)
            for part in response.candidates[0].content.parts:
                if tool_call := part.function_call:
                    self.logger(f"Function to call: {tool_call.name}", tag="gray")
                    self.logger(f"Arguments: {tool_call.args}", tag="gray")

                    if tool_call.name == "list_dir":
                        result = tool_list_dir(**tool_call.args)
                    elif tool_call.name == "read_file":
                        result = tool_read_file(**tool_call.args)
                    else:
                        result = t("unknown_function")

                    # 【修复2】强制将结果转为字符串！防止 Exception 对象导致 JSON 序列化丢失，让 AI 变成瞎子
                    res_str = str(result)
                    self.logger(f"Function execution result: {res_str[:100]}...", tag="gray")

                    function_responses.append(
                        types.Part.from_function_response(
                            name=str(tool_call.name),
                            response={"result": res_str},
                        )
                    )

            # 将 AI 的所有并发调用请求打包进历史
            contents.append(response.candidates[0].content)
            # 将所有的工具执行结果打包成一个完整的 User 回合返回给 AI
            contents.append(types.Content(role="user", parts=function_responses))

            # 带着结果再次请求大模型
            response = self.generate_content(contents=contents)

        # 循环结束，确信模型已经给出了最终的 JSON 文本回复
        contents.append(response.candidates[0].content)
        return Response.model_validate_json(response.text)


def fake_call(result, agr, name, content):
    content.append(types.Content(role="model", parts=[types.Part(
        function_call=types.FunctionCall(name=name, args=agr),
        thought_signature=b"context_engineering_is_the_way_to_go"
    )]))
    function_response_part = types.Part.from_function_response(
        name=name,
        response={"result": str(result)},
    )
    content.append(types.Content(role="user", parts=[function_response_part]))


def manage_context_menu(root):
    import winreg
    exe_path = os.path.abspath(sys.argv[0])

    targets = [
        (r"Software\Classes\*\shell\AIAssistant", "%1"),
        (r"Software\Classes\Directory\shell\AIAssistant", "%1"),
        (r"Software\Classes\Directory\Background\shell\AIAssistant", "%V")
    ]

    def check_installed():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, targets[0][0]):
                return True
        except FileNotFoundError:
            return False

    def toggle_menu():

        installed = check_installed()
        try:
            for base_path, arg in targets:
                if installed:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base_path + r"\command")
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base_path)
                else:
                    command_string = f'"{exe_path}" "{arg}"'
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_path) as key:
                        winreg.SetValue(key, "", winreg.REG_SZ, t("menu_name"))
                        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,43")
                        with winreg.CreateKey(key, "command") as cmd_key:
                            winreg.SetValue(cmd_key, "", winreg.REG_SZ, command_string)

            new_state = check_installed()
            btn_toggle.config(text=t("btn_rm") if new_state else t("btn_add"))
            messagebox.showinfo(t("title_success"), t("msg_success"))
        except Exception as e:
            messagebox.showerror(t("title_error"), f"{t('msg_fail')}{e}")

    root.geometry("600x100")  # 初始高度
    root.title(t("setup_title"))
    root.configure(bg=style_config["bg_main"])  # 确保根窗口背景色统一

    # 1. 创建一个横向的容器 Frame，并用 padx 和 pady 留出舒适的边缘呼吸感
    container = tk.Frame(root, bg=style_config["bg_main"])
    container.pack(fill='both', expand=True, padx=40, pady=30)

    # 2. 左侧的提示文字 (这里为了直观暂时写死，建议后续将 "start_hint" 加入 locales.json)
    lbl_hint = tk.Label(container, text=t("start_hint"),
                        font=style_config["font_main"],
                        fg=style_config["fg_gray"],  # 使用灰色字体显得更高级
                        bg=style_config["bg_main"])
    lbl_hint.pack(side='left', anchor="w")  # anchor="w" 保证靠西(左)对齐

    # 3. 右侧的切换按钮
    btn_toggle = tk.Button(container, text=t("btn_rm") if check_installed() else t("btn_add"),
                           bg=style_config["primary"], fg="white",
                           font=style_config["font_bold"],
                           relief="flat", activebackground="#218838", cursor="hand2",
                           command=toggle_menu,
                           padx=20, pady=6)  # 增加内部边距，让扁平按钮更大气
    btn_toggle.pack(side='right', anchor="e")  # anchor="e" 保证靠东(右)对齐


# --- 3. 极致扁平化美化的 UI 类 ---
class AgentGUI:
    def __init__(self, root, target_paths):
        self.gemini = None
        self.y = 0
        self.x = 0
        self.txt_log = None
        self.input_frame = None
        self.entry = None
        self.expand_frame = None
        self.cmd_panel = None
        self.lbl_paths: tk.Label | None = None
        self.main_container = None
        self.btn_close = None
        self.root = root
        self.target_paths = target_paths
        self.chat_history = []

        self.setup_ui()

    def setup_ui(self):
        # 初始化窗口：横条形，置顶，去除原生边框 (overrideredirect)
        self.root.overrideredirect(True)
        # 1. 获取预设的宽和高
        w, h = 600, 70

        # 2. 获取当前鼠标的全局物理坐标
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()

        # 3. 稍微给个偏移量，防止窗口直接挡住鼠标指针（向右下角偏移 10 像素）
        pos_x = mouse_x + 10
        pos_y = mouse_y + 10

        # 可选进阶：防止窗口超出屏幕右侧或下侧边界被遮挡
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if pos_x + w > screen_width:
            pos_x = screen_width - w - 10
        if pos_y + h > screen_height:
            pos_y = screen_height - h - 50  # 底部留出任务栏空间

        # 4. 组合成 Tkinter 要求的格式: "宽x高+X轴坐标+Y轴坐标"
        self.root.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=style_config["bg_main"])

        # 全局最外层 Padding 容器
        self.main_container = tk.Frame(self.root, bg=style_config["bg_main"])
        self.main_container.pack(fill='both', expand=True, padx=5, pady=5)

        # 1. 顶部栏 (文件引用 + 关闭按钮)
        top_bar = tk.Frame(self.main_container, bg=style_config["bg_main"])
        top_bar.pack(fill='x')

        path_text = " | ".join([os.path.basename(p) for p in self.target_paths])
        self.lbl_paths = tk.Label(top_bar, text=f"{path_text}",
                                  font=style_config["font_main"],
                                  fg=style_config["fg_gray"],
                                  bg=style_config["bg_main"], anchor="w")
        self.lbl_paths.pack(side='left', fill='x', expand=True)

        top_bar.bind("<ButtonPress-1>", self.start_drag)
        top_bar.bind("<B1-Motion>", self.do_drag)
        self.lbl_paths.bind("<ButtonPress-1>", self.start_drag)
        self.lbl_paths.bind("<B1-Motion>", self.do_drag)

        # 扁平化关闭按钮 (鼠标悬停变红)
        self.btn_close = tk.Label(top_bar, text=" × ", font=("Arial", 14, "bold"),
                                  bg=style_config["bg_main"], fg="#ff4d4d", cursor="hand2")
        self.btn_close.pack(side='right')
        self.btn_close.bind("<Button-1>", lambda e: self.root.destroy())
        self.btn_close.bind("<Enter>", lambda e: self.btn_close.config(bg="#ff4d4d", fg="white"))
        self.btn_close.bind("<Leave>", lambda e: self.btn_close.config(bg=style_config["bg_main"], fg="#ff4d4d"))

        # 2. 动态扩展区 (日志 + 指令板块，初始隐藏)
        self.expand_frame = tk.Frame(self.main_container, bg=style_config["bg_main"])

        # 日志区：彻底扁平化，灰色背景
        self.txt_log = scrolledtext.ScrolledText(self.expand_frame, height=12, state='disabled',
                                                 font=style_config["font_main"],
                                                 bg=style_config["bg_textarea"],
                                                 fg=style_config["fg_main"],
                                                 relief="flat", highlightthickness=0)
        self.txt_log.pack(fill='both', expand=True, pady=(style_config["pady"], 0))
        # 定义日志内的富文本样式 (加粗，蓝色执行，红色错误)
        self.txt_log.tag_config("bold", font=style_config["font_bold"])
        self.txt_log.tag_config("exec", foreground="#0078D7")
        self.txt_log.tag_config("error", foreground="#ff4d4d")

        # 指令区板块 (蓝色扁平板块)
        self.cmd_panel = tk.Frame(self.expand_frame, bg=style_config["bg_cmd"],
                                  relief="solid", borderwidth=1)
        self.cmd_panel.configure(highlightbackground=style_config["border_input"])  # 细边框
        self.cmd_panel.pack(fill='x', pady=(style_config["pady"], 0))
        self.cmd_panel.pack_forget()  # 初始隐藏

        # 3. 底部输入区
        self.input_frame = tk.Frame(self.main_container, bg=style_config["bg_main"])
        self.input_frame.pack(fill='x', side='bottom')

        # 输入框：单色灰色边框，扁平 relief
        self.entry = tk.Entry(self.input_frame, font=style_config["font_main"],
                              relief="solid", borderwidth=1,
                              highlightthickness=1, highlightcolor=style_config["primary"],
                              highlightbackground=style_config["border_input"])
        self.entry.pack(side="left", fill='x', expand=True, ipady=3)  # ipady 增加内部高度
        self.entry.bind("<Return>", lambda e: self.on_enter())
        self.entry.focus()

    # --- 窗口拖拽实现 ---
    def start_drag(self, event):
        self.x, self.y = event.x, event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def add_path(self, new_path):
        if new_path not in self.target_paths:
            self.target_paths.append(new_path)
            if self.lbl_paths:
                path_text = " | ".join([os.path.basename(p) for p in self.target_paths])
                self.lbl_paths.config(text=path_text)

    def init_context(self):
        readable_exts = ('.txt', '.csv', '.md', '.py', '.json', '.log', '.ini', '.bat',
                         '.docx', '.xlsx', '.xls', '.doc', '.pptx', '.pdf')

        # --- 情景 1：只选中了一个目标，且它是文件夹 ---
        if len(self.target_paths) == 1 and os.path.isdir(self.target_paths[0]):
            folder_path = self.target_paths[0]
            items = tool_list_dir(folder_path)
            fake_call(items, {'path': folder_path}, 'list_dir', self.chat_history)
            if not isinstance(items, Exception):
                text_files = [f for f in items if isinstance(f, str) and f.lower().endswith(readable_exts)]
                if len(text_files) == 1:
                    file_path = os.path.join(folder_path, text_files[0])
                    content = tool_read_file(file_path)
                    fake_call(content, {'path': file_path}, 'read_file', self.chat_history)

        else:
            text_files = [f for f in self.target_paths if isinstance(f, str) and f.lower().endswith(readable_exts)]
            if len(text_files) == 1:
                content = tool_read_file(text_files[0])
                fake_call(content, {'path': text_files}, 'read_file', self.chat_history)

    def expand_window(self):
        """规则 9: 回车后窗口平滑展开"""
        if not self.expand_frame.winfo_ismapped():
            self.root.geometry("600x500")  # 最终高度
            self.expand_frame.pack(fill='both', expand=True, before=self.input_frame)

    def log_msg(self, msg, tag: str | None = None):
        print(f"[{tag or 'LOG'}] {msg}")
        self.txt_log.config(state='normal')
        if tag == "you":
            self.txt_log.insert(tk.END, t("you"), "bold")
            self.txt_log.insert(tk.END, msg + "\n\n")
        elif tag == "ai":
            self.txt_log.insert(tk.END, t("ai_explains"), "bold")
            self.txt_log.insert(tk.END, msg + "\n\n")
        else:
            current_tag: str | None = tag if tag in ["exec", "error", "gray"] else None
            self.txt_log.insert(tk.END, msg + "\n\n", current_tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def clear_cmd_panel(self):
        self.cmd_panel.pack_forget()
        for widget in self.cmd_panel.winfo_children(): widget.destroy()

    def on_enter(self):
        user_input = self.entry.get().strip()
        if not user_input: return
        self.expand_window()
        self.entry.delete(0, tk.END)
        self.clear_cmd_panel()
        self.log_msg(user_input, tag="you")
        self.chat_history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
        if len(self.chat_history) == 1:
            self.init_context()
        threading.Thread(target=self.process_ai_loop, daemon=True).start()

    def process_ai_loop(self):
        self.log_msg(t("ai_thinking"))
        if self.gemini is None:
            self.gemini = Gemini(self.target_paths, self.log_msg)
        try:
            response_str = self.gemini.call(self.chat_history)
            self.root.after(0, self.handle_ai_response, response_str)
        except Exception as e:
            self.root.after(0, self.log_msg, f"API Error: {e}")

    def handle_ai_response(self, response: Response):
        desc, code, lang_type = response.description, response.code, response.lang
        if desc: self.log_msg(desc, tag="ai")

        if code or lang_type:
            self.cmd_panel.pack(fill=tk.X, pady=style_config["pady"])

            # 1. 创建一个顶部标题栏容器
            header_frame = tk.Frame(self.cmd_panel, bg=style_config["bg_cmd"])
            header_frame.pack(fill='x', padx=5, pady=(5, 0))

            # 2. 标签放左边
            if lang_type:
                lbl = tk.Label(header_frame, text=f"{t('pending_cmd')} ({lang_type}):",
                               bg=style_config["bg_cmd"], font=style_config["font_bold"])
                lbl.pack(side='left')

            # 3. 按钮放右边 (和标签在同一行)
            if code:
                btn_run = tk.Button(header_frame, text=t("btn_run"),
                                    bg=style_config["primary"], fg="white",
                                    font=style_config["font_bold"],
                                    relief="flat", activebackground="#218838", cursor="hand2")
                btn_run.pack(side='right')

                # 4. 代码框放在最下面
                txt_cmd = scrolledtext.ScrolledText(self.cmd_panel, height=6,
                                                    font=style_config["font_cmd"],
                                                    bg="#1e1e1e", fg="#569cd6",  # 代码配色
                                                    relief="flat", borderwidth=0)
                txt_cmd.insert(tk.END, code)
                txt_cmd.pack(fill='x', padx=5, pady=5)

                btn_run.config(command=lambda: self.execute_code(txt_cmd.get("1.0", tk.END).strip(), lang_type))

    def execute_code(self, code, lang_type):
        try:
            if lang_type.lower() == "python":
                # 创建一个安全的临时 Python 文件
                fd, temp_path = tempfile.mkstemp(suffix=".py")
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    # 注入代码，并在末尾加上暂停，防止执行完控制台秒退
                    f.write(code + "\n\nimport os\nos.system('pause')")

                # 0x00000010 是 Windows 的 CREATE_NEW_CONSOLE 标志位
                subprocess.Popen(["python", temp_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.log_msg(t("py_done"), tag="exec")

            else:
                # 创建一个安全的临时 PowerShell 文件
                fd, temp_path = tempfile.mkstemp(suffix=".ps1")
                # 注意：PowerShell 脚本最好使用 utf-8-sig (BOM) 防止中文乱码
                with os.fdopen(fd, 'w', encoding='utf-8-sig') as f:
                    f.write(code + "\n\nRead-Host -Prompt '按回车键退出...'")

                subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.log_msg(t("ps_done"), tag="exec")

        except Exception as e:
            messagebox.showerror(t("exec_err"), str(e))


def ipc_server_thread(app):
    """后台监听线程，接收其他选中的文件路径"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
        _s.bind(('127.0.0.1', IPC_PORT))
        _s.listen()
        while True:
            conn, addr = _s.accept()
            with conn:
                data = conn.recv(4096)
                if data:
                    path = data.decode('utf-8')
                    app.root.after(0, app.add_path, path)


# --- 5. 路由入口 ---
if __name__ == "__main__":
    _root = tk.Tk()
    if len(sys.argv) > 1:
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.bind(('127.0.0.1', IPC_PORT))
            test_sock.close()
            is_primary = True
        except OSError:
            is_primary = False

        if not is_primary:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', IPC_PORT))
                s.sendall(sys.argv[1].encode('utf-8'))
            sys.exit(0)
        _app = AgentGUI(_root, sys.argv[1:])
        threading.Thread(target=ipc_server_thread, args=(_app,), daemon=True).start()
    else:
        manage_context_menu(_root)
    _root.mainloop()
