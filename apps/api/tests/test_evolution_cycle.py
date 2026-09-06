"""
FORGE S6-I — Complete One Evolution Cycle (End-to-End Integration Test)

Exercises the FULL service-level pipeline with DB persistence:

    G0
     ↓ Benchmark
     ↓ Metrics
     ↓ Failure clustering
     ↓ Mutation proposal
     ↓ Candidate AgentSpec
     ↓ Candidate benchmark (same version, reset tasks)
     ↓ Candidate metrics
     ↓ Pareto acceptance
     ↓ G1 ACCEPTED or REJECTED

Verifies:
- Same benchmark version used for G0 and G1
- Task environments reset between generations
- All executions persisted (G0 + G1)
- Mutation persisted with grounded evidence
- Candidate generation persisted with parent link
- Acceptance decision persisted (status, reason, metrics_delta, dominance_result)
- Provenance chain preserved
- Rejected candidate preserved if rejected
- Parent metrics untouched
"""
import copy
import pytest
from sqlalchemy import select

from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import (
    ExperimentModel,
    GenerationModel,
    ExecutionModel,
    MutationModel,
    TraceEventModel,
)
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.evolution.mutation import SUPPORTED_MUTATION_TARGETS
from app.provenance.hasher import verify_event_chain
from app.tracing.events import EventType, TraceEvent


