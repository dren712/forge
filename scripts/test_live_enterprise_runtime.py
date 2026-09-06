#!/usr/bin/env python3
"""
Live verification of AgentRuntime using TensorMux provider against the enterprise tools.
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
    print("--- LIVE ENTERPRISE RUNTIME TEST (TensorMux) ---")
    temp_dir = Path(tempfile.mkdtemp())
    try:
        spec = AgentSpec(
            model=settings.tensormux_model,
            tools=["crm_api", "sentry_api", "linear_api", "slack_api", "github_api"],
        )
        provider = TensorMuxProvider(
            api_key=settings.tensormux_api_key,
            base_url=settings.tensormux_base_url,
            model=settings.tensormux_model,
        )
        runtime = AgentRuntime(spec=spec, provider=provider, tool_registry=default_registry)

        goal = (
            "Query CRM to get customer details for 'cust_acme_corp', and inspect Sentry APM error trace "
            "for service 'billing-api'. Report the customer tier, SLA, and the root cause exception."
        )

        state = await runtime.run(goal=goal, workspace=temp_dir)

        print(f"Model:              {spec.model}")
        print(f"Agent Status:       {state.status}")
        print(f"Turns / Steps:      {state.current_step}")
        print(f"Tool Calls:         {state.tool_call_count}")
        print(f"Errors Count:       {len(state.errors)}")
        print(f"Tokens Used:        {state.total_tokens}")
        print(f"Runtime Latency:    {state.latency_ms:.1f}ms")
        print(f"Verification Passed:{state.verification_passed}")
        print(f"Final Output Snippet: {(state.final_output or '')[:300]}...")

        assert state.status == "COMPLETED", f"Expected COMPLETED, got {state.status}"
        assert state.tool_call_count >= 2, f"Expected at least 2 tool calls, got {state.tool_call_count}"
        print("[SUCCESS] Live enterprise runtime execution verified with TensorMux!")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
