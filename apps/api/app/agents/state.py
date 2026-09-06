from typing import Any, Literal
from pydantic import BaseModel, Field
from app.agents.verifier import VerificationResult
from app.schemas.execution import ExecutionResult

VALID_TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"RUNNING", "CANCELLED", "FAILED"},
    "RUNNING": {
        "WAITING_FOR_TOOL",
        "RECOVERING",
        "VERIFYING",
        "COMPLETED",
        "FAILED",
        "TIMEOUT",
        "CANCELLED",
        "MAX_STEPS",
    },
    "WAITING_FOR_TOOL": {"RUNNING", "RECOVERING", "FAILED", "TIMEOUT", "CANCELLED"},
    "RECOVERING": {"RUNNING", "WAITING_FOR_TOOL", "VERIFYING", "FAILED", "TIMEOUT", "CANCELLED", "MAX_STEPS"},
    "VERIFYING": {"COMPLETED", "RECOVERING", "RUNNING", "FAILED", "TIMEOUT", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "TIMEOUT": set(),
    "CANCELLED": set(),
    "MAX_STEPS": set(),
}

AgentStatus = Literal[
    "CREATED",
    "RUNNING",
    "WAITING_FOR_TOOL",
    "RECOVERING",
    "VERIFYING",
    "COMPLETED",
    "FAILED",
    "TIMEOUT",
    "CANCELLED",
    "MAX_STEPS",
]


class AgentState(BaseModel):
    goal: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    memory_context: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    current_step: int = 0
    tool_call_count: int = 0
    model_call_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    status: AgentStatus = "CREATED"
    errors: list[str] = Field(default_factory=list)
    verification_passed: bool = False
    verification_feedback: str | None = None
    verification_result: VerificationResult | None = None
    final_output: str | None = None
    latency_ms: float = 0.0

    def transition_to(self, new_status: AgentStatus) -> None:
        """Enforces canonical execution lifecycle state transitions."""
        valid_next = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in valid_next:
            raise RuntimeError(
                f"Invalid state transition from '{self.status}' to '{new_status}'. "
                f"Allowed transitions: {list(valid_next) if valid_next else 'None (terminal state)'}"
            )
        self.status = new_status

    def to_execution_result(self) -> ExecutionResult:
        """Converts AgentState into the canonical ExecutionResult representation."""
        return ExecutionResult(
            status=self.status,
            final_output=self.final_output,
            verification=self.verification_result,
            tool_calls=self.tool_results,
            model_calls=self.model_call_count,
            errors=self.errors,
            duration_ms=self.latency_ms,
            usage={
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
            },
        )
