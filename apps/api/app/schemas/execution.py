from typing import Any
from pydantic import BaseModel, Field
from app.agents.verifier import VerificationResult


class ExecutionResult(BaseModel):
    status: str
    final_output: str | None = None
    verification: VerificationResult | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    model_calls: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    usage: dict[str, int] = Field(default_factory=dict)
