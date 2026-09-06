from typing import Protocol, runtime_checkable, Any
from pathlib import Path
from pydantic import BaseModel, Field
from app.agents.state import AgentState


class TaskCheck(BaseModel):
    name: str
    passed: bool
    evidence: str = ""


class BenchmarkTask(BaseModel):
    id: str
    title: str
    description: str
    goal: str = ""
    repository: str = ""
    issue: str = ""
    expected_behavior: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    hidden_constraints: list[str] = Field(default_factory=list)
    primary_skill: str = ""
    main_failure_mode: str = ""
    starting_state: dict[str, Any] = Field(default_factory=dict)
    evaluator: str = "deterministic_state"
    evaluator_config: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.goal and self.issue:
            self.goal = self.issue
        elif not self.issue and self.goal:
            self.issue = self.goal


class TaskEvaluation(BaseModel):
    task_id: str
    passed: bool
    score: float
    reason: str
    checks: list[TaskCheck] = Field(default_factory=list)
    execution_id: str = ""
    failures: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    tool_calls: int = 0
    model_calls: int = 0
    usage: dict[str, Any] = Field(default_factory=dict)
    test_stdout: str = ""
    test_stderr: str = ""
    failed_tests: list[str] = Field(default_factory=list)
    verification_passed: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


# TaskResult is an alias for TaskEvaluation to satisfy Section 13 contract
TaskResult = TaskEvaluation


@runtime_checkable
class Benchmark(Protocol):
    benchmark_id: str
    name: str
    version: str
    evaluator_version: str
    created_at: str

    def list_tasks(self) -> list[BenchmarkTask]:
        ...

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Sets up repository files and initial state in task workspace."""
        ...

    async def reset_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Resets task workspace to clean baseline state."""
        ...

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        """Evaluates whether the agent successfully solved the task."""
        ...

