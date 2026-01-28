"""自定义 system prompt 示例

通过 system_prompt 参数可以定制 Moltbot 的行为和人设。
"""

from dingtalk_moltbot_connector import MoltbotConnector

connector = MoltbotConnector(
    dingtalk_client_id="dingxxxxxxxxx",
    dingtalk_client_secret="your_secret_here",
    system_prompt="你是一个友好的技术助手，擅长解答 Python 和前端开发问题。回答简洁明了。",
    model="default",
    enable_media_upload=False,  # 纯文本场景可关闭图片上传
)

connector.start()
