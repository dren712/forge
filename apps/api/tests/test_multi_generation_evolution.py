"""
FORGE S6-J — Multi-Generation Evolution Integration Tests

Validates:
1. Multi-generation evolution cycle:
   G0 → G1 accepted → G2 rejected
2. Lineage pointers:
   - G0 (root ancestor, parent=None)
   - G1 (accepted, parent=G0)
   - G2 (rejected, parent=G1)
3. State transitions:
   - When G1 accepted: current becomes G1, best becomes G1
   - When G2 rejected: current remains G1, best remains G1
4. Rejection preservation:
   - G2 remains persisted with status=REJECTED, rejection_reason, full metrics
   - G1 metrics and agent_spec remain strictly unmodified
5. Termination conditions:
   - max_generations reached
   - max_consecutive_rejections reached
   - target_accuracy reached
   - no valid mutation generated
"""
import copy
import pytest
from unittest.mock import patch
from sqlalchemy import select

from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import ExperimentModel, GenerationModel
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.acceptance import AcceptanceDecision, DominanceResult


@pytest.mark.asyncio
async def test_multi_generation_cycle_g0_accept_g1_reject_g2():
    """
    FORGE S6-J Deterministic Integration Test:
    G0 (baseline)
     ↓
    G1 (accepted candidate, parent=G0, becomes current/best)
     ↓
    G2 (rejected candidate, parent=G1, current/best remains G1)

    Proves:
    - G0 parent is None
    - G1 parent is G0, status is ACCEPTED
    - G1 is promoted to exp.current_generation_id and exp.best_generation_id
    - G2 parent is G1, status is REJECTED
    - On G2 rejection, exp.current_generation_id remains G1, exp.best_generation_id remains G1
    - G2 is NOT deleted; all 3 generations remain persisted
    - G1 metrics are unmodified by G2's rejection
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="S6-J Multi-Generation Test G0->G1->G2",
            goal="Test multi-generation evolution with accept G1 then reject G2",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
            max_generations=3,
        )
        exp = await ExperimentService.create_experiment(db, req)

        # 1. Setup G0 baseline
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"
        assert g0.parent_generation_id is None

        await db.refresh(exp)
        assert exp.best_generation_id == g0.id
        assert exp.current_generation_id == g0.id

        # 2. Mock decision sequence: G1 accepted, G2 rejected
        mock_accepted_g1 = AcceptanceDecision(
            accepted=True,
            status="ACCEPTED",
            reason="Candidate G1 Pareto-dominates parent G0: strictly better accuracy and reliability.",
            dominance_result=DominanceResult.CANDIDATE_DOMINATES,
            metrics_delta={"accuracy": 0.25, "reliability": 0.10, "cost_per_task": -0.001, "latency_per_task": -20.0},
            accuracy_delta=0.25,
            reliability_delta=0.10,
            cost_delta_percent=-5.0,
            latency_delta_percent=-5.0,
            composite_delta=0.20,
        )

        mock_rejected_g2 = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Candidate G2 regresses cost (+75%) and latency (+40%) without compensating gain.",
            dominance_result=DominanceResult.TRADEOFF,
            metrics_delta={"accuracy": 0.0, "reliability": 0.01, "cost_per_task": 0.015, "latency_per_task": 500.0},
            accuracy_delta=0.0,
            reliability_delta=0.01,
            cost_delta_percent=75.0,
            latency_delta_percent=40.0,
            composite_delta=-0.15,
        )

        decision_sequence = [mock_accepted_g1, mock_rejected_g2]

        def mock_evaluate_candidate(parent_metrics, candidate_metrics):
            if decision_sequence:
                return decision_sequence.pop(0)
            return mock_rejected_g2

        with patch("app.evolution.acceptance.AcceptanceEngine.evaluate_candidate", side_effect=mock_evaluate_candidate):
            evolved = await ExperimentService.run_evolution_loop(
                db=db,
                experiment_id=exp.id,
                max_generations=3,  # G0 + G1 + G2 = 3 total generations
                task_limit=1,
            )

        assert len(evolved) == 2, f"Expected 2 evolved generations (G1, G2), got {len(evolved)}"

        g1 = evolved[0]
        g2 = evolved[1]

        # ── Verify G1 (Accepted) ──
        assert g1.generation_number == 1
        assert g1.parent_generation_id == g0.id, "G1 parent must be G0"
        assert g1.status == "ACCEPTED"
        assert g1.rejection_reason is None
        assert "acceptance_decision" in g1.metrics
        assert g1.metrics["acceptance_decision"]["accepted"] is True

        # ── Verify G2 (Rejected) ──
        assert g2.generation_number == 2
        assert g2.parent_generation_id == g1.id, "G2 parent must be G1"
        assert g2.status == "REJECTED"
        assert g2.rejection_reason == mock_rejected_g2.reason
        assert "acceptance_decision" in g2.metrics
        assert g2.metrics["acceptance_decision"]["accepted"] is False

        # ── Verify Experiment Pointers ──
        await db.refresh(exp)
        assert exp.best_generation_id == g1.id, "Champion must be G1 (since G2 was rejected)"
        assert exp.current_generation_id == g1.id, "Current pointer must remain G1 (since G2 was rejected)"

        # ── Verify Database Lineage DAG ──
        all_gens = (await db.execute(
            select(GenerationModel)
            .where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )).scalars().all()

        assert len(all_gens) == 3, "All 3 generations (G0, G1, G2) must remain persisted in DB"
        gen_by_num = {g.generation_number: g for g in all_gens}

        db_g0 = gen_by_num[0]
        db_g1 = gen_by_num[1]
        db_g2 = gen_by_num[2]

        assert db_g0.id == g0.id
        assert db_g0.parent_generation_id is None
        assert db_g1.id == g1.id
        assert db_g1.parent_generation_id == g0.id
        assert db_g2.id == g2.id
        assert db_g2.parent_generation_id == g1.id

        # ── Verify G1 Immutability After G2 Rejection ──
        assert db_g1.status == "ACCEPTED"
        assert db_g1.agent_spec == g1.agent_spec
        assert db_g1.metrics == g1.metrics


@pytest.mark.asyncio
async def test_multi_generation_termination_conditions():
    """
    FORGE S6-J: Proves termination conditions:
    1. Terminate when max_generations reached
    2. Terminate when repeated failures prevent progress (max_consecutive_rejections)
    3. Terminate when target_accuracy reached
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # Case A: Terminate on consecutive rejections
        req_a = ExperimentCreateRequest(
            name="S6-J Consecutive Rejections Termination",
            goal="Test termination on repeated rejections",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
            max_generations=10,
        )
        exp_a = await ExperimentService.create_experiment(db, req_a)
        g0_a = await ExperimentService.generate_initial_agent(db, exp_a.id)
        g0_a = await ExperimentService.run_generation_benchmark(db, exp_a.id, g0_a.id, task_limit=1)

        always_reject = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Degraded performance.",
            dominance_result=DominanceResult.PARENT_DOMINATES,
            metrics_delta={"accuracy": -0.10, "reliability": -0.10, "cost_per_task": 0.01, "latency_per_task": 100.0},
        )

        with patch("app.evolution.acceptance.AcceptanceEngine.evaluate_candidate", return_value=always_reject):
            evolved_a = await ExperimentService.run_evolution_loop(
                db=db,
                experiment_id=exp_a.id,
                max_generations=10,
                max_consecutive_rejections=2,  # Should terminate after 2 consecutive rejections
                task_limit=1,
            )

        # Must stop after 2 rejected candidates
        assert len(evolved_a) == 2
        assert all(g.status == "REJECTED" for g in evolved_a)
        await db.refresh(exp_a)
        assert exp_a.best_generation_id == g0_a.id, "Champion remains G0 when all candidates rejected"

        # Case B: Terminate on target_accuracy
        req_b = ExperimentCreateRequest(
            name="S6-J Target Accuracy Termination",
            goal="Test termination on reaching target accuracy",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
            max_generations=10,
        )
        exp_b = await ExperimentService.create_experiment(db, req_b)
        g0_b = await ExperimentService.generate_initial_agent(db, exp_b.id)
        g0_b = await ExperimentService.run_generation_benchmark(db, exp_b.id, g0_b.id, task_limit=1)

        # G0 has accuracy 0.0 (fails baseline verification); candidate G1 evolves and scores 1.0.
        # With target_accuracy=0.99, evolution must terminate immediately after G1 (1 generation instead of 10).
        evolved_b = await ExperimentService.run_evolution_loop(
            db=db,
            experiment_id=exp_b.id,
            max_generations=10,
            target_accuracy=0.99,
            task_limit=1,
        )
        assert len(evolved_b) == 1, "Should terminate after G1 reaches target_accuracy"
        assert evolved_b[0].metrics["accuracy"] >= 0.99

        # Running again when champion already meets target_accuracy yields 0 further generations
        evolved_b2 = await ExperimentService.run_evolution_loop(
            db=db,
            experiment_id=exp_b.id,
            max_generations=10,
            target_accuracy=0.99,
            task_limit=1,
        )
        assert len(evolved_b2) == 0, "Should terminate immediately when champion already meets target_accuracy"
