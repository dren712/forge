from typing import Protocol, runtime_checkable, Any
from pydantic import BaseModel, Field


class ToolCallItem(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCallItem] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    raw_response: Any = None


@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Generate response from the model."""
        ...
