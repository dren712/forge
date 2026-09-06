#!/usr/bin/env python3
"""
Tests AgentRuntime with live TensorMuxProvider on a simple task.
"""
import sys
import asyncio
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.core.config import settings
from app.providers.tensormux import TensorMuxProvider
from app.schemas.agent_spec import AgentSpec
from app.agents.runtime import AgentRuntime
from app.tools.registry import default_registry


async def main():
    print("Testing AgentRuntime with TensorMuxProvider...")
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Seed test workspace
        (temp_dir / "app.py").write_text("print('hello world')\n")

        spec = AgentSpec(
            model=settings.tensormux_model,
            tools=["file_editor", "repository"],
        )
        provider = TensorMuxProvider(
            api_key=settings.tensormux_api_key,
            base_url=settings.tensormux_base_url,
            model=settings.tensormux_model,
        )
        runtime = AgentRuntime(spec=spec, provider=provider, tool_registry=default_registry)

        state = await runtime.run(
            goal="Inspect app.py and report what it does.",
            workspace=temp_dir,
        )

        print(f"Agent Status:      {state.status}")
        print(f"Steps:             {state.current_step}")
        print(f"Tool Calls:        {state.tool_call_count}")
        print(f"Tokens:            {state.total_tokens}")
        print(f"Latency:           {state.latency_ms:.1f}ms")
        print(f"Errors:            {state.errors}")
        assert state.status == "COMPLETED"
        assert state.tool_call_count >= 1
        print("[SUCCESS] AgentRuntime executed with TensorMuxProvider successfully!")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
