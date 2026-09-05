from typing import Protocol, runtime_checkable, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        """Execute the tool within the designated sandboxed workspace."""
        ...


def sanitize_path(workspace: Path, relative_or_absolute: str | Path) -> Path:
    """
    Ensures that the target path resolves strictly inside the workspace boundary.
    Raises PermissionError if path traversal is attempted.
    """
    workspace_resolved = workspace.resolve()
    target = (workspace_resolved / relative_or_absolute).resolve()

    if not str(target).startswith(str(workspace_resolved)):
        raise PermissionError(f"Security violation: path '{relative_or_absolute}' escapes designated workspace.")

    return target
