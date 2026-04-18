import ctypes
import os
import socket
import subprocess
import sys
import tempfile
import threading
from typing import Optional

from PySide6.QtCore import Qt, Signal, QObject, QPoint
from PySide6.QtGui import QCursor, QFont, QTextCursor
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QTextBrowser, QTextEdit,
                               QLineEdit, QFrame, QMessageBox)

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from locales import DEFAULT_LOCALES


def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()
IPC_PORT = 14514
API_KEY_FILE = os.path.join(APP_DIR, "api_key.txt")
md = None

# --- 现代 QSS 样式表配置 ---
STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI";
    font-size: 10pt;
    color: #222222;
}
#MainFrame {
    background-color: #fcfcfc;
    border-radius: 8px;
    border: 1px solid #dcdcdc;
}
#TopBar {
    background-color: transparent;
}
#PathLabel {
    color: #777777;
    font-size: 9pt;
}
#CloseBtn {
    color: #ff4d4d;
    font-size: 14pt;
    font-weight: bold;
    background: transparent;
    border: none;
}
#CloseBtn:hover {
    color: white;
    background-color: #ff4d4d;
    border-radius: 4px;
}
QTextBrowser {
    background-color: #f5f5f5;
    border: none;
    border-radius: 6px;
    padding: 8px;
}
#CmdPanel {
    background-color: #e0f0ff;
    border: 1px solid #b3d7ff;
    border-radius: 6px;
}
#CmdHeader {
    font-weight: bold;
    color: #0056b3;
}
#RunBtn {
    background-color: #0078D7;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 12px;
    font-weight: bold;
}
#RunBtn:hover {
    background-color: #005a9e;
}
#CodeArea {
    background-color: #1e1e1e;
    color: #569cd6;
    font-family: "Consolas";
    font-size: 10pt;
    border: none;
    border-radius: 4px;
    padding: 8px;
}
QLineEdit {
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 6px;
    background-color: white;
}
QLineEdit:focus {
    border: 1px solid #0078D7;
}
#SetupBtn {
    background-color: #0078D7;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 20px;
    font-weight: bold;
}
#SetupBtn:hover {
    background-color: #005a9e;
}
"""


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


class AppSignals(QObject):
    log = Signal(str, str)
    response = Signal(object)
    new_path = Signal(str)


class Gemini:
    def __init__(self, files, log_callback):
        self.log_callback = log_callback
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
        response = self.generate_content(contents=contents)
        while any(part.function_call for part in response.candidates[0].content.parts):
            function_responses = []
            for part in response.candidates[0].content.parts:
                if tool_call := part.function_call:
                    self.log_callback(f"Function to call: {tool_call.name}", "gray")
                    self.log_callback(f"Arguments: {tool_call.args}", "gray")

                    if tool_call.name == "list_dir":
                        result = tool_list_dir(**tool_call.args)
                    elif tool_call.name == "read_file":
                        result = tool_read_file(**tool_call.args)
                    else:
                        result = t("unknown_function")

                    res_str = str(result)
                    self.log_callback(f"Function execution result: {res_str[:100]}...", "gray")
                    function_responses.append(
                        types.Part.from_function_response(name=str(tool_call.name), response={"result": res_str})
                    )
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=function_responses))
            response = self.generate_content(contents=contents)

        contents.append(response.candidates[0].content)
        return Response.model_validate_json(response.text)


def fake_call(result, agr, name, content):
    content.append(types.Content(role="model", parts=[types.Part(
        function_call=types.FunctionCall(name=name, args=agr),
        thought_signature=b"context_engineering_is_the_way_to_go"
    )]))
    function_response_part = types.Part.from_function_response(name=name, response={"result": str(result)})
    content.append(types.Content(role="user", parts=[function_response_part]))


# --- PySide6 Setup Window (Menu Manager) ---
class SetupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(500, 100)
        self.drag_pos = None

        main_frame = QFrame(self)
        main_frame.setObjectName("MainFrame")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(main_frame)

        frame_layout = QHBoxLayout(main_frame)
        frame_layout.setContentsMargins(20, 10, 20, 10)

        lbl_hint = QLabel(t("start_hint"))
        lbl_hint.setObjectName("PathLabel")
        frame_layout.addWidget(lbl_hint)

        frame_layout.addStretch()

        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("SetupBtn")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_menu)
        frame_layout.addWidget(self.btn_toggle)

        btn_close = QPushButton(" × ")
        btn_close.setObjectName("CloseBtn")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        frame_layout.addWidget(btn_close)

        self.update_btn_state()

        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def get_targets(self):
        exe_path = os.path.abspath(sys.argv[0])
        return [
            (r"Software\Classes\*\shell\AIAssistant", "%1", exe_path),
            (r"Software\Classes\Directory\shell\AIAssistant", "%1", exe_path),
            (r"Software\Classes\Directory\Background\shell\AIAssistant", "%V", exe_path)
        ]

    def check_installed(self):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.get_targets()[0][0]):
                return True
        except FileNotFoundError:
            return False

    def update_btn_state(self):
        self.btn_toggle.setText(t("btn_rm") if self.check_installed() else t("btn_add"))

    def toggle_menu(self):
        import winreg
        installed = self.check_installed()
        try:
            for base_path, arg, exe_path in self.get_targets():
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
            self.update_btn_state()
            QMessageBox.information(self, t("title_success"), t("msg_success"))
        except Exception as e:
            QMessageBox.critical(self, t("title_error"), f"{t('msg_fail')}{e}")


# --- PySide6 Main Window (AI Assistant UI) ---
class AgentGUI(QWidget):
    def __init__(self, target_paths):
        super().__init__()
        self.target_paths = target_paths
        self.chat_history = []
        self.gemini = None
        self.drag_pos = None

        self.signals = AppSignals()
        self.signals.log.connect(self.append_log)
        self.signals.response.connect(self.handle_ai_response)
        self.signals.new_path.connect(self.add_path)

        self.setup_ui()
        self.position_window()

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")
        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(10)
        layout.addWidget(self.main_frame)

        # 1. 顶部栏
        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        path_text = " | ".join([os.path.basename(p) for p in self.target_paths])
        self.lbl_paths = QLabel(path_text)
        self.lbl_paths.setObjectName("PathLabel")
        top_layout.addWidget(self.lbl_paths)
        top_layout.addStretch()

        self.btn_close = QPushButton(" × ")
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(top_bar)

        # 2. 扩展区 (初始隐藏)
        self.expand_widget = QWidget()
        expand_layout = QVBoxLayout(self.expand_widget)
        expand_layout.setContentsMargins(0, 0, 0, 0)
        expand_layout.setSpacing(10)

        self.txt_log = QTextBrowser()
        self.txt_log.setOpenExternalLinks(False)
        expand_layout.addWidget(self.txt_log)

        self.cmd_panel = QFrame()
        self.cmd_panel.setObjectName("CmdPanel")
        cmd_layout = QVBoxLayout(self.cmd_panel)
        cmd_layout.setContentsMargins(10, 10, 10, 10)

        cmd_header_widget = QWidget()
        cmd_header_layout = QHBoxLayout(cmd_header_widget)
        cmd_header_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_cmd_type = QLabel()
        self.lbl_cmd_type.setObjectName("CmdHeader")
        cmd_header_layout.addWidget(self.lbl_cmd_type)
        cmd_header_layout.addStretch()

        self.btn_run = QPushButton(t("btn_run"))
        self.btn_run.setObjectName("RunBtn")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        cmd_header_layout.addWidget(self.btn_run)

        cmd_layout.addWidget(cmd_header_widget)

        self.txt_cmd = QTextEdit()
        self.txt_cmd.setObjectName("CodeArea")
        self.txt_cmd.setFixedHeight(120)
        cmd_layout.addWidget(self.txt_cmd)

        self.cmd_panel.hide()
        expand_layout.addWidget(self.cmd_panel)

        self.expand_widget.hide()
        main_layout.addWidget(self.expand_widget)

        # 3. 输入区
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter command...")
        self.entry.returnPressed.connect(self.on_enter)
        main_layout.addWidget(self.entry)

    def position_window(self):
        cursor_pos = QCursor.pos()
        pos_x = cursor_pos.x() + 10
        pos_y = cursor_pos.y() + 10
        screen = QApplication.screenAt(cursor_pos)
        if screen:
            screen_geom = screen.availableGeometry()
            if pos_x + 600 > screen_geom.right(): pos_x = screen_geom.right() - 610
            if pos_y + 70 > screen_geom.bottom(): pos_y = screen_geom.bottom() - 80
        self.move(pos_x, pos_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def add_path(self, new_path):
        if new_path not in self.target_paths:
            self.target_paths.append(new_path)
            path_text = " | ".join([os.path.basename(p) for p in self.target_paths])
            self.lbl_paths.setText(path_text)

    def init_context(self):
        readable_exts = ('.txt', '.csv', '.md', '.py', '.json', '.log', '.ini', '.bat',
                         '.docx', '.xlsx', '.xls', '.doc', '.pptx', '.pdf')
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

    def append_log(self, msg, tag=None):
        msg = msg.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        if tag == "you":
            self.txt_log.append(f'<b style="color:#222222;">{t("you")}</b><br>{msg}<br>')
        elif tag == "ai":
            self.txt_log.append(f'<b style="color:#222222;">{t("ai_explains")}</b><br>{msg}<br>')
        elif tag == "exec":
            self.txt_log.append(f'<span style="color:#0078D7;">{msg}</span><br>')
        elif tag == "error":
            self.txt_log.append(f'<span style="color:#ff4d4d;">{msg}</span><br>')
        elif tag == "gray":
            self.txt_log.append(f'<span style="color:#777777;">{msg}</span><br>')
        else:
            self.txt_log.append(f'<span>{msg}</span><br>')
        self.txt_log.moveCursor(QTextCursor.End)

    def on_enter(self):
        user_input = self.entry.text().strip()
        if not user_input: return

        if self.expand_widget.isHidden():
            self.expand_widget.show()
            self.resize(600, 500)

        self.entry.clear()
        self.cmd_panel.hide()
        self.append_log(user_input, tag="you")
        self.chat_history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
        if len(self.chat_history) == 1:
            self.init_context()

        threading.Thread(target=self.process_ai_loop, daemon=True).start()

    def process_ai_loop(self):
        self.signals.log.emit(t("ai_thinking"), None)
        if self.gemini is None:
            self.gemini = Gemini(self.target_paths, lambda m, t: self.signals.log.emit(m, t))
        try:
            response_obj = self.gemini.call(self.chat_history)
            self.signals.response.emit(response_obj)
        except Exception as e:
            self.signals.log.emit(f"API Error: {e}", "error")

    def handle_ai_response(self, response: Response):
        desc, code, lang_type = response.description, response.code, response.lang
        if desc:
            self.append_log(desc, tag="ai")
        if code and lang_type:
            self.cmd_panel.show()
            self.lbl_cmd_type.setText(f"{t('pending_cmd')} ({lang_type}):")
            self.txt_cmd.setPlainText(code)
            try:
                self.btn_run.clicked.disconnect()
            except RuntimeError:
                pass
            self.btn_run.clicked.connect(lambda: self.execute_code(self.txt_cmd.toPlainText().strip(), lang_type))

    def execute_code(self, code, lang_type):
        try:
            if lang_type and lang_type.lower() == "python":
                fd, temp_path = tempfile.mkstemp(suffix=".py")
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(code + "\n\nimport os\nos.system('pause')")
                subprocess.Popen(["python", temp_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.append_log(t("py_done"), tag="exec")
            else:
                fd, temp_path = tempfile.mkstemp(suffix=".ps1")
                with os.fdopen(fd, 'w', encoding='utf-8-sig') as f:
                    f.write(code + "\n\nRead-Host -Prompt 'Press Enter to exit...'")
                subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.append_log(t("ps_done"), tag="exec")
        except Exception as e:
            QMessageBox.critical(self, t("exec_err"), str(e))


def ipc_server_thread(signals: AppSignals):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
        _s.bind(('127.0.0.1', IPC_PORT))
        _s.listen()
        while True:
            conn, addr = _s.accept()
            with conn:
                data = conn.recv(4096)
                if data:
                    path = data.decode('utf-8')
                    signals.new_path.emit(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

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

        gui = AgentGUI(sys.argv[1:])
        threading.Thread(target=ipc_server_thread, args=(gui.signals,), daemon=True).start()
        gui.show()
    else:
        setup_gui = SetupWindow()
        setup_gui.show()

    sys.exit(app.exec())