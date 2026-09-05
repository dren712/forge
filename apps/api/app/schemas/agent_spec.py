from typing import Literal
from pydantic import BaseModel, Field


class PlannerConfig(BaseModel):
    type: Literal["none", "structured_plan", "re_act", "hierarchical"] = "none"
    max_subgoals: int = 5
    require_replan_on_error: bool = False


class MemoryConfig(BaseModel):
    type: Literal["stateless", "working_context", "scratchpad_summarized"] = "working_context"
    max_history_items: int = 30
    summarize_threshold: int = 20


class VerifierConfig(BaseModel):
    type: Literal["none", "self_check", "mandatory_tests", "strict_test_gate"] = "none"
    require_zero_failed_tests: bool = True
    enforce_before_complete: bool = True
    min_test_count: int = 1


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    retry_on_tool_failure: bool = True
    backoff_seconds: float = 1.0


class OrchestrationConfig(BaseModel):
    type: Literal["direct", "plan_execute_verify", "iterative_feedback"] = "direct"
    max_loops: int = 10


class AgentSpec(BaseModel):
    model: str = "glm-4-7-flash"
    system_prompt: str = (
        "You are an autonomous software engineering agent. "
        "Your task is to inspect the repository, identify the problem, implement the solution, and verify correctness."
    )
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    tools: list[str] = Field(default_factory=lambda: ["repository", "file_editor", "shell", "test_runner", "search"])
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)

    def canonical_dict(self) -> dict:
        """Returns normalized dictionary for deterministic serialization."""
        return self.model_dump(mode="json")
