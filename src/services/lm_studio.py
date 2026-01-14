"""
LM Studio AI Provider

Connects to a local LM Studio instance via OpenAI-compatible API.
"""

import logging
from typing import List, Optional
from openai import AsyncOpenAI

from .base import AIProvider, Message, ChatResponse, Model

logger = logging.getLogger(__name__)


class LMStudioProvider(AIProvider):
    """
    LM Studio provider using OpenAI-compatible API.
    
    LM Studio runs locally and exposes an OpenAI-compatible endpoint.
    Default URL: http://127.0.0.1:1234/v1
    """
    
    name = "lm_studio"
    display_name = "LM Studio"
    
    def __init__(self, base_url: str = "http://127.0.0.1:1234/v1", api_key: str = "lm-studio"):
        self.base_url = base_url
        self.api_key = api_key
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    
    def _update_client(self, base_url: str):
        """Update the client with a new base URL"""
        if base_url != self.base_url:
            self.base_url = base_url
            self.client = AsyncOpenAI(base_url=base_url, api_key=self.api_key)
    
    async def chat(self, messages: List[Message], model: str) -> ChatResponse:
        """Send a chat completion to LM Studio"""
        
        # Convert Message objects to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.info(f"Sending request to LM Studio ({self.base_url}) with model {model}")
        
        completion = await self.client.chat.completions.create(
            model=model,
            messages=openai_messages
        )
        
        logger.info("Received response from LM Studio")
        
        response_text = completion.choices[0].message.content or ""
        
        usage = None
        if completion.usage:
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        
        return ChatResponse(
            text=response_text,
            model=model,
            provider=self.name,
            usage=usage
        )
    
    async def list_models(self) -> List[Model]:
        """List available models from LM Studio"""
        try:
            models_response = await self.client.models.list()
            return [
                Model(id=m.id, name=m.id, provider=self.name)
                for m in models_response.data
            ]
        except Exception as e:
            logger.error(f"Error listing LM Studio models: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if LM Studio is running and accessible"""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {e}")
            return False
    
    def supports_vision(self) -> bool:
        """LM Studio supports vision with compatible models"""
        return True
    
    def supports_streaming(self) -> bool:
        """LM Studio supports streaming"""
        return True
