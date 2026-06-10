import autogen

OPENAI_API_KEY = "sk-0d550a671ecd4c04938c7b9f840faf83"
OPENAI_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 配置 LLM（替换为你的 API 密钥）
config_list = [
    {
        "model": "deepseek-v3",
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_API_BASE,
    }
]

llm_config = {"config_list": config_list}

# 1. 定义三个智能体
product_manager = autogen.AssistantAgent(
    name="ProductManager",
    system_message="你是一名产品经理。请清晰描述用户需求，并确保功能定义无歧义。",
    llm_config=llm_config,
)

software_engineer = autogen.AssistantAgent(
    name="SoftwareEngineer",
    system_message="你是一名资深 Python 工程师。请根据产品需求编写简洁、正确的代码，并附带使用示例。",
    llm_config=llm_config,
)

code_reviewer = autogen.AssistantAgent(
    name="CodeReviewer",
    system_message=(
        "你是代码审查员。你的职责是：\n"
        "1. 检查代码是否满足产品需求；\n"
        "2. **但不要假设代码运行正确**；\n"
        "3. **不要回复 TERMINATE**；\n"
        "4. 如果代码逻辑有明显错误，请指出；\n"
        "5. 如果代码看起来合理，请说：'代码逻辑无明显错误，请 UserProxy 执行验证。'\n"
        "只有在 UserProxy 执行后，确认输出符合预期，才可回复 TERMINATE。"
    ),
    llm_config=llm_config,
)

# 2. 用户代理（启动任务 + 可选执行代码）
user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    is_termination_msg=lambda x: any(
        term in x.get("content", "") for term in ["TERMINATE", "批准通过", "任务完成"]
    ),
)

# 3. 创建群聊
groupchat = autogen.GroupChat(
    agents=[user_proxy, product_manager, software_engineer, code_reviewer],
    messages=[],
    max_round=12,
    speaker_selection_method="auto",  # 让 LLM 决定下一个发言者
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
)

# 4. 启动群聊
user_proxy.initiate_chat(
    manager,
     message=(
            "我需要一个函数：输入一个字符串列表，返回其中最长的字符串。"
            "如果有多个一样长的，返回第一个。"
            "请实现该函数，并用以下测试用例验证："
            "['apple', 'hi', 'banana', 'cat'] → 应返回 'banana'；"
            "[] → 应抛出 ValueError。"
            "请 SoftwareEngineer 用 ```python 代码块提供完整可执行代码，包括测试用例。"
            "在代码审核通过后，UserProxy 执行后再结束。"
        ),
)
