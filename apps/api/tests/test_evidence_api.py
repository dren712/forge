"""
FORGE S7-D — Evidence API Tests

Validates read-only evidence APIs inspecting the existing evidence chain to answer:
1. Why did this agent fail? (failures)
2. What did it learn? (memory)
3. What changed? (mutations)
4. Which generation introduced the change? (generation, mutations[].generation_id)
5. Was the candidate accepted? (decision.accepted, decision.status)
6. What evidence supports the decision? (decision.reason, metrics_delta, dominance_result)
7. Is the provenance chain valid? (provenance.valid)
"""
import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import (
    ExperimentModel,
    GenerationModel,
    MutationModel,
    ToolMemoryModel,
    TraceEventModel,
)
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.acceptance import AcceptanceDecision, DominanceResult


@pytest.mark.asyncio
async def test_evidence_api_not_found():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/experiments/nonexistent-exp-id/evidence")
        assert res.status_code == 404
        assert "Experiment nonexistent-exp-id not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_evidence_api_generation_not_found():
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Gen Not Found Test",
            goal="Test 404 on missing generation",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/experiments/{exp.id}/evidence?generation_id=missing-gen-id")
        assert res.status_code == 404
        assert "Generation missing-gen-id not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_evidence_api_no_generations():
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Empty Gen Test",
            goal="Test evidence when no generations exist yet",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/experiments/{exp.id}/evidence")
        assert res.status_code == 200
        data = res.json()

        assert data["generation"] is None
        assert data["parent_generation"] is None
        assert data["metrics"] == {}
        assert data["failures"] == []
        assert data["memory"] == []
        assert data["mutations"] == []
        assert data["decision"] == {}
        assert "provenance" in data
        assert data["provenance"]["valid"] is True


@pytest.mark.asyncio
async def test_evidence_api_baseline_g0():
    """
    Validates evidence response on evaluated baseline G0:
    - Answers why agent failed
    - Metrics populated
    - Provenance valid
    - Decision indicates baseline status
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence G0 Baseline Test",
            goal="Test G0 evidence",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=2)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/experiments/{exp.id}/evidence")
        assert res.status_code == 200
        data = res.json()

        assert data["generation"] == g0.id
        assert data["parent_generation"] is None
        assert isinstance(data["metrics"], dict)
        assert "accuracy" in data["metrics"]
        assert "reliability" in data["metrics"]

        # Why did this agent fail?
        assert isinstance(data["failures"], list)
        if data["metrics"]["accuracy"] < 1.0:
            assert len(data["failures"]) >= 1
            f0 = data["failures"][0]
            assert "failure_type" in f0
            assert "root_cause" in f0

        # Provenance
        assert data["provenance"]["valid"] is True
        assert data["provenance"]["total_events"] >= 2

        # Decision on G0
        assert data["decision"]["status"] == "COMPLETED"
        assert data["decision"]["accepted"] is True


@pytest.mark.asyncio
async def test_evidence_api_accepted_candidate_g1_and_causal_relationships():
    """
    Full end-to-end evidence inspection proving answers to all 7 required questions:
    1. Why did this agent fail?
    2. What did it learn?
    3. What changed?
    4. Which generation introduced the change?
    5. Was the candidate accepted?
    6. What evidence supports the decision?
    7. Is the provenance chain valid?
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Full Causal Chain Test",
            goal="Resolve SWE issues with verified causal links",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # 1. Create and evaluate G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)

        # 2. Evaluate candidate G1 with Pareto acceptance
        mock_decision = AcceptanceDecision(
            accepted=True,
            status="ACCEPTED",
            reason="Candidate strictly Pareto-dominates parent on accuracy (+50.0%) without cost/latency regression.",
            dominance_result=DominanceResult.CANDIDATE_DOMINATES,
            metrics_delta={
                "accuracy": 0.50,
                "reliability": 0.20,
                "cost_per_task": -0.0005,
                "latency_per_task": -40.0,
            },
            accuracy_delta=0.50,
            reliability_delta=0.20,
            cost_delta_percent=-5.0,
            latency_delta_percent=-4.0,
            composite_delta=0.35,
        )

        with patch("app.evolution.acceptance.AcceptanceEngine") as MockEngine:
            MockEngine.return_value.evaluate_candidate.return_value = mock_decision
            candidate = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

        # 3. Add explicit memory record linked to execution & failure
        exec_id = str(uuid.uuid4())
        fail_id = str(uuid.uuid4())
        refl_id = str(uuid.uuid4())
        mem_id = str(uuid.uuid4())

        mem_record = ToolMemoryModel(
            id=mem_id,
            experiment_id=exp.id,
            tool_name="test_runner",
            category="WORKFLOW_DEPENDENCY",
            pattern_trigger="pytest exit code 1",
            learned_rule="Always run unit tests before declaring task completion",
            evidence="Observed verification failure in baseline evaluation",
            confidence=0.95,
            observation_count=2,
            execution_id=exec_id,
            failure_id=fail_id,
            reflection_id=refl_id,
        )
        db.add(mem_record)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Query evidence for the experiment (defaults to current generation = G1 candidate)
        res = await client.get(f"/api/experiments/{exp.id}/evidence")
        assert res.status_code == 200
        data = res.json()

        # Schema & Identity
        assert data["generation"] == candidate.id
        assert data["parent_generation"] == g0.id

        # Question 1: Why did this agent fail? (G0 baseline evidence query)
        g0_res = await client.get(f"/api/experiments/{exp.id}/evidence?generation_id={g0.id}")
        assert g0_res.status_code == 200
        g0_data = g0_res.json()
        assert len(g0_data["failures"]) >= 1
        assert "failure_type" in g0_data["failures"][0]
        assert "root_cause" in g0_data["failures"][0]

        # Question 2: What did it learn? (Memory)
        assert len(data["memory"]) >= 1
        target_mem = next(m for m in data["memory"] if m["id"] == mem_id)
        assert target_mem["tool_name"] == "test_runner"
        assert target_mem["learned_rule"] == "Always run unit tests before declaring task completion"
        assert target_mem["execution_id"] == exec_id
        assert target_mem["failure_id"] == fail_id
        assert target_mem["reflection_id"] == refl_id

        # Question 3: What changed? (Mutations)
        assert len(data["mutations"]) >= 1
        mut = data["mutations"][0]
        assert mut["id"] == candidate.mutation_id
        assert "mutation_type" in mut
        assert "target" in mut
        assert "before" in mut
        assert "after" in mut
        assert "reason" in mut

        # Question 4: Which generation introduced the change?
        assert data["generation"] == candidate.id
        assert mut["generation_id"] == g0.id

        # Question 5: Was the candidate accepted?
        assert data["decision"]["accepted"] is True
        assert data["decision"]["status"] == "ACCEPTED"

        # Question 6: What evidence supports the decision?
        assert data["decision"]["reason"] == mock_decision.reason
        assert data["decision"]["dominance_result"] == "CANDIDATE_DOMINATES"
        assert data["decision"]["metrics_delta"]["accuracy"] == 0.50
        assert data["decision"]["parent_generation_id"] == g0.id
        assert data["decision"]["candidate_generation_id"] == candidate.id

        # Question 7: Is the provenance chain valid?
        assert data["provenance"]["valid"] is True
        assert data["provenance"]["total_events"] >= 3
        assert "latest_hash" in data["provenance"]
        assert "genesis_hash" in data["provenance"]


