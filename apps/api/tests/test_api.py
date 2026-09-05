import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db


@pytest.mark.asyncio
async def test_api_lifecycle():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        h_res = await client.get("/api/health")
        assert h_res.status_code == 200
        assert h_res.json()["product"] == "FORGE"

        # List benchmarks
        b_res = await client.get("/api/benchmarks")
        assert b_res.status_code == 200
        assert len(b_res.json()) >= 1

        # Create experiment
        create_res = await client.post(
            "/api/experiments",
            json={
                "name": "Integration Test Experiment",
                "goal": "Test automated agent generation",
                "benchmark_id": "software_engineering",
                "tools": ["repository", "file_editor", "test_runner"],
            },
        )
        assert create_res.status_code == 200
        exp_data = create_res.json()
        exp_id = exp_data["id"]
        assert exp_data["name"] == "Integration Test Experiment"

        # Generate G0
        gen_res = await client.post(f"/api/experiments/{exp_id}/generate")
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["generation_number"] == 0
        assert "agent_spec" in gen_data

        # Verify provenance
        prov_res = await client.get(f"/api/experiments/{exp_id}/provenance")
        assert prov_res.status_code == 200
        prov_data = prov_res.json()
        assert prov_data["is_valid"] is True
        assert prov_data["total_events"] >= 2
