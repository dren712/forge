from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    goal: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    current_step: int = 0
    tool_call_count: int = 0
    model_call_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    status: Literal["RUNNING", "COMPLETED", "FAILED", "TIMEOUT", "MAX_STEPS"] = "RUNNING"
    errors: list[str] = Field(default_factory=list)
    verification_passed: bool = False
    verification_feedback: str | None = None
    final_output: str | None = None
    latency_ms: float = 0.0