@pytest.mark.asyncio
async def test_complete_evolution_cycle_g0_to_g1():
    """
    End-to-end: G0 → benchmark → failure clustering → mutation → candidate benchmark
    → Pareto acceptance → G1 persisted with ACCEPTED or REJECTED.
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # ── 1. Create experiment ──
        req = ExperimentCreateRequest(
            name="S6-I Complete Evolution Cycle",
            goal="End-to-end test of one full G0→G1 evolution cycle",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner", "shell", "search"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        assert exp.status == "CREATED"

        # ── 2. Generate G0 AgentSpec ──
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        assert g0.generation_number == 0
        assert g0.parent_generation_id is None
        assert g0.status == "CREATED"
        assert g0.agent_spec is not None

        # ── 3. Run G0 benchmark ──
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"
        assert g0.metrics is not None
        assert "accuracy" in g0.metrics
        assert "reliability" in g0.metrics
        assert "avg_cost_per_task" in g0.metrics
        assert "avg_latency_ms" in g0.metrics
        assert "composite_score" in g0.metrics

        # Snapshot parent state for immutability verification
        g0_metrics_snapshot = copy.deepcopy(g0.metrics)
        g0_spec_snapshot = copy.deepcopy(g0.agent_spec)
        g0_benchmark_id = g0.benchmark_id
        g0_benchmark_version = g0.benchmark_version

        await db.refresh(exp)
        assert exp.best_generation_id == g0.id

        # Verify G0 executions persisted
        g0_execs = (await db.execute(
            select(ExecutionModel).where(ExecutionModel.generation_id == g0.id)
        )).scalars().all()
        assert len(g0_execs) == 1
        g0_task_id = g0_execs[0].task_id

        # ── 4. Run one evolution cycle: G0 → G1 ──
        # This single call exercises:
        # - failure clustering (from G0 metrics)
        # - mutation proposal (grounded in failures)
        # - candidate AgentSpec construction
        # - candidate benchmark (same version, tasks reset)
        # - candidate metrics computation
        # - Pareto acceptance gate
        # - persistence of everything
        g1 = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)

        # ── 5. Verify G1 generation metadata ──
        assert g1.id != g0.id
        assert g1.parent_generation_id == g0.id
        assert g1.generation_number == 1
        assert g1.agent_spec is not None
        assert g1.metrics is not None

        # Same benchmark version
        assert g1.benchmark_id == g0_benchmark_id
        assert g1.benchmark_version == g0_benchmark_version

        # ── 6. Verify acceptance decision persisted ──
        assert g1.status in ("ACCEPTED", "REJECTED"), f"G1 status must be ACCEPTED or REJECTED, got {g1.status}"
        assert "acceptance_decision" in g1.metrics
        ad = g1.metrics["acceptance_decision"]
        assert "accepted" in ad
        assert "status" in ad
        assert "reason" in ad
        assert "dominance_result" in ad
        assert "metrics_delta" in ad
        assert ad["parent_generation_id"] == g0.id
        assert ad["candidate_generation_id"] == g1.id
        assert ad["status"] == g1.status
        assert isinstance(ad["reason"], str) and len(ad["reason"]) > 0

        if g1.status == "REJECTED":
            assert g1.rejection_reason is not None
            assert g1.rejection_reason == ad["reason"]
        else:
            assert g1.rejection_reason is None

        # ── 7. Verify mutation persisted ──
        assert g1.mutation_id is not None
        mutation_db = (await db.execute(
            select(MutationModel).where(MutationModel.id == g1.mutation_id)
        )).scalar_one()
        assert mutation_db.target in SUPPORTED_MUTATION_TARGETS
        assert mutation_db.before_json is not None
        assert mutation_db.after_json is not None
        assert mutation_db.before_json != mutation_db.after_json
        assert len(mutation_db.reason) > 0
        assert len(mutation_db.observed_failure) > 0
        assert len(mutation_db.expected_effect) > 0

        # ── 8. Verify candidate executions persisted ──
        g1_execs = (await db.execute(
            select(ExecutionModel).where(ExecutionModel.generation_id == g1.id)
        )).scalars().all()
        assert len(g1_execs) == 1
        assert g1_execs[0].task_id == g0_task_id, "Candidate must evaluate the exact same task as parent"
        assert g1_execs[0].metrics is not None

        # ── 9. Verify experiment pointers reflect acceptance ──
        await db.refresh(exp)
        if g1.status == "ACCEPTED":
            assert exp.best_generation_id == g1.id
            assert exp.current_generation_id == g1.id
        else:
            assert exp.best_generation_id == g0.id, "Rejected candidate must not update best_generation_id"

        # ── 10. Verify parent G0 is completely unchanged ──
        g0_db = (await db.execute(
            select(GenerationModel).where(GenerationModel.id == g0.id)
        )).scalar_one()
        assert g0_db.metrics == g0_metrics_snapshot, "Parent metrics must remain untouched"
        assert g0_db.agent_spec == g0_spec_snapshot
        assert g0_db.status == "COMPLETED"

        # ── 11. Verify both generations persisted (rejected never deleted) ──
        all_gens = (await db.execute(
            select(GenerationModel)
            .where(GenerationModel.experiment_id == exp.id)
            .order_by(GenerationModel.generation_number.asc())
        )).scalars().all()
        assert len(all_gens) == 2
        assert all_gens[0].id == g0.id
        assert all_gens[1].id == g1.id

        # ── 12. Verify provenance chain ──
        events_db = (await db.execute(
            select(TraceEventModel)
            .where(TraceEventModel.experiment_id == exp.id)
            .order_by(TraceEventModel.timestamp)
        )).scalars().all()
        assert len(events_db) >= 5, f"Expected at least 5 provenance events, got {len(events_db)}"

        events = [
            TraceEvent(
                event_id=e.id,
                experiment_id=e.experiment_id,
                generation_id=e.generation_id,
                execution_id=e.execution_id,
                timestamp=e.timestamp,
                type=EventType(e.type),
                payload=e.payload,
                previous_event_hash=e.previous_event_hash,
                event_hash=e.event_hash,
            )
            for e in events_db
        ]
        is_valid, broken_idx, msg = verify_event_chain(events)
        assert is_valid is True, f"Provenance chain broken at index {broken_idx}: {msg}"

        # ── 13. Verify candidate metrics are real (not fabricated) ──
        assert g1.metrics["total_tasks"] >= 1
        assert 0.0 <= g1.metrics["accuracy"] <= 1.0
        assert 0.0 <= g1.metrics["reliability"] <= 1.0
        assert g1.metrics["avg_cost_per_task"] >= 0.0
        assert g1.metrics["avg_latency_ms"] >= 0.0
