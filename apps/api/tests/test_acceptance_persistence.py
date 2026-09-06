import pytest
from unittest.mock import patch
from sqlalchemy import select

from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import ExperimentModel, GenerationModel
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.acceptance import AcceptanceDecision, DominanceResult


@pytest.mark.asyncio
async def test_accepted_candidate_status_and_promotion():
    """
    FORGE S6-H: Proves that an accepted candidate:
    - status == ACCEPTED
    - exp.best_generation_id == candidate.id
    - exp.current_generation_id == candidate.id
    - acceptance_decision persisted in metrics with decision/reason/metrics_delta/dominance_result
    - parent generation remains inspectable and unchanged
    - rejected candidates are never deleted (both G0 and G1 persist)
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="S6-H Acceptance Persistence Test",
            goal="Test accepted candidate promotion",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # Create and benchmark G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"
        assert g0.metrics is not None

        await db.refresh(exp)
        assert exp.best_generation_id == g0.id

        # Force acceptance by mocking the AcceptanceEngine to return ACCEPTED
        mock_accept = AcceptanceDecision(
            accepted=True,
            status="ACCEPTED",
            reason="Candidate Pareto-dominates parent: strictly better on ['accuracy'] with no regression on any metric.",
            dominance_result=DominanceResult.CANDIDATE_DOMINATES,
            metrics_delta={
                "accuracy": 0.50,
                "reliability": 0.10,
                "cost_per_task": -0.001,
                "latency_per_task": -50.0,
            },
            accuracy_delta=0.50,
            reliability_delta=0.10,
            cost_delta_percent=-10.0,
            latency_delta_percent=-5.0,
            composite_delta=0.30,
        )

        with patch("app.evolution.acceptance.AcceptanceEngine") as MockEngine:
            MockEngine.return_value.evaluate_candidate.return_value = mock_accept
            candidate = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

        # --- Verify accepted candidate status ---
        assert candidate.status == "ACCEPTED"
        assert candidate.rejection_reason is None
        assert candidate.parent_generation_id == g0.id
        assert candidate.generation_number == 1

        # --- Verify acceptance decision persisted in metrics ---
        assert "acceptance_decision" in candidate.metrics
        ad = candidate.metrics["acceptance_decision"]
        assert ad["accepted"] is True
        assert ad["status"] == "ACCEPTED"
        assert ad["reason"] == mock_accept.reason
        assert ad["dominance_result"] == "CANDIDATE_DOMINATES"
        assert ad["parent_generation_id"] == g0.id
        assert ad["candidate_generation_id"] == candidate.id
        assert isinstance(ad["metrics_delta"], dict)
        assert ad["metrics_delta"]["accuracy"] == 0.50

        # --- Verify experiment pointers updated ---
        await db.refresh(exp)
        assert exp.best_generation_id == candidate.id, "best_generation_id must point to accepted candidate"
        assert exp.current_generation_id == candidate.id, "current_generation_id must point to accepted candidate"

        # --- Verify parent G0 remains inspectable and unchanged ---
        g0_db = (await db.execute(select(GenerationModel).where(GenerationModel.id == g0.id))).scalar_one()
        assert g0_db.status == "COMPLETED"
        assert g0_db.metrics is not None

        # --- Verify both generations persist (system never deletes generations) ---
        all_gens = (await db.execute(
            select(GenerationModel).where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )).scalars().all()
        assert len(all_gens) == 2
        assert all_gens[0].id == g0.id
        assert all_gens[1].id == candidate.id


@pytest.mark.asyncio
async def test_rejected_candidate_status_and_parent_unchanged():
    """
    FORGE S6-H: Proves that a rejected candidate:
    - status == REJECTED
    - rejection_reason is non-empty and matches decision.reason
    - exp.best_generation_id remains parent G0
    - exp.current_generation_id remains parent G0
    - acceptance_decision persisted in metrics with decision/reason/metrics_delta/dominance_result
    - rejected candidate remains fully inspectable in DB (never deleted)
    - parent generation metrics are unmodified
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        req = ExperimentCreateRequest(
            name="S6-H Rejection Persistence Test",
            goal="Test rejected candidate preservation",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)

        # Create and benchmark G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"
        assert g0.metrics is not None

        await db.refresh(exp)
        assert exp.best_generation_id == g0.id
        original_best = exp.best_generation_id
        original_current = exp.current_generation_id

        # Force rejection by mocking the AcceptanceEngine to return REJECTED
        mock_reject = AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Candidate is dominated by parent because cost and latency regress substantially without sufficient compensating improvement.",
            dominance_result=DominanceResult.TRADEOFF,
            metrics_delta={
                "accuracy": 0.04,
                "reliability": 0.02,
                "cost_per_task": 0.0074,
                "latency_per_task": 390.0,
                "cost_delta_percent": 74.0,
                "latency_delta_percent": 39.0,
            },
            accuracy_delta=0.04,
            reliability_delta=0.02,
            cost_delta_percent=74.0,
            latency_delta_percent=39.0,
            composite_delta=-0.05,
        )

        import copy
        parent_metrics_before = copy.deepcopy(g0.metrics)

        with patch("app.evolution.acceptance.AcceptanceEngine") as MockEngine:
            MockEngine.return_value.evaluate_candidate.return_value = mock_reject
            candidate = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

        # --- Verify rejected candidate status ---
        assert candidate.status == "REJECTED"
        assert candidate.rejection_reason == mock_reject.reason
        assert candidate.parent_generation_id == g0.id
        assert candidate.generation_number == 1

        # --- Verify acceptance decision persisted in metrics ---
        assert "acceptance_decision" in candidate.metrics
        ad = candidate.metrics["acceptance_decision"]
        assert ad["accepted"] is False
        assert ad["status"] == "REJECTED"
        assert ad["reason"] == mock_reject.reason
        assert ad["dominance_result"] == "TRADEOFF"
        assert ad["parent_generation_id"] == g0.id
        assert ad["candidate_generation_id"] == candidate.id
        assert isinstance(ad["metrics_delta"], dict)

        # --- Verify experiment pointers remain on parent ---
        await db.refresh(exp)
        assert exp.best_generation_id == original_best, "best_generation_id must remain G0 on rejection"
        assert exp.current_generation_id == original_current, "current_generation_id must remain on parent on rejection"

        # --- Verify parent G0 metrics are completely unmodified ---
        g0_db = (await db.execute(select(GenerationModel).where(GenerationModel.id == g0.id))).scalar_one()
        assert g0_db.metrics == parent_metrics_before, "Parent metrics must remain unmodified after rejection"
        assert g0_db.status == "COMPLETED"

        # --- Critical: Rejected candidate remains fully inspectable (never deleted) ---
        all_gens = (await db.execute(
            select(GenerationModel).where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )).scalars().all()
        assert len(all_gens) == 2, "Both G0 and rejected G1 must remain persisted"
        assert all_gens[0].id == g0.id
        assert all_gens[1].id == candidate.id
        assert all_gens[1].status == "REJECTED"
        assert all_gens[1].rejection_reason is not None
        assert all_gens[1].metrics is not None, "Rejected candidate metrics must remain inspectable"
        assert all_gens[1].agent_spec is not None, "Rejected candidate agent_spec must remain inspectable"
