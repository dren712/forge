import time
import os
import re
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult, sanitize_path


class SearchTool(Tool):
    name = "search"
    description = "Search codebase for exact text or regex patterns across files."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text or regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Subdirectory to restrict search in (default is workspace root)",
                "default": ".",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether search is case sensitive (default false)",
                "default": False,
            },
        },
        "required": ["query"],
    }

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        query = input_data.get("query", "").strip()
        rel_path = input_data.get("path", ".")
        case_sensitive = input_data.get("case_sensitive", False)
        workspace_resolved = workspace.resolve()

        if not query:
            return ToolResult(
                success=False,
                output="",
                error="Query string is required.",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        try:
            target_dir = sanitize_path(workspace_resolved, rel_path)
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(query, flags)

            matches = []
            max_matches = 50

            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache", ".venv"}]
                for f in files:
                    if len(matches) >= max_matches:
                        break
                    file_path = (Path(root) / f).resolve()
                    if file_path.stat().st_size > 500_000:
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        for idx, line in enumerate(content.splitlines(), start=1):
                            if pattern.search(line):
                                rel = file_path.relative_to(workspace_resolved)
                                matches.append(f"{rel}:{idx}: {line.strip()}")
                                if len(matches) >= max_matches:
                                    break
                    except Exception:
                        continue

            if matches:
                output = f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)
            else:
                output = f"No matches found for '{query}' in '{rel_path}'."

            return ToolResult(
                success=True,
                output=output,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )
