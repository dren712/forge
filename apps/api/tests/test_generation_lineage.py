import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import GenerationModel
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.acceptance import AcceptanceDecision


@pytest.mark.asyncio
async def test_generation_zero_lineage_contract():
    """
    Validates FORGE S6-B Generation 0 contract:
    - parent_generation_id is explicitly None (null in DB/JSON)
    - generation_number is 0
    - records experiment_id, generation_id, agent_spec, benchmark_id, benchmark_version, status, created_at
    - mutation_id is null for G0
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create experiment
        req = ExperimentCreateRequest(
            name="S6-B Lineage Test G0",
            goal="Test generation zero lineage contract",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # Generate G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)

        # Direct DB verification
        stmt = select(GenerationModel).where(GenerationModel.id == g0.id)
        res = await db.execute(stmt)
        persisted_g0 = res.scalar_one()

        assert persisted_g0.experiment_id == exp.id
        assert persisted_g0.id == g0.id
        assert persisted_g0.generation_number == 0
        assert persisted_g0.parent_generation_id is None, "Generation 0 parent_generation_id must be null"
        assert isinstance(persisted_g0.agent_spec, dict)
        assert persisted_g0.benchmark_id == "software_engineering"
        assert persisted_g0.benchmark_version is not None
        assert persisted_g0.mutation_id is None
        assert persisted_g0.status == "CREATED"
        assert persisted_g0.created_at is not None


@pytest.mark.asyncio
async def test_candidate_generation_lineage_and_rejected_preservation():
    """
    Validates FORGE S6-B:
    G0
    ↓
    G1 candidate
    ↓
    G1 rejected

    Proves:
    - G1 candidate links to parent G0 (parent_generation_id == G0.id)
    - G1 rejected remains persisted in SQLite with status REJECTED and rejection_reason
    - G1 records mutation_id, metrics, benchmark_id, benchmark_version, created_at
    - exp.best_generation_id is NOT corrupted (remains G0)
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="S6-B Rejection Preservation Test",
            goal="Test candidate parent link and rejected generation persistence",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        # Run G0 on 1 task to populate baseline metrics
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"
        assert g0.parent_generation_id is None

        # Verify exp best generation is G0
        await db.refresh(exp)
        assert exp.best_generation_id == g0.id

        # Mock acceptance decision to reject G1
        mock_rejected_decision = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Accuracy regressed by -50.0%.",
            accuracy_delta=-0.50,
            reliability_delta=-0.20,
            cost_delta_percent=10.0,
            latency_delta_percent=5.0,
            composite_delta=-0.40,
        )

        with patch("app.evolution.acceptance.AcceptanceEngine.evaluate_candidate", return_value=mock_rejected_decision):
            candidate_g1 = await ExperimentService.evolve_generation(db, exp.id, g0.id, task_limit=1)

        # Verify G1 candidate lineage
        assert candidate_g1.parent_generation_id == g0.id, "Candidate G1 must point to parent G0"
        assert candidate_g1.generation_number == 1
        assert candidate_g1.status == "REJECTED", "Rejected candidate must have status REJECTED"
        assert candidate_g1.rejection_reason == "Accuracy regressed by -50.0%."
        assert candidate_g1.mutation_id is not None, "Candidate must record mutation_id"
        assert candidate_g1.benchmark_id == "software_engineering"
        assert candidate_g1.benchmark_version is not None
        assert candidate_g1.metrics is not None
        assert candidate_g1.created_at is not None

        # Critical: rejected candidate MUST remain persisted in DB
        stmt = (
            select(GenerationModel)
            .where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )
        all_gens = (await db.execute(stmt)).scalars().all()
        assert len(all_gens) == 2, "Both G0 and rejected G1 must remain persisted"

        persisted_g0 = all_gens[0]
        persisted_g1 = all_gens[1]

        assert persisted_g0.id == g0.id
        assert persisted_g0.parent_generation_id is None
        assert persisted_g1.id == candidate_g1.id
        assert persisted_g1.parent_generation_id == g0.id
        assert persisted_g1.status == "REJECTED"

        # Verify experiment best_generation_id was NOT updated to rejected G1
        await db.refresh(exp)
        assert exp.best_generation_id == g0.id, "Best generation must remain G0 when G1 is rejected"


