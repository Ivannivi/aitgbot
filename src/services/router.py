"""
AI Provider Router

Manages multiple AI providers and routes requests to the appropriate one.
To add a new provider:
1. Create the provider class in a new file (inheriting from AIProvider)
2. Import and register it in PROVIDERS dict below
"""

import logging
from typing import Dict, List, Optional, Type

from .base import AIProvider, Message, ChatResponse, Model
from .lm_studio import LMStudioProvider

logger = logging.getLogger(__name__)

# ============================================================================
# PROVIDER REGISTRY
# ============================================================================
# Add new providers here. The key is the provider name used in config.
# ============================================================================

PROVIDERS: Dict[str, Type[AIProvider]] = {
    "lm_studio": LMStudioProvider,
    # Add more providers here:
    # "openai": OpenAIProvider,
    # "anthropic": AnthropicProvider,
    # "ollama": OllamaProvider,
}

# Default provider if none specified
DEFAULT_PROVIDER = "lm_studio"


class AIRouter:
    """
    Routes AI requests to the appropriate provider.
    
    Usage:
        router = AIRouter()
        router.configure_provider("lm_studio", base_url="http://127.0.0.1:1234/v1")
        response = await router.chat(messages, model="my-model")
    """
    
    def __init__(self):
        self._instances: Dict[str, AIProvider] = {}
        self._current_provider: str = DEFAULT_PROVIDER
    
    def configure_provider(self, provider_name: str, **kwargs) -> bool:
        """
        Configure and instantiate a provider.
        
        Args:
            provider_name: Name of the provider (must be in PROVIDERS)
            **kwargs: Provider-specific configuration
            
        Returns:
            True if successful, False otherwise
        """
        if provider_name not in PROVIDERS:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        
        try:
            provider_class = PROVIDERS[provider_name]
            self._instances[provider_name] = provider_class(**kwargs)
            logger.info(f"Configured provider: {provider_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure provider {provider_name}: {e}")
            return False
    
    def set_current_provider(self, provider_name: str) -> bool:
        """Set the current active provider"""
        if provider_name not in PROVIDERS:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        self._current_provider = provider_name
        return True
    
    def get_current_provider(self) -> str:
        """Get the current active provider name"""
        return self._current_provider
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[AIProvider]:
        """
        Get a provider instance.
        
        Args:
            provider_name: Provider to get (uses current if None)
            
        Returns:
            Provider instance or None if not configured
        """
        name = provider_name or self._current_provider
        
        # Auto-configure with defaults if not yet configured
        if name not in self._instances:
            self.configure_provider(name)
        
        return self._instances.get(name)
    
    async def chat(
        self, 
        messages: List[Message], 
        model: str,
        provider_name: Optional[str] = None
    ) -> ChatResponse:
        """
        Send a chat request to a provider.
        
        Args:
            messages: List of Message objects
            model: Model ID to use
            provider_name: Override the current provider
            
        Returns:
            ChatResponse from the provider
            
        Raises:
            ValueError: If provider not found or not configured
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not configured: {provider_name or self._current_provider}")
        
        return await provider.chat(messages, model)
    
    async def list_models(self, provider_name: Optional[str] = None) -> List[Model]:
        """List models from a provider"""
        provider = self.get_provider(provider_name)
        if not provider:
            return []
        return await provider.list_models()
    
    async def list_all_models(self) -> Dict[str, List[Model]]:
        """List models from all configured providers"""
        result = {}
        for name in self._instances:
            result[name] = await self.list_models(name)
        return result
    
    async def health_check(self, provider_name: Optional[str] = None) -> bool:
        """Check if a provider is healthy"""
        provider = self.get_provider(provider_name)
        if not provider:
            return False
        return await provider.health_check()
    
    def list_providers(self) -> List[str]:
        """List all available provider names"""
        return list(PROVIDERS.keys())
    
    def list_configured_providers(self) -> List[str]:
        """List all configured provider names"""
        return list(self._instances.keys())


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
# Use get_router() to get the shared router instance
# ============================================================================

_router_instance: Optional[AIRouter] = None


def get_router() -> AIRouter:
    """Get the shared AIRouter instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = AIRouter()
    return _router_instance
