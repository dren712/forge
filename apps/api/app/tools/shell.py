import time
import asyncio
import os
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult

# Block dangerous command prefixes or operations
DISALLOWED_COMMANDS = {
    "rm -rf /",
    "shutdown",
    "reboot",
    "killall",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "curl",
    "wget",
}


class ShellTool(Tool):
    name = "shell"
    description = (
        "Execute commands inside the restricted task workspace. "
        "Useful for running linters, build commands, or scripts."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute inside workspace",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds (default 30.0)",
                "default": 30.0,
            },
        },
        "required": ["command"],
    }

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        cmd = input_data.get("command", "").strip()
        timeout = float(input_data.get("timeout", 30.0))

        if not cmd:
            return ToolResult(
                success=False,
                output="",
                error="Command cannot be empty.",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Sanitize command for catastrophic patterns
        for bad in DISALLOWED_COMMANDS:
            if bad in cmd:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command rejected by security policy: forbidden pattern '{bad}'.",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

        # Scrub sensitive environment variables
        env = os.environ.copy()
        for k in list(env.keys()):
            if any(term in k.upper() for term in ("KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH")):
                env.pop(k, None)

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds.",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            stdout_str = stdout_data.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr_data.decode("utf-8", errors="replace")[:5000]
            exit_code = process.returncode

            combined_output = f"Exit code: {exit_code}\n"
            if stdout_str:
                combined_output += f"STDOUT:\n{stdout_str}\n"
            if stderr_str:
                combined_output += f"STDERR:\n{stderr_str}\n"

            return ToolResult(
                success=(exit_code == 0),
                output=combined_output,
                error=None if exit_code == 0 else f"Command exited with non-zero status {exit_code}",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                metadata={"exit_code": exit_code, "command": cmd},
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Shell execution failed: {str(e)}",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )
