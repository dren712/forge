from typing import Dict
from app.tools.base import Tool
from app.tools.repository import RepositoryTool
from app.tools.file_editor import FileEditorTool
from app.tools.shell import ShellTool
from app.tools.test_runner import TestRunnerTool
from app.tools.search import SearchTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        # Register default suite of engineering tools
        self.register(RepositoryTool())
        self.register(FileEditorTool())
        self.register(ShellTool())
        self.register(TestRunnerTool())
        self.register(SearchTool())

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def get_definitions_for(self, tool_names: list[str]) -> list[dict]:
        """Returns tool schema definitions for the requested tools."""
        defs = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                defs.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                })
        return defs


default_registry = ToolRegistry()
