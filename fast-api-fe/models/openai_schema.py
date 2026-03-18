"""
Pydantic models matching the OpenAI Chat Completions API schema.
https://platform.openai.com/docs/api-reference/chat/create
"""
from typing import Literal, Optional
import time
import uuid

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Request body for POST /v1/chat/completions."""

    model: str = "customers-agent"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatChoice(BaseModel):
    """A single chat completion choice."""

    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageStats(BaseModel):
    """Token usage — filled with zeros since we proxy to Agent Engine."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Response body for POST /v1/chat/completions (non-streaming)."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "customers-agent"
    choices: list[ChatChoice]
    usage: UsageStats = Field(default_factory=UsageStats)
