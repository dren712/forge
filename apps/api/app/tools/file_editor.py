import time
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult, sanitize_path


class FileEditorTool(Tool):
    name = "file_editor"
    description = (
        "Controlled file editor for reading, creating, and editing files. "
        "Supports actions: 'create', 'replace', 'patch', 'read'."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "replace", "patch", "read"],
                "description": "The file editing action",
            },
            "path": {
                "type": "string",
                "description": "Path to file relative to workspace root",
            },
            "content": {
                "type": "string",
                "description": "Full file content for create/replace, or replacement text",
            },
            "target": {
                "type": "string",
                "description": "Exact text to find and replace when action is 'patch'",
            },
        },
        "required": ["action", "path"],
    }

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        action = input_data.get("action")
        rel_path = input_data.get("path")
        content = input_data.get("content", "")
        target_str = input_data.get("target")

        if not rel_path:
            return ToolResult(
                success=False,
                output="",
                error="Path parameter is required.",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        try:
            target_path = sanitize_path(workspace, rel_path)

            if action == "read":
                if not target_path.exists():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"File '{rel_path}' does not exist.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                data = target_path.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    success=True,
                    output=data,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            elif action in ("create", "replace"):
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    output=f"Successfully wrote {len(content)} characters to '{rel_path}'.",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    metadata={"path": rel_path, "bytes_written": len(content.encode("utf-8"))},
                )

            elif action == "patch":
                if not target_path.exists():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cannot patch non-existent file '{rel_path}'.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                existing = target_path.read_text(encoding="utf-8", errors="replace")
                if not target_str:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Action 'patch' requires 'target' substring parameter.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                if target_str not in existing:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Target substring not found in '{rel_path}'.",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    )
                updated = existing.replace(target_str, content, 1)
                target_path.write_text(updated, encoding="utf-8")
                return ToolResult(
                    success=True,
                    output=f"Successfully patched '{rel_path}'.",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    metadata={"path": rel_path, "action": "patch"},
                )

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown file_editor action '{action}'.",
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
                error=f"FileEditor error: {str(e)}",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )
