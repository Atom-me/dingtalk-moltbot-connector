#!/usr/bin/env python3
"""快速启动

用法:
    python examples/quick_start.py

首次运行会交互式引导你输入钉钉凭证，之后可直接启动。
"""

import os
import sys

# 让脚本在项目根目录直接运行时也能找到包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dingtalk_moltbot_connector import MoltbotConnector


def prompt_input(name: str, env_key: str, secret: bool = False) -> str:
    """从环境变量读取，没有则交互式输入"""
    value = os.environ.get(env_key, "")
    if value:
        display = value[:4] + "****" if secret else value
        print(f"  {name}: {display} (来自环境变量 {env_key})")
        return value

    hint = f"  请输入{name}: "
    value = input(hint).strip()
    if not value:
        print(f"  ✗ {name}不能为空")
        sys.exit(1)
    return value


def main():
    print()
    print("=" * 50)
    print("  dingtalk-moltbot-connector 快速启动")
    print("=" * 50)
    print()

    # 交互式收集配置
    print("▶ 钉钉机器人配置")
    print("  (如何获取: https://open.dingtalk.com → 应用开发 → 企业内部开发)")
    print()
    client_id = prompt_input("AppKey", "DINGTALK_CLIENT_ID")
    client_secret = prompt_input("AppSecret", "DINGTALK_CLIENT_SECRET", secret=True)

    print()
    print("▶ Moltbot Gateway 配置")
    gateway_url = os.environ.get("MOLTBOT_GATEWAY_URL", "")
    if not gateway_url:
        gateway_url = input("  Gateway 地址 (直接回车使用默认 http://127.0.0.1:18789): ").strip()
        if not gateway_url:
            gateway_url = "http://127.0.0.1:18789"
    print(f"  Gateway: {gateway_url}")

    print()
    print("  提示: 下次可通过环境变量跳过输入:")
    print(f'    export DINGTALK_CLIENT_ID="{client_id}"')
    print(f'    export DINGTALK_CLIENT_SECRET="****"')
    if gateway_url != "http://127.0.0.1:18789":
        print(f'    export MOLTBOT_GATEWAY_URL="{gateway_url}"')
    print()

    connector = MoltbotConnector(
        dingtalk_client_id=client_id,
        dingtalk_client_secret=client_secret,
        gateway_url=gateway_url,
    )
    connector.start()


if __name__ == "__main__":
    main()