@pytest.mark.asyncio
async def test_generation_lineage_dag_traversal():
    """
    Validates multi-generation lineage chain:
    G0 (root, parent=None)
    ↓
    G1 (accepted candidate, parent=G0)
    ↓
    G2 (rejected candidate, parent=G1)

    Traverses lineage pointers back from G2 -> G1 -> G0 -> None.
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="S6-B Lineage DAG Traversal Test",
            goal="Test multi-generation lineage links",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)

        # Evolve G1 (Accepted)
        mock_accepted = AcceptanceDecision(
            accepted=True,
            status="ACCEPTED",
            reason="Accuracy improved by +25.0%.",
            accuracy_delta=0.25,
            reliability_delta=0.15,
            cost_delta_percent=-5.0,
            latency_delta_percent=-10.0,
            composite_delta=0.22,
        )
        with patch("app.evolution.acceptance.AcceptanceEngine.evaluate_candidate", return_value=mock_accepted):
            g1 = await ExperimentService.evolve_generation(db, exp.id, g0.id, task_limit=1)

        assert g1.status == "ACCEPTED"
        assert g1.parent_generation_id == g0.id
        await db.refresh(exp)
        assert exp.best_generation_id == g1.id
        assert exp.current_generation_id == g1.id

        # Evolve G2 (Rejected)
        mock_rejected = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Reliability regressed.",
            accuracy_delta=0.0,
            reliability_delta=-0.30,
            cost_delta_percent=40.0,
            latency_delta_percent=15.0,
            composite_delta=-0.15,
        )
        with patch("app.evolution.acceptance.AcceptanceEngine.evaluate_candidate", return_value=mock_rejected):
            g2 = await ExperimentService.evolve_generation(db, exp.id, g1.id, task_limit=1)

        assert g2.status == "REJECTED"
        assert g2.parent_generation_id == g1.id
        await db.refresh(exp)
        assert exp.best_generation_id == g1.id

        # Query all generations and traverse lineage DAG
        stmt = (
            select(GenerationModel)
            .where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )
        generations = (await db.execute(stmt)).scalars().all()
        gen_map = {g.id: g for g in generations}

        assert len(generations) == 3
        assert generations[0].id == g0.id
        assert generations[1].id == g1.id
        assert generations[2].id == g2.id

        # Trace backwards: G2 -> G1 -> G0 -> None
        curr = gen_map[g2.id]
        assert curr.parent_generation_id == g1.id

        curr = gen_map[curr.parent_generation_id]
        assert curr.id == g1.id
        assert curr.parent_generation_id == g0.id

        curr = gen_map[curr.parent_generation_id]
        assert curr.id == g0.id
        assert curr.parent_generation_id is None, "Root ancestor must have parent null"


@pytest.mark.asyncio
async def test_api_generation_lineage_serialization():
    """
    Validates that API responses preserve full lineage fields:
    - parent_generation_id
    - benchmark_id and benchmark_version
    - status and rejection_reason
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create experiment
        create_res = await client.post(
            "/api/experiments",
            json={
                "name": "Lineage API Serialization Test",
                "goal": "Test API serialization of lineage fields",
                "benchmark_id": "software_engineering",
                "tools": ["repository", "file_editor", "test_runner"],
            },
        )
        assert create_res.status_code == 200
        exp_id = create_res.json()["id"]

        # Generate G0
        gen_res = await client.post(f"/api/experiments/{exp_id}/generate")
        assert gen_res.status_code == 200
        g0_data = gen_res.json()

        assert g0_data["generation_number"] == 0
        assert g0_data["parent_generation_id"] is None
        assert g0_data["benchmark_id"] == "software_engineering"
        assert g0_data["benchmark_version"] is not None
        assert g0_data["status"] == "CREATED"
        assert "created_at" in g0_data

        # List generations
        list_res = await client.get(f"/api/experiments/{exp_id}/generations")
        assert list_res.status_code == 200
        gens_list = list_res.json()
        assert len(gens_list) == 1
        assert gens_list[0]["parent_generation_id"] is None
        assert gens_list[0]["benchmark_version"] is not None
