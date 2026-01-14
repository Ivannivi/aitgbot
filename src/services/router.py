import logging
from typing import Dict, List, Optional, Type

from .base import AIProvider, Message, ChatResponse, Model
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider

logger = logging.getLogger(__name__)

PROVIDERS: Dict[str, Type[AIProvider]] = {
    "lm_studio": LMStudioProvider,
    "ollama": OllamaProvider,
}

DEFAULT_PROVIDER = "lm_studio"


class AIRouter:
    def __init__(self):
        self._instances: Dict[str, AIProvider] = {}
        self._current_provider: str = DEFAULT_PROVIDER

    def configure_provider(self, provider_name: str, **kwargs) -> bool:
        if provider_name not in PROVIDERS:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        try:
            self._instances[provider_name] = PROVIDERS[provider_name](**kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to configure {provider_name}: {e}")
            return False

    def set_current_provider(self, provider_name: str) -> bool:
        if provider_name not in PROVIDERS:
            return False
        self._current_provider = provider_name
        return True

    def get_current_provider(self) -> str:
        return self._current_provider

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[AIProvider]:
        name = provider_name or self._current_provider
        if name not in self._instances:
            self.configure_provider(name)
        return self._instances.get(name)

    async def chat(self, messages: List[Message], model: str, provider_name: Optional[str] = None) -> ChatResponse:
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not configured: {provider_name or self._current_provider}")
        return await provider.chat(messages, model)

    async def list_models(self, provider_name: Optional[str] = None) -> List[Model]:
        provider = self.get_provider(provider_name)
        return await provider.list_models() if provider else []

    async def list_all_models(self) -> Dict[str, List[Model]]:
        return {name: await self.list_models(name) for name in self._instances}

    async def health_check(self, provider_name: Optional[str] = None) -> bool:
        provider = self.get_provider(provider_name)
        return await provider.health_check() if provider else False

    def list_providers(self) -> List[str]:
        return list(PROVIDERS.keys())

    def list_configured_providers(self) -> List[str]:
        return list(self._instances.keys())


_router_instance: Optional[AIRouter] = None


def get_router() -> AIRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = AIRouter()
    return _router_instance
