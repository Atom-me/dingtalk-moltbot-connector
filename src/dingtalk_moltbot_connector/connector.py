"""MoltbotConnector — 主入口类

将钉钉机器人消息桥接到 Moltbot Gateway，以 AI Card 流式卡片响应。
"""

import logging
import signal
import sys
import threading
from typing import Optional

import dingtalk_stream

from .config import ConnectorConfig
from .handler import MoltbotChatbotHandler

logger = logging.getLogger("dingtalk_moltbot_connector")


def _setup_default_logging() -> None:
    """配置默认日志格式（仅在用户未配置时生效）"""
    root_logger = logging.getLogger("dingtalk_moltbot_connector")
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(handler)


class MoltbotConnector:
    """钉钉 ↔ Moltbot Gateway 连接器

    用法::

        connector = MoltbotConnector(
            dingtalk_client_id="dingXXX",
            dingtalk_client_secret="secret",
            gateway_url="http://127.0.0.1:18789",
        )
        connector.start()  # 阻塞运行

    Args:
        dingtalk_client_id: 钉钉 AppKey
        dingtalk_client_secret: 钉钉 AppSecret
        gateway_url: Moltbot Gateway 地址
        model: 模型名称
        system_prompt: 自定义 system prompt
        enable_media_upload: 是否启用钉钉图片上传引导
        timeout: SSE 请求超时秒数
        gateway_token: Gateway 认证 token
    """

    def __init__(
        self,
        dingtalk_client_id: str = "",
        dingtalk_client_secret: str = "",
        gateway_url: str = "http://127.0.0.1:18789",
        model: str = "default",
        system_prompt: str = "",
        enable_media_upload: bool = True,
        timeout: float = 120.0,
        gateway_token: str = "",
    ):
        self.config = ConnectorConfig(
            dingtalk_client_id=dingtalk_client_id,
            dingtalk_client_secret=dingtalk_client_secret,
            gateway_url=gateway_url,
            model=model,
            system_prompt=system_prompt,
            enable_media_upload=enable_media_upload,
            timeout=timeout,
            gateway_token=gateway_token,
        )
        self._client: Optional[dingtalk_stream.DingTalkStreamClient] = None
        self._stop = threading.Event()

    @classmethod
    def from_env(cls) -> "MoltbotConnector":
        """从环境变量创建连接器实例

        环境变量：
            DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET,
            MOLTBOT_GATEWAY_URL, MOLTBOT_MODEL, MOLTBOT_GATEWAY_TOKEN
        """
        return cls()

    def start(self) -> None:
        """阻塞启动连接器，Ctrl+C 退出"""
        _setup_default_logging()
        self.config.validate()

        logger.info("=" * 50)
        logger.info("dingtalk-moltbot-connector 启动")
        logger.info(f"  Gateway: {self.config.gateway_url}")
        logger.info(f"  Model:   {self.config.model}")
        logger.info(f"  图片上传: {'启用' if self.config.enable_media_upload else '关闭'}")
        logger.info("=" * 50)

        # 创建钉钉 Stream 客户端
        credential = dingtalk_stream.Credential(
            self.config.dingtalk_client_id,
            self.config.dingtalk_client_secret,
        )
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        # 注册消息处理器
        handler = MoltbotChatbotHandler(self.config)
        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        # 信号处理
        def _handle_signal(signum, frame):
            logger.info("收到停止信号，正在退出...")
            self._stop.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        # 在后台线程启动 Stream 客户端
        def _run():
            try:
                logger.info("钉钉 Stream 客户端已启动，等待消息...")
                self._client.start_forever()
            except Exception as e:
                logger.error(f"Stream 客户端异常退出: {e}")
                self._stop.set()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        # 主线程等待停止信号
        self._stop.wait()
        logger.info("连接器已停止")

    def stop(self) -> None:
        """停止连接器"""
        self._stop.set()
        self._client = None


def cli_main() -> None:
    """CLI 入口点：dingtalk-moltbot"""
    import argparse

    parser = argparse.ArgumentParser(
        description="dingtalk-moltbot-connector: 将钉钉机器人连接到 Moltbot Gateway"
    )
    parser.add_argument(
        "--gateway-url",
        default="",
        help="Moltbot Gateway 地址 (默认: http://127.0.0.1:18789)",
    )
    parser.add_argument(
        "--model",
        default="",
        help="模型名称 (默认: default)",
    )
    parser.add_argument(
        "--no-media-upload",
        action="store_true",
        help="关闭钉钉图片上传引导",
    )
    args = parser.parse_args()

    kwargs = {}
    if args.gateway_url:
        kwargs["gateway_url"] = args.gateway_url
    if args.model:
        kwargs["model"] = args.model
    if args.no_media_upload:
        kwargs["enable_media_upload"] = False

    connector = MoltbotConnector(**kwargs)
    connector.start()