@pytest.mark.asyncio
async def test_evidence_api_rejected_candidate():
    """
    Validates evidence response when a candidate is REJECTED by Pareto gate:
    - decision.accepted is False
    - decision.status == 'REJECTED'
    - decision.reason contains rejection rationale
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Rejected Candidate Test",
            goal="Test rejected candidate evidence",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)

        mock_rejection = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Candidate is dominated: cost regressed by +75% and latency by +40% with no compensating improvement.",
            dominance_result=DominanceResult.PARENT_DOMINATES,
            metrics_delta={
                "accuracy": 0.0,
                "reliability": -0.10,
                "cost_per_task": 0.005,
                "latency_per_task": 600.0,
            },
            accuracy_delta=0.0,
            reliability_delta=-0.10,
            cost_delta_percent=75.0,
            latency_delta_percent=40.0,
            composite_delta=-0.30,
        )

        with patch("app.evolution.acceptance.AcceptanceEngine") as MockEngine:
            MockEngine.return_value.evaluate_candidate.return_value = mock_rejection
            candidate = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Query specific rejected candidate generation
        res = await client.get(f"/api/experiments/{exp.id}/evidence?generation_id={candidate.id}")
        assert res.status_code == 200
        data = res.json()

        assert data["generation"] == candidate.id
        assert data["parent_generation"] == g0.id
        assert data["decision"]["accepted"] is False
        assert data["decision"]["status"] == "REJECTED"
        assert "dominated" in data["decision"]["reason"]
        assert data["decision"]["dominance_result"] == "PARENT_DOMINATES"
        assert data["provenance"]["valid"] is True


@pytest.mark.asyncio
async def test_evidence_api_provenance_tampering_detection():
    """
    Validates that cryptographic tampering with an event causes
    provenance.valid to be False in the evidence response.
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Tampering Detection Test",
            goal="Test provenance tampering in evidence API",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)

        # Tamper with an event in trace_events
        ev = (await db.execute(
            select(TraceEventModel).where(TraceEventModel.experiment_id == exp.id).limit(1)
        )).scalar_one()
        ev.event_hash = "deadbeef" * 8
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/experiments/{exp.id}/evidence")
        assert res.status_code == 200
        data = res.json()

        assert data["provenance"]["valid"] is False
        assert data["provenance"]["broken_index"] is not None


@pytest.mark.asyncio
async def test_evidence_api_generation_alias_endpoint():
    """
    Validates GET /api/generations/{id}/evidence alias.
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="Evidence Alias Test",
            goal="Test generation alias endpoint",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/generations/{g0.id}/evidence")
        assert res.status_code == 200
        data = res.json()
        assert data["generation"] == g0.id
        assert data["provenance"]["valid"] is True

        # Test nonexistent generation ID
        bad_res = await client.get("/api/generations/nonexistent-gen/evidence")
        assert bad_res.status_code == 404
