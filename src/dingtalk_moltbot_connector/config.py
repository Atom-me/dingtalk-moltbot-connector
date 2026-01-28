"""配置管理模块

支持三级配置优先级：构造参数 > 环境变量 > 默认值
"""

import os
from dataclasses import dataclass

# 标记值，用于区分"用户未传参"和"用户显式传入空字符串"
_UNSET = "__UNSET__"

# 字段名 → (环境变量名, 默认值)
_ENV_DEFAULTS: dict[str, tuple[str, str]] = {
    "dingtalk_client_id": ("DINGTALK_CLIENT_ID", ""),
    "dingtalk_client_secret": ("DINGTALK_CLIENT_SECRET", ""),
    "gateway_url": ("MOLTBOT_GATEWAY_URL", "http://127.0.0.1:18789"),
    "model": ("MOLTBOT_MODEL", "default"),
    "gateway_token": ("MOLTBOT_GATEWAY_TOKEN", ""),
}


@dataclass
class ConnectorConfig:
    """连接器配置

    优先级：构造参数 > 环境变量 > 默认值

    Args:
        dingtalk_client_id: 钉钉机器人 AppKey
        dingtalk_client_secret: 钉钉机器人 AppSecret
        gateway_url: Moltbot Gateway 地址（不含 path）
        model: 请求 Gateway 时使用的模型名称
        system_prompt: 自定义 system prompt，会拼接在媒体提示词之后
        enable_media_upload: 是否注入钉钉图片上传引导提示词
        timeout: SSE 流式请求超时秒数
        gateway_token: Gateway 认证 token，本地免认证时留空
    """

    dingtalk_client_id: str = _UNSET
    dingtalk_client_secret: str = _UNSET
    gateway_url: str = _UNSET
    model: str = _UNSET
    system_prompt: str = ""
    enable_media_upload: bool = True
    timeout: float = 120.0
    gateway_token: str = _UNSET

    def __post_init__(self):
        """对 _UNSET 字段按 环境变量 > 默认值 顺序填充"""
        for attr, (env_key, default) in _ENV_DEFAULTS.items():
            if getattr(self, attr) == _UNSET:
                env_val = os.environ.get(env_key, "")
                setattr(self, attr, env_val if env_val else default)

    @property
    def api_url(self) -> str:
        """Gateway chat completions API 完整地址"""
        base = self.gateway_url.rstrip("/")
        return f"{base}/v1/chat/completions"

    def validate(self) -> None:
        """校验必填配置，不满足时抛出 ValueError"""
        if not self.dingtalk_client_id:
            raise ValueError(
                "缺少 dingtalk_client_id，"
                "请通过构造参数或环境变量 DINGTALK_CLIENT_ID 配置"
            )
        if not self.dingtalk_client_secret:
            raise ValueError(
                "缺少 dingtalk_client_secret，"
                "请通过构造参数或环境变量 DINGTALK_CLIENT_SECRET 配置"
            )

    @classmethod
    def from_env(cls) -> "ConnectorConfig":
        """纯从环境变量构建配置"""
        return cls()
