import logging
from typing import List
from openai import AsyncOpenAI

from .base import AIProvider, Message, ChatResponse, Model

logger = logging.getLogger(__name__)


class LMStudioProvider(AIProvider):
    name = "lm_studio"
    display_name = "LM Studio"

    def __init__(self, base_url: str = "http://127.0.0.1:1234/v1", api_key: str = "lm-studio"):
        self.base_url = base_url
        self.api_key = api_key
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        completion = await self.client.chat.completions.create(
            model=model,
            messages=openai_messages
        )

        usage = None
        if completion.usage:
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }

        return ChatResponse(
            text=completion.choices[0].message.content or "",
            model=model,
            provider=self.name,
            usage=usage
        )

    async def list_models(self) -> List[Model]:
        try:
            response = await self.client.models.list()
            return [Model(id=m.id, name=m.id, provider=self.name) for m in response.data]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def supports_vision(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
        """LM Studio supports streaming"""
        return True
