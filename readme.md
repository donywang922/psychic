# psychic · 通灵

AI泔水（划掉

一个从 Windows 右键菜单打开的 DeepSeek 聊天框。

选中文件或文件夹，右键打开 psychic，输入问题；需要批量处理文件时，可以查看 AI 生成的 PowerShell / Python 脚本，再点击运行。

**项目目标：轻量、快速打开、按需运行，关闭聊天窗口后退出，不需要后台常驻。**

## 功能与边界

* 支持文件、文件夹、文件夹空白处的右键入口。
* 使用 DeepSeek API，默认模型为 `deepseek-flash`，关闭思考模式。
* 支持窗口内连续对话，以及列出目录、读取文件内容的工具调用。
* 脚本展示在可编辑区域，点击“运行”后在独立终端执行。
* 启动时只创建基础界面；API 依赖、文件读取和完整聊天界面按需加载。

当前使用传统右键菜单注册方式。在 Windows 11 中，请到 **“显示更多选项”** 中查找 psychic；尚未接入新版右键菜单第一层。

## 快速开始：使用打包版

运行环境：**Windows 11 x64**。打包版无需额外安装 Python即可聊天；运行 AI 生成的 Python 脚本仍需要系统能找到 `python` 命令。

1. 将整个程序目录放到固定位置，不要单独移动 exe。
2. 在 `psychic.exe` 同目录创建 `api\_key.txt`，填入自己的 DeepSeek API 密钥。
3. 双击 `psychic.exe`，在管理窗口点击“添加右键菜单”。
4. 在资源管理器里右键文件或文件夹，通过 psychic 打开聊天框。
5. 输入问题并按 Enter 发送。

本项目的打包输出结构：

```text
dist/deepseek/psychic/
├── psychic.exe
├── \_internal/       # 运行依赖，必须保留
└── api\_key.txt      # 本机配置，打包后单独放置
```

无参数启动 exe 会打开菜单管理窗口；传入路径则直接打开聊天框：

```powershell
.\\dist\\deepseek\\psychic\\psychic.exe "D:\\示例文件夹"
```

## DeepSeek 配置

### 密钥文件

源码运行时，将 `api\_key.txt` 放在 `psychic.py` 同目录；打包运行时放在 exe 同目录。

文件内容为一行，不加引号：

```text
YOUR\_DEEPSEEK\_API\_KEY\_HERE
```

请将占位符替换为真实密钥。也可以指定模型：

```text
YOUR\_DEEPSEEK\_API\_KEY\_HERE|deepseek-flash
```

