"""
Ollama AI Provider

Connects to a local Ollama instance.
Ollama provides a REST API for running LLMs locally.
"""

import logging
from typing import List, Optional
import httpx

from .base import AIProvider, Message, ChatResponse, Model

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """
    Ollama provider using native Ollama API.
    
    Ollama runs locally and exposes a REST API.
    Default URL: http://127.0.0.1:11434
    """
    
    name = "ollama"
    display_name = "Ollama"
    
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip('/')
    
    def _convert_messages(self, messages: List[Message]) -> List[dict]:
        """Convert Message objects to Ollama format"""
        ollama_messages = []
        
        for msg in messages:
            if isinstance(msg.content, str):
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            elif isinstance(msg.content, list):
                # Handle multimodal content (images)
                text_parts = []
                images = []
                
                for part in msg.content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif part.get("type") == "image_url":
                            image_url = part.get("image_url", {}).get("url", "")
                            # Extract base64 data if it's a data URL
                            if image_url.startswith("data:"):
                                # Format: data:image/jpeg;base64,<data>
                                base64_data = image_url.split(",", 1)[-1]
                                images.append(base64_data)
                
                message_dict = {
                    "role": msg.role,
                    "content": " ".join(text_parts)
                }
                if images:
                    message_dict["images"] = images
                
                ollama_messages.append(message_dict)
        
        return ollama_messages
    
    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        """Send a chat completion to Ollama"""
        
        ollama_messages = self._convert_messages(messages)
        
        logger.info(f"Sending request to Ollama ({self.base_url}) with model {model}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
        
        logger.info("Received response from Ollama")
        
        response_text = data.get("message", {}).get("content", "")
        
        usage = None
        if "prompt_eval_count" in data or "eval_count" in data:
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            }
        
        return ChatResponse(
            text=response_text,
            model=model,
            provider=self.name,
            usage=usage
        )
    
    async def list_models(self) -> List[Model]:
        """List available models from Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            
            return [
                Model(
                    id=m["name"],
                    name=m.get("name", m["name"]),
                    provider=self.name
                )
                for m in data.get("models", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def supports_vision(self) -> bool:
        """Ollama supports vision with compatible models (like llava)"""
        return True
    
    def supports_streaming(self) -> bool:
        """Ollama supports streaming"""
        return True
