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
        用户已安装ffmpeg, imagemagick。
        python环境中存在Pillow。
        你应该优先提供powershell脚本。
        **重要：对于计数类任务，不要调用list_dir自己计数，总是提供计数脚本以保证绝对的准确性！**
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
        "btn_run": "▶ Run Command",
        "executing": "Executing...",
        "py_done": "Python script execution finished.",
        "ps_done": "Command line execution finished.",
        "parse_err": "AI response parsing error: ",
        "exec_err": "Execution Exception",
        "read_mock": "Tool read_file executed. First 20 lines of {file}:\n{content}",
        "read_ack": "Received. I understand the file content.",

        # --- AI Prompts (English) ---
        "init_trigger": "Please analyze the target paths and prepare for instructions.",
        "tool_dir_res": "System returned tool execution result:\nDirectory preview: {items}",
        "tool_file_res": "System returned tool execution result:\nFile content preview:\n{content}",
        "tool_unk_res": "System returned tool execution result:\nUnknown tool: {name}",
        "tool_err_res": "System returned tool execution result:\nTool execution failed, error: {err}",
        "sys_prompt": """You are a system-level automation assistant.
Current target paths selected by the user: {paths}

You MUST strictly return a pure JSON object, without markdown tags. The format MUST be one of the following:
1. Call tool (to explore env): {{"type": "tool", "name": "list_directory" or "read_file", "path": "absolute path"}}
2. Generate command (when ready): {{"type": "command", "lang": "python" or "powershell", "code": "executable code", "desc": "short explanation in English"}}
3. Cannot execute (beyond capability): {{"type": "explain", "text": "detailed explanation in English why it cannot be done"}}"""
    }
}