原 Gemini API 密钥不能用于 DeepSeek。密钥获取和 API 说明见 [DeepSeek 开放平台](https://platform.deepseek.com/) 与 [官方文档](https://api-docs.deepseek.com/zh-cn/)。

### 环境变量

也支持通过 PowerShell 为当前进程及其子进程配置：

```powershell
$env:DEEPSEEK\_API\_KEY = "替换为你的密钥"
$env:DEEPSEEK\_MODEL = "deepseek-flash"
python psychic.py "D:\\示例文件夹"
```

|配置|规则|
|-|-|
|API 地址|固定为 `https://api.deepseek.com`|
|密钥|优先读取非空 `DEEPSEEK\_API\_KEY`，否则读取 `api\_key.txt`|
|模型|优先读取非空 `DEEPSEEK\_MODEL`，否则读取所选密钥配置中 `\|` 后的模型名，最后使用 `deepseek-flash`|
|思考模式|当前请求固定关闭|

设置 `DEEPSEEK\_API\_KEY` 后，密钥文件整体不再读取，包括其中的模型名。PowerShell 的临时环境变量不会自动传给已经运行的资源管理器，因此右键启动时使用密钥文件更直接。修改配置后，请关闭聊天窗口再重新打开。

密钥文件按明文保存在本机，已被 `.gitignore` 排除。分享打包目录时请移除 `api\_key.txt`。对话文本和作为上下文读取的文件内容会发送至 DeepSeek API。

## 从源码运行

需要 Python 3.10+；本机打包与聊天验证使用 Python 3.14。具体 Python 版本还需满足所安装依赖的要求。

在项目目录执行：

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt

# 打开右键菜单管理窗口
.\\.venv\\Scripts\\python.exe psychic.py

# 直接针对文件或文件夹打开聊天框
.\\.venv\\Scripts\\python.exe psychic.py "D:\\示例文件夹"
```

源码注册菜单时会记录当前 Python 解释器和脚本的绝对路径，因此移动项目或删除虚拟环境后，需要重新注册。

## 使用说明

### 文件上下文

首次发送消息时，程序在工作线程准备文件上下文，模型随后可以按需调用文件工具。

|类型|当前行为|
|-|-|
|目录|非递归列出前 50 项；目录中筛选到恰好一个支持的文件时，会尝试读取|
|文本|支持 `.txt`、`.csv`、`.md`、`.py`、`.json`、`.log`、`.ini`、`.bat`，按 UTF-8 读取前 2,000 字符|
|文档|尝试通过 MarkItDown 解析 `.docx`、`.xlsx`、`.xls`、`.doc`、`.pptx`、`.pdf`，取转换结果前 2,000 字符；实际支持取决于转换器和文件内容|
|多个选中路径|自动读取仅在支持的文件恰好有一个时进行|

这些是内容截取限制，不代表完整文件分析。长文档后半部分、超过 50 项的目录内容不会自动全部进入上下文。

### 脚本执行

AI 返回脚本时，界面会显示脚本和运行按钮。可以先修改脚本，再点击运行。

* PowerShell 脚本通过系统 `powershell` 启动。
* Python 脚本通过系统 `python` 启动，使用的是该命令对应的环境。
* 输出和交互输入保留在独立终端中，聊天框不嵌入终端输出。
* 脚本需要的 ffmpeg、ImageMagick、Pillow 等工具或库需自行安装。
* 关闭聊天框不会终止已经单独启动的脚本终端。

### 窗口与退出

对话只保存在当前窗口内存中，关闭后不保留。窗口打开期间，通过本机 `127.0.0.1:14514` 接收后续右键传入的路径；该监听随程序退出结束，不是后台服务。

目前后续传入的路径会更新界面，但已创建的模型系统上下文不会自动同步。需要准确切换处理对象时，建议关闭当前聊天框，再从目标文件重新打开。

## 管理右键菜单

* **添加或移除**：无参数启动程序，在管理窗口点击对应按钮。
* **注册范围**：当前 Windows 用户，包含文件、文件夹及文件夹背景入口。
* **切换版本或移动目录**：先通过管理窗口移除旧菜单，再运行目标版本并添加。程序不会自动更新已有菜单路径。
* **卸载**：先移除右键菜单，再删除程序目录。

## 打包

在已安装项目依赖的虚拟环境中执行：

```powershell
.\\.venv\\Scripts\\python.exe -m pip install pyinstaller
.\\.venv\\Scripts\\python.exe -m PyInstaller deepseek.spec --distpath dist\\deepseek --workpath build\\deepseek --noconfirm
```

输出为 `dist\\deepseek\\psychic\\psychic.exe`。这是目录打包，避免单文件打包每次启动时的解压步骤。源码修改后，需要重新打包才能更新 exe。

重新打包会替换输出目录，先关闭该目录中的程序，并保存其中的个人配置。打包完成后再将密钥文件放回 exe 同目录；密钥不会嵌入可执行文件。

`deepseek.spec` 排除了可能从构建环境误收集的 `icuuc.dll`，使用 Windows 11 系统 ICU，解决已遇到的 QtCore DLL 加载冲突。

“轻量”目前主要指按需启动和不常驻，安装体积仍有优化空间：本机验证的目录约 297 MiB，包含 Qt 界面和文档解析依赖，实际大小随依赖版本变化。

## GitHub Actions 自动发布

仓库提供 `.github/workflows/release.yml`，在 GitHub 的 Windows x64 runner 上使用 Python 3.14 和 PyInstaller 6.19.0 打包。不需要配置 DeepSeek 密钥或个人访问令牌；Release 使用 GitHub 自动提供的 `GITHUB_TOKEN`。

### 发布正式版本

先将源码、`deepseek.spec` 和工作流提交并推送到 GitHub，再在需要发布的提交上创建版本标签。例如（请换成尚未使用的版本号）：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

推送 `v` 开头的标签后，工作流会检查源码启动、构建程序、生成 ZIP 和 SHA-256 校验文件，并创建 GitHub Release。`v1.0.0-beta.1` 等带连字符的标签会标记为预发布。已有同名 Release 时，不覆盖其附件；发布更新请使用新版本标签。

在仓库的 **Actions → Build Windows Release** 查看进度，完成后从 **Releases** 下载 `psychic-版本号-windows-x64.zip`，解压整个目录使用。

### 手动试打包

工作流进入默认分支后，在 **Actions → Build Windows Release → Run workflow** 选择分支并运行。手动运行仅生成构建产物，不创建 Release。完成后下载页面底部的 `windows-x64` artifact，里面包含程序 ZIP 和校验文件；artifact 保留 14 天。

发布包包含 `api_key.example.txt`，使用者需将其复制或重命名为 `api_key.txt` 并填写自己的密钥。工作流不复制本机配置，且发现打包目录中包含 `api_key.txt` 时会中止发布。

自动检查目前覆盖源码的无屏幕渲染启动和打包产物结构，不调用真实 API，也不代替 Windows 11 上的右键菜单、窗口交互测试。安装依赖使用 `requirements.txt` 中的版本范围，不同时间构建的依赖版本和包大小可能变化。

## 启动性能验证

```powershell
.\\.venv\\Scripts\\python.exe benchmark\_startup.py
```

脚本启动三个独立进程，使用无屏幕渲染模式创建窗口：

|字段|含义|
|-|-|
|`import\_ms`|导入项目模块的耗时|
|`ready\_ms`|从开始导入到窗口创建并处理一次事件的耗时|
|`process\_ms`|父进程测得的完整子进程运行耗时，包含退出|
|`openai\_loaded` / `pydantic\_loaded`|窗口准备完成时是否已加载 API 相关依赖，当前应为 `false`|

本机对比中，窗口准备时间中位数从 763 ms 降至 112 ms；随后在项目 Python 3.14 环境中测得约 150–160 ms。两组环境不同，数值仅供参考。

测试不包含资源管理器菜单、真实屏幕绘制或打包启动器耗时，也不代表清空系统缓存后的冷启动性能。API 依赖的加载耗时被推迟到首次发送，并未消失。

## 常见问题

**右键找不到 psychic？** 先无参数启动程序并添加菜单；Windows 11 再检查“显示更多选项”。

**为什么双击 exe 没有聊天框？** 无参数启动用于管理菜单。通过右键打开，或在命令行传入目标路径。

**为什么仍然打开旧版本？** 菜单保存的是绝对路径，重新打包到其他目录不会更新菜单。移除旧菜单后，从新版本重新添加。

**提示密钥未配置或 API 错误？** 检查实际启动版本旁的 `api\_key.txt`、环境变量覆盖、DeepSeek 密钥与账户状态，以及网络连接。聊天框会显示接口返回的错误。

**文档读取失败或回答不完整？** 检查文件类型、UTF-8 编码及转换依赖，并注意前 2,000 字符和目录前 50 项的限制。

**提示 QtCore DLL 加载失败？** 保留完整 `\_internal` 目录，并使用本项目的 `deepseek.spec` 重新打包，避免混用不同版本的运行库。

## 项目结构

```text
psychic.py              # 界面、DeepSeek 调用、文件工具、菜单注册及本机通信
locales.py              # 中英文界面文字与系统提示词
requirements.txt        # 运行依赖
benchmark\_startup.py    # 无屏幕渲染启动测试
deepseek.spec           # PyInstaller 目录打包配置
.github/workflows/release.yml  # GitHub Actions 构建及 Release 发布
```

