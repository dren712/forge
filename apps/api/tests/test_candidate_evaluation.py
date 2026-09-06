import copy
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import ExperimentModel, GenerationModel, ExecutionModel, MutationModel
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.mutation import SUPPORTED_MUTATION_TARGETS


@pytest.mark.asyncio
async def test_candidate_evaluation_pipeline_integration():
    """
    Validates FORGE S6-F Candidate Evaluation pipeline:
    G0
    → candidate mutation
    → candidate run
    → candidate metrics

    Requirements verified:
    1. Candidate runs against the SAME benchmark version and task set as parent.
    2. Benchmark state is reset before execution.
    3. Parent generation and its metrics are strictly preserved.
    4. Candidate generation is created with valid parent reference.
    5. Real tasks executed, real metrics calculated.
    6. Candidate execution results and generation metrics persisted in DB.
    7. No acceptance/rejection decision made (parent remains best_generation_id).
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # 1. Create experiment
        req = ExperimentCreateRequest(
            name="S6-F Candidate Evaluation Integration",
            goal="Test automated candidate evaluation pipeline",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner", "shell", "search"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # 2. Generate G0 and run benchmark on 1 task
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)

        assert g0.metrics is not None
        assert g0.status == "COMPLETED"
        assert g0.parent_generation_id is None

        # Snapshot parent state to verify immutability
        parent_metrics_snapshot = copy.deepcopy(g0.metrics)
        parent_spec_snapshot = copy.deepcopy(g0.agent_spec)
        parent_status_snapshot = g0.status

        # Query parent task IDs
        parent_exec_stmt = select(ExecutionModel).where(ExecutionModel.generation_id == g0.id)
        parent_execs = (await db.execute(parent_exec_stmt)).scalars().all()
        assert len(parent_execs) == 1
        parent_task_id = parent_execs[0].task_id

        # 3. Evaluate candidate generation (S6-F)
        candidate_gen = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

        # 4. Verify candidate generation metadata and lineage
        assert candidate_gen.id != g0.id
        assert candidate_gen.parent_generation_id == g0.id
        assert candidate_gen.generation_number == 1
        assert candidate_gen.benchmark_id == g0.benchmark_id
        assert candidate_gen.benchmark_version == g0.benchmark_version
        assert candidate_gen.mutation_id is not None
        assert candidate_gen.status == "COMPLETED"
        assert candidate_gen.rejection_reason is None

        # 5. Verify mutation was generated and persisted
        mut_stmt = select(MutationModel).where(MutationModel.id == candidate_gen.mutation_id)
        mutation_db = (await db.execute(mut_stmt)).scalar_one()
        assert mutation_db.target in SUPPORTED_MUTATION_TARGETS
        assert mutation_db.before_json is not None
        assert mutation_db.after_json is not None
        assert mutation_db.before_json != mutation_db.after_json
        assert len(mutation_db.reason) > 0

        # 6. Verify real candidate metrics and task execution persistence
        assert candidate_gen.metrics is not None
        assert "accuracy" in candidate_gen.metrics
        assert "reliability" in candidate_gen.metrics
        assert "composite_score" in candidate_gen.metrics
        assert "avg_cost_per_task" in candidate_gen.metrics
        assert "avg_latency_ms" in candidate_gen.metrics

        cand_exec_stmt = select(ExecutionModel).where(ExecutionModel.generation_id == candidate_gen.id)
        cand_execs = (await db.execute(cand_exec_stmt)).scalars().all()
        assert len(cand_execs) == 1
        assert cand_execs[0].task_id == parent_task_id, "Candidate must evaluate the exact same task as parent"
        assert cand_execs[0].metrics is not None

        # 7. Invariant: Parent generation and metrics strictly unchanged
        g0_refreshed = (await db.execute(select(GenerationModel).where(GenerationModel.id == g0.id))).scalar_one()
        assert g0_refreshed.metrics == parent_metrics_snapshot, "Parent metrics must remain unmodified"
        assert g0_refreshed.agent_spec == parent_spec_snapshot
        assert g0_refreshed.status == parent_status_snapshot

        # 8. Invariant: No acceptance/rejection implemented yet (best_generation remains G0)
        await db.refresh(exp)
        assert exp.best_generation_id == g0.id, "best_generation_id must not be altered during candidate evaluation"


@pytest.mark.asyncio
async def test_candidate_evaluation_via_api():
    """
    Validates candidate evaluation endpoint:
    POST /api/experiments/{id}/candidate
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create experiment
        create_res = await client.post(
            "/api/experiments",
            json={
                "name": "Candidate Evaluation API Test",
                "goal": "Test candidate evaluation HTTP route",
                "benchmark_id": "software_engineering",
                "tools": ["repository", "file_editor", "test_runner"],
            },
        )
        assert create_res.status_code == 200
        exp_id = create_res.json()["id"]

        # Generate G0
        gen_res = await client.post(f"/api/experiments/{exp_id}/generate")
        assert gen_res.status_code == 200
        g0_id = gen_res.json()["id"]

        # Run G0
        run_res = await client.post(f"/api/experiments/{exp_id}/run", params={"task_limit": 1})
        assert run_res.status_code == 200
        assert run_res.json()["metrics"] is not None

        # Evaluate candidate
        cand_res = await client.post(f"/api/experiments/{exp_id}/candidate", params={"task_limit": 1})
        assert cand_res.status_code == 200
        cand_data = cand_res.json()

        assert cand_data["parent_generation_id"] == g0_id
        assert cand_data["generation_number"] == 1
        assert cand_data["metrics"] is not None
        assert cand_data["status"] == "COMPLETED"
        assert cand_data["rejection_reason"] is None
        assert cand_data["mutation_id"] is not None
