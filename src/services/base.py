"""
Base class for AI providers.
All AI providers should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a chat message"""
    role: str  # 'system', 'user', 'assistant'
    content: Any  # str or list for multimodal content


@dataclass
class ChatResponse:
    """Response from an AI provider"""
    text: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None  # tokens used, if available


@dataclass
class Model:
    """Represents an available model"""
    id: str
    name: str
    provider: str


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    To add a new provider:
    1. Create a new file in services/ (e.g., openai_provider.py)
    2. Inherit from AIProvider
    3. Implement all abstract methods
    4. Register in router.py
    """
    
    name: str = "base"
    display_name: str = "Base Provider"
    
    @abstractmethod
    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of Message objects
            model: Model ID to use
            
        Returns:
            ChatResponse with the AI's response
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Model]:
        """
        List available models from this provider.
        
        Returns:
            List of Model objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available and working.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def supports_vision(self) -> bool:
        """
        Check if this provider supports vision/image inputs.
        Override in subclass if supported.
        """
        return False
    
    def supports_streaming(self) -> bool:
        """
        Check if this provider supports streaming responses.
        Override in subclass if supported.
        """
        return False
