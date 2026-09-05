import time
import os
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult, sanitize_path


class RepositoryTool(Tool):
    name = "repository"
    description = (
        "Inspect and explore files within the workspace repository. "
        "Supports actions: 'list_files', 'read_file', 'inspect_dir'."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_files", "read_file", "inspect_dir"],
                "description": "The inspection action to perform",
            },
            "path": {
                "type": "string",
                "description": "Relative path to file or directory",
                "default": ".",
            },
        },
        "required": ["action"],
    }

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        action = input_data.get("action", "list_files")
        rel_path = input_data.get("path", ".")
        workspace_resolved = workspace.resolve()

        try:
            target = sanitize_path(workspace_resolved, rel_path)

            if action in ("list_files", "inspect_dir"):
                if not target.exists():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Directory '{rel_path}' does not exist.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                entries = []
                for root, dirs, files in os.walk(target):
                    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache", ".venv"}]
                    for f in files:
                        p = (Path(root) / f).resolve()
                        entries.append(str(p.relative_to(workspace_resolved)))
                output_str = "\n".join(sorted(entries)) if entries else "(empty directory)"
                return ToolResult(
                    success=True,
                    output=f"Files in repository ({len(entries)} items):\n{output_str}",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            elif action == "read_file":
                if not target.is_file():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"File '{rel_path}' not found.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                content = target.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    success=True,
                    output=content,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown repository action: {action}",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

        except PermissionError as pe:
            return ToolResult(
                success=False,
                output="",
                error=str(pe),
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Repository tool error: {str(e)}",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )
