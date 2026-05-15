DEFAULT_LOCALES = {
    "zh": {
        "menu_name": "通灵",
        "setup_title": "通灵",
        'start_hint': "右键任意文件或文件夹以开始",
        "btn_add": "添加右键菜单",
        "btn_rm": "移除右键菜单",
        "title_success": "成功",
        "title_error": "错误",
        "msg_success": "操作完成！",
        "msg_fail": "操作失败: ",
        "assistant_title": "通灵",
        "ai_thinking": "思考中...",
        "you": "你: ",
        "ai_trying": "尝试调用: ",
        "ai_explains": "AI: ",
        "pending_cmd": "待执行",
        "btn_run": "▶ 运行",
        "executing": "正在执行...",
        "py_done": "Python开始执行。",
        "ps_done": "powershell开始执行。",
        "parse_err": "解析出错: ",
        "exec_err": "错误: ",

        "command_lang": "留空 或 python 或 powershell",
        "command_code": "留空 或 脚本代码 ",
        "command_description": "回答用户的问题或简短描述代码",

        "list_dir_desc": "列出目录下的文件（不递归）**注意，此命令占用较大，不要重复执行**",
        "list_dir_path_desc": "目录的路径",
        "read_file_desc": "读取文件内容（支持'.txt', '.csv', '.md', '.py', '.json', '.log', '.ini', '.bat','.docx', '.xlsx', '.xls', '.doc', '.pptx', '.pdf'）**注意，此命令占用极大，不要重复执行**",
        "read_file_path_desc": "文件的路径",

        "sys_prompt": """你已与系统深度集成，请根据用户选中的文件和提问选择如下操作之一，回答用户的问题，给用户提供一个自动化脚本。
        用户选中的文件[{files}]
        用户系统Windows 11。
        用户已安装ffmpeg，imagemagick，Sound eXchange，yt-dlp。
        python环境中存在Pillow。
        你应该优先提供powershell脚本。
        **重要：对于计数类任务如"这里有多少图片"，不要调用list_dir！这会占用大量电脑性能甚至卡死！直接提供计数脚本以保证性能和绝对的准确性！**
        **重要：无论如何都不要重复调用list_dir或read_file，文件永远不会变化，永远相信之前的调用结果！**
        **重要：如果调用返回了错误，不要再次尝试调用，因为文件永远不会变化，下次调用的结果不会改变！**
        """
    },
    "en": {
        "menu_name": "psychic",
        "setup_title": "psychic",
        'start_hint': "Right-click any file or folder to start",
        "btn_add": "Add Context Menu",
        "btn_rm": "Remove Context Menu",
        "title_success": "Success",
        "title_error": "Error",
        "msg_success": "Operation successful!",
        "msg_fail": "Operation failed: ",
        "assistant_title": "psychic",
        "ai_thinking": "thinking...",
        "you": "You: ",
        "ai_trying": "trying to call: ",
        "ai_explains": "AI: ",
        "pending_cmd": "Pending",
        "btn_run": "▶ Run",
        "executing": "Executing...",
        "py_done": "Python execution started.",
        "ps_done": "Powershell execution started.",
        "parse_err": "Parsing error: ",
        "exec_err": "Error: ",

        "command_lang": "Leave empty or 'python' or 'powershell'",
        "command_code": "Leave empty or script code",
        "command_description": "Answer user's question or briefly describe the code",

        "list_dir_desc": "List files in directory (non-recursive). **Note: High resource usage, do not repeat execution**",
        "list_dir_path_desc": "Path of the directory",
        "read_file_desc": "Read file content (supports '.txt', '.csv', '.md', '.py', '.json', '.log', '.ini', '.bat','.docx', '.xlsx', '.xls', '.doc', '.pptx', '.pdf'). **Note: Extremely high resource usage, do not repeat execution**",
        "read_file_path_desc": "Path of the file",

        "sys_prompt": """You are deeply integrated with the system. Based on the files selected by the user and their queries, choose one of the following operations to answer the question or provide an automation script.
        Selected files: [{files}]
        OS: Windows 11.
        Installed tools: ffmpeg, imagemagick, Sound eXchange, yt-dlp.
        Python environment: Pillow is available.
        Preference: You should prioritize providing PowerShell scripts.
        **IMPORTANT: For counting tasks (e.g., 'how many images are here'), DO NOT call list_dir! This consumes significant resources. Provide a counting script directly for performance and absolute accuracy!**
        **IMPORTANT: Never repeat list_dir or read_file calls. Files will not change; always trust previous results!**
        **IMPORTANT: If a call returns an error, do not retry. The file state is static, and subsequent calls will yield the same result!**
        """
    }
}
