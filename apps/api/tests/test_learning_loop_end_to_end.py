import pytest
from app.core.database import AsyncSessionLocal, init_db
from app.services.experiment_service import ExperimentService
from app.schemas.api import ExperimentCreateRequest


@pytest.mark.asyncio
async def test_learning_loop_end_to_end():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create experiment
        req = ExperimentCreateRequest(
            name="Track 1 Multi-App Autonomous Agent",
            goal="Automate multi-app customer incident escalation across Linear, Slack, and CRM.",
            benchmark_id="third_party_automation",
            tools=["linear_api", "slack_api", "crm_api"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        assert exp.id is not None

        # Execute Learning Loop
        report = await ExperimentService.run_learning_loop(db, exp.id)
        assert report["status"] == "SUCCESS"

        # Assert Run 1 vs Run 2 deltas
        r1 = report["run_1_cold"]
        r2 = report["run_2_warm"]
        delta = report["efficiency_delta"]

        assert r1["tool_calls"] > r2["tool_calls"]
        assert r1["errors_encountered"] == 3
        assert r2["errors_encountered"] == 0
        assert r2["cost_usd"] < r1["cost_usd"]
        assert r2["latency_ms"] < r1["latency_ms"]
        assert delta["errors_prevented"] == 3

        # Assert Tool Memories persisted
        memories = await ExperimentService.get_tool_memories(db, exp.id)
        assert len(memories) >= 4
        categories = {m["category"] for m in memories}
        assert "SCHEMA_QUIRK" in categories
        assert "CONTEXTUAL_LOGIC" in categories
        assert "WORKFLOW_DEPENDENCY" in categories
