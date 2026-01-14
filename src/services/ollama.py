import logging
from typing import List
import httpx

from .base import AIProvider, Message, ChatResponse, Model

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    name = "ollama"
    display_name = "Ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip('/')

    def _convert_messages(self, messages: List[Message]) -> List[dict]:
        result = []
        for msg in messages:
            if isinstance(msg.content, str):
                result.append({"role": msg.role, "content": msg.content})
            elif isinstance(msg.content, list):
                text_parts, images = [], []
                for part in msg.content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif part.get("type") == "image_url":
                            url = part.get("image_url", {}).get("url", "")
                            if url.startswith("data:"):
                                images.append(url.split(",", 1)[-1])
                entry = {"role": msg.role, "content": " ".join(text_parts)}
                if images:
                    entry["images"] = images
                result.append(entry)
        return result

    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": self._convert_messages(messages), "stream": False}
            )
            response.raise_for_status()
            data = response.json()

        usage = None
        if "prompt_eval_count" in data or "eval_count" in data:
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            }

        return ChatResponse(
            text=data.get("message", {}).get("content", ""),
            model=model,
            provider=self.name,
            usage=usage
        )

    async def list_models(self) -> List[Model]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            return [Model(id=m["name"], name=m["name"], provider=self.name) for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def supports_vision(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
