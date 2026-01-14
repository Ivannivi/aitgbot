from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: Any


@dataclass
class ChatResponse:
    text: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None


@dataclass
class Model:
    id: str
    name: str
    provider: str


class AIProvider(ABC):
    name: str = "base"
    display_name: str = "Base Provider"

    @abstractmethod
    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        pass

    @abstractmethod
    async def list_models(self) -> List[Model]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    def supports_vision(self) -> bool:
        return False

    def supports_streaming(self) -> bool:
        return False
