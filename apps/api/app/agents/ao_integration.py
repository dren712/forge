import asyncio
import shutil
from pathlib import Path
from typing import Any
from app.core.logging import get_logger

logger = get_logger("forge.ao")


class AOOrchestratorBridge:
    """
    Integration layer with Maximor's Agent Orchestrator (AO) daemon and CLI.
    Enables spawning, monitoring, and supervising agent sessions through AO.
    """

    def __init__(self):
        self.ao_binary = shutil.which("ao") or "/Applications/Agent Orchestrator.app/Contents/Resources/daemon/ao"

    def is_available(self) -> bool:
        return Path(self.ao_binary).exists()

    async def run_doctor(self) -> dict[str, Any]:
        """Executes 'ao doctor' to check local health and agent harnesses."""
        if not self.is_available():
            return {"available": False, "error": "ao binary not found in PATH or Applications"}

        try:
            proc = await asyncio.create_subprocess_exec(
                self.ao_binary, "doctor",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "available": True,
                "exit_code": proc.returncode,
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def get_status(self) -> dict[str, Any]:
        """Executes 'ao status' to query daemon status."""
        if not self.is_available():
            return {"running": False, "error": "ao binary not found"}

        try:
            proc = await asyncio.create_subprocess_exec(
                self.ao_binary, "status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "running": proc.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            return {"running": False, "error": str(e)}


ao_bridge = AOOrchestratorBridge()
