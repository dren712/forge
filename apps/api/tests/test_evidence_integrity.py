"""
FORGE S7-E — Evidence Integrity Verification Tests

Verifies that:
1. Complete deterministic experiment evidence can reconstruct the causal chain:
   Goal -> Generation -> Execution -> Failure -> Reflection -> Memory -> Mutation -> Candidate -> Acceptance/Rejection -> Provenance
2. Normal evidence has valid cryptographic provenance.
3. A test-controlled copy with tampered event payload or hash is detected as invalid.
4. The production database is untouched and remains strictly valid.
"""
import copy
import pytest
from sqlalchemy import select

from app.core.database import init_db, AsyncSessionLocal
from app.schemas.api import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.provenance.hasher import verify_event_chain
from app.tracing.events import EventType, TraceEvent
from app.models.entities import (
    ExperimentModel,
    GenerationModel,
    ExecutionModel,
    MutationModel,
    TraceEventModel,
    ToolMemoryModel,
)


@pytest.mark.asyncio
async def test_evidence_integrity_reconstruction_and_tampering():
    """
    Executes a complete G0 -> G1 evolution cycle in deterministic mode,
    validates the causal trace identifiers across every transition,
    and runs a tamper test against a controlled copy.
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # 1. Goal
        req = ExperimentCreateRequest(
            name="S7-E Integrity Automated Verification",
            goal="Verify full causal chain reconstruction and cryptographic tamper resistance",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "test_runner"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        assert exp.id is not None
        assert exp.goal == req.goal

        # 2. Generation G0
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        assert g0.id is not None
        assert g0.experiment_id == exp.id
        assert g0.generation_number == 0

        # 3. Execution & Failure in G0
        g0 = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=1)
        assert g0.status == "COMPLETED"

        exec_stmt = select(ExecutionModel).where(ExecutionModel.generation_id == g0.id)
        g0_execs = (await db.execute(exec_stmt)).scalars().all()
        assert len(g0_execs) == 1
        g0_exec = g0_execs[0]
        assert g0_exec.experiment_id == exp.id
        assert g0_exec.generation_id == g0.id

        # Trace events in G0
        g0_events_stmt = select(TraceEventModel).where(TraceEventModel.generation_id == g0.id)
        g0_events = (await db.execute(g0_events_stmt)).scalars().all()
        assert len(g0_events) >= 5

        # Verify Failure trace event
        fail_events = [e for e in g0_events if e.type == EventType.FAILURE_DETECTED.value]
        assert len(fail_events) >= 1
        fail_ev = fail_events[0]
        assert fail_ev.execution_id == g0_exec.id
        assert "failure_id" in fail_ev.payload
        assert fail_ev.payload["execution_id"] == g0_exec.id

        # Verify Reflection trace events
        refl_starts = [e for e in g0_events if e.type == EventType.SELF_REFLECTION_STARTED.value]
        refl_completes = [e for e in g0_events if e.type == EventType.SELF_REFLECTION_COMPLETED.value]
        assert len(refl_starts) >= 1
        assert len(refl_completes) >= 1
        assert refl_completes[0].execution_id == g0_exec.id

        # 4. Candidate Generation G1 & Mutation
        g1 = await ExperimentService.evaluate_candidate(db, exp.id, g0.id, task_limit=1)
        assert g1.id is not None
        assert g1.parent_generation_id == g0.id
        assert g1.generation_number == 1
        assert g1.mutation_id is not None

        # Verify Mutation record
        mut_stmt = select(MutationModel).where(MutationModel.id == g1.mutation_id)
        mut = (await db.execute(mut_stmt)).scalar_one()
        assert mut.generation_id == g0.id
        assert mut.failure_cluster_id is not None
        assert isinstance(mut.failure_ids, list)

        # 5. Acceptance / Rejection Decision
        assert g1.decision_id is not None
        assert g1.status in ("ACCEPTED", "REJECTED")
        assert "acceptance_decision" in g1.metrics
        ad = g1.metrics["acceptance_decision"]
        assert ad["decision_id"] == g1.decision_id
        assert ad["candidate_generation_id"] == g1.id
        assert ad["parent_generation_id"] == g0.id
        assert ad["mutation_id"] == g1.mutation_id

        # 6. Provenance Verification on Untouched DB
        prov = await ExperimentService.verify_provenance(db, exp.id)
        assert prov["is_valid"] is True
        assert prov["broken_index"] is None
        assert prov["total_events"] >= 10

        # 7. Tamper Test on Test-Controlled Copy
        events_db = (await db.execute(
            select(TraceEventModel)
            .where(TraceEventModel.experiment_id == exp.id)
            .order_by(TraceEventModel.timestamp)
        )).scalars().all()

        original_trace = [
            TraceEvent(
                event_id=e.id,
                experiment_id=e.experiment_id,
                generation_id=e.generation_id,
                execution_id=e.execution_id,
                timestamp=e.timestamp,
                type=EventType(e.type),
                payload=copy.deepcopy(e.payload),
                previous_event_hash=e.previous_event_hash,
                event_hash=e.event_hash,
            )
            for e in events_db
        ]

        # Verify normal copy is valid
        normal_valid, normal_broken, normal_msg = verify_event_chain(original_trace)
        assert normal_valid is True
        assert normal_broken is None

        # Case A: Tamper with event payload in controlled copy
        tampered_payload_trace = copy.deepcopy(original_trace)
        tampered_payload_trace[5].payload["tampered_key"] = "tampered_value"
        tamp_valid, tamp_broken, tamp_msg = verify_event_chain(tampered_payload_trace)
        assert tamp_valid is False
        assert tamp_broken == 5
        assert "Tampering detected at index 5" in tamp_msg

        # Case B: Tamper with previous_event_hash in controlled copy
        tampered_hash_trace = copy.deepcopy(original_trace)
        tampered_hash_trace[8].previous_event_hash = "deadbeef" * 8
        hash_valid, hash_broken, hash_msg = verify_event_chain(tampered_hash_trace)
        assert hash_valid is False
        assert hash_broken == 8
        assert "Chain broken at index 8" in hash_msg

        # 8. Invariant: Production DB is untouched and strictly valid
        prov_after = await ExperimentService.verify_provenance(db, exp.id)
        assert prov_after["is_valid"] is True
        assert prov_after["broken_index"] is None
        assert prov_after["total_events"] == prov["total_events"]
        assert prov_after["latest_hash"] == prov["latest_hash"]
