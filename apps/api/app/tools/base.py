from typing import Protocol, runtime_checkable, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None
    error_type: str | None = None
    status_code: int | None = None
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
    rel_str = str(relative_or_absolute)
    if Path(rel_str).is_absolute():
        target = Path(rel_str).resolve()
    else:
        target = (workspace_resolved / rel_str).resolve()

    try:
        target.relative_to(workspace_resolved)
    except ValueError:
        raise PermissionError(f"Security violation: path '{relative_or_absolute}' escapes designated workspace.")

    return target
