from typing import Protocol, runtime_checkable, Any
from pathlib import Path
from pydantic import BaseModel, Field
from app.agents.state import AgentState


class BenchmarkTask(BaseModel):
    id: str
    title: str
    description: str
    repository: str
    issue: str
    expected_behavior: str
    evaluator_config: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)


class TaskEvaluation(BaseModel):
    task_id: str
    passed: bool
    score: float
    reason: str
    test_stdout: str = ""
    test_stderr: str = ""
    failed_tests: list[str] = Field(default_factory=list)
    verification_passed: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Benchmark(Protocol):
    name: str
    version: str

    def list_tasks(self) -> list[BenchmarkTask]:
        ...

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Sets up repository files and initial state in task workspace."""
        ...

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        """Evaluates whether the agent successfully solved the task."""
        ...
