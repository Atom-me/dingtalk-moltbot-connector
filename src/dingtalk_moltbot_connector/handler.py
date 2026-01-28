"""钉钉机器人消息处理器

接收钉钉消息，调用 Moltbot Gateway SSE API，以 AI Card 流式响应。
"""

import json
import logging
from typing import AsyncGenerator

import httpx
import dingtalk_stream
from dingtalk_stream import ChatbotMessage, CallbackMessage

from .config import ConnectorConfig
from .media import build_media_system_prompt

logger = logging.getLogger("dingtalk_moltbot_connector")


class MoltbotChatbotHandler(dingtalk_stream.ChatbotHandler):
    """钉钉机器人消息处理器 — 桥接到 Moltbot Gateway"""

    def __init__(self, config: ConnectorConfig):
        super().__init__()
        self.config = config

    async def process(self, callback: CallbackMessage):
        """处理钉钉机器人消息"""
        try:
            incoming_message = ChatbotMessage.from_dict(callback.data)
            user_content = incoming_message.text.content.strip()
            logger.info(f"收到消息: {user_content[:100]}...")

            # 尝试创建 AI 流式卡片
            try:
                card = self.ai_markdown_card_start(incoming_message)
            except Exception as e:
                logger.warning(f"AI Card 创建失败，降级为文本回复: {e}")
                card = None

            if card and card.card_instance_id:
                # 流式卡片模式
                accumulated = ""
                try:
                    async for chunk in self._stream_from_gateway(user_content):
                        accumulated += chunk
                        card.ai_streaming(accumulated)
                except Exception as e:
                    logger.error(f"Gateway 调用失败: {e}")
                    accumulated += f"\n\n⚠️ 响应中断: {e}"
                    card.ai_streaming(accumulated)

                card.ai_finish(accumulated)
                logger.info(f"流式响应完成，共 {len(accumulated)} 字符")
            else:
                # 降级：纯文本回复
                try:
                    full_response = ""
                    async for chunk in self._stream_from_gateway(user_content):
                        full_response += chunk
                    self.reply_text(full_response or "（无响应）", incoming_message)
                    logger.info(f"文本回复完成，共 {len(full_response)} 字符")
                except Exception as e:
                    logger.error(f"Gateway 调用失败: {e}")
                    self.reply_text(f"抱歉，处理请求时出错: {e}", incoming_message)

            return dingtalk_stream.AckMessage.STATUS_OK, "ok"

        except Exception as e:
            logger.error(f"处理消息异常: {e}", exc_info=True)
            return dingtalk_stream.AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)

    async def _stream_from_gateway(
        self, user_content: str
    ) -> AsyncGenerator[str, None]:
        """调用 Moltbot Gateway SSE 接口，逐 chunk 产出内容

        Args:
            user_content: 用户消息文本

        Yields:
            响应内容片段
        """
        headers = {"Content-Type": "application/json"}
        if self.config.gateway_token:
            headers["Authorization"] = f"Bearer {self.config.gateway_token}"

        # 构建 messages
        messages: list[dict] = []

        # 图片上传引导 prompt
        if self.config.enable_media_upload:
            media_prompt = build_media_system_prompt(
                self.config.dingtalk_client_id,
                self.config.dingtalk_client_secret,
            )
            if media_prompt:
                messages.append({"role": "system", "content": media_prompt})

        # 自定义 system prompt
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                self.config.api_url,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(
                        f"Gateway 返回 {response.status_code}: "
                        f"{error_body.decode(errors='replace')}"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        choices = chunk.get("choices", [])
                        if choices:
                            content = (
                                choices[0].get("delta", {}).get("content", "")
                            )
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
