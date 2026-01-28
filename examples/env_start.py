"""环境变量方式启动

设置以下环境变量后运行:
    export DINGTALK_CLIENT_ID="dingxxxxxxxxx"
    export DINGTALK_CLIENT_SECRET="your_secret_here"
    export MOLTBOT_GATEWAY_URL="http://127.0.0.1:18789"  # 可选
    python examples/env_start.py
"""

from dingtalk_moltbot_connector import MoltbotConnector

MoltbotConnector.from_env().start()
