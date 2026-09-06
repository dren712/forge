"""
FORGE S7-B — Provenance Integrity Tests

Comprehensive verification that every event hash in the provenance chain
is derived from:
    previous_event_hash + canonical_event_representation (SHA-256)

Validates:
1. Valid chain -> PASS
2. Modified payload -> FAIL (tamper detection)
3. Modified previous hash -> FAIL (broken link detection, both genesis and interior)
4. Modified event hash -> FAIL (signature corruption detection)
5. Deleted event -> FAIL (gap detection, both genesis and interior)
6. Reordered event -> FAIL (sequence permutation detection)
7. End-to-end database service verification via ExperimentService.verify_provenance()
"""
import pytest
from sqlalchemy import select
from app.tracing.recorder import EventRecorder
from app.tracing.events import EventType, TraceEvent
from app.provenance.hasher import (
    verify_event_chain,
    compute_event_hash,
    canonicalize_payload,
    sign_event,
    GENESIS_HASH,
)
from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import ExperimentModel, TraceEventModel
from app.services.experiment_service import ExperimentService


async def _create_sample_chain(length: int = 5) -> list[TraceEvent]:
    """Helper to generate a valid, cryptographically signed chain of events."""
    recorder = EventRecorder(experiment_id="exp_provenance_test")
    event_types = [
        (EventType.EXPERIMENT_CREATED, {"name": "Test Experiment", "benchmark": "swe_v2"}),
        (EventType.GENERATION_CREATED, {"generation": 0, "model": "glm-4-7-flash"}),
        (EventType.AGENT_STARTED, {"agent": "g0", "task_id": "task_01"}),
        (EventType.TOOL_CALL, {"tool": "repository", "action": "list_files"}),
        (EventType.TOOL_RESULT, {"tool": "repository", "success": True, "files_count": 12}),
        (EventType.VERIFICATION_STARTED, {"checks": ["pytest"]}),
        (EventType.VERIFICATION_RESULT, {"passed": True, "failed_tests": 0}),
        (EventType.AGENT_COMPLETED, {"status": "COMPLETED", "turns": 4}),
    ]
    for etype, payload in event_types[:length]:
        await recorder.emit(etype, payload)
    return recorder.get_events()


# ── 1. Valid Chain ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_provenance_valid_chain():
    """Valid unbroken chain must pass verification."""
    events = await _create_sample_chain(length=5)
    assert len(events) == 5

    # Genesis check
    assert events[0].previous_event_hash == GENESIS_HASH

    # Consecutive links
    for i in range(1, len(events)):
        assert events[i].previous_event_hash == events[i - 1].event_hash

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is True
    assert broken_idx is None
    assert "valid and unbroken" in msg


# ── 2. Modified Payload ─────────────────────────────────────
@pytest.mark.asyncio
async def test_provenance_modified_payload():
    """Tampering with payload data at any position must be detected immediately."""
    events = await _create_sample_chain(length=5)

    # Tamper with event at index 2
    events[2].payload["agent"] = "adversarial_injected_agent"

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is False
    assert broken_idx == 2
    assert "Tampering detected at index 2" in msg


# ── 3. Modified Previous Hash ───────────────────────────────
@pytest.mark.asyncio
async def test_provenance_modified_previous_hash():
    """Tampering with previous_event_hash must fail verification."""
    # 3a: Modified previous hash on interior event
    events = await _create_sample_chain(length=5)
    events[2].previous_event_hash = "deadbeef" * 8

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is False
    assert broken_idx == 2
    assert "Chain broken at index 2" in msg

    # 3b: Modified previous hash on genesis event
    events_genesis = await _create_sample_chain(length=5)
    events_genesis[0].previous_event_hash = "badgenesis" * 6 + "0" * 4

    is_valid_g, broken_idx_g, msg_g = verify_event_chain(events_genesis)
    assert is_valid_g is False
    assert broken_idx_g == 0
    assert "Genesis event previous hash mismatch" in msg_g


# ── 4. Modified Event Hash ──────────────────────────────────
@pytest.mark.asyncio
async def test_provenance_modified_event_hash():
    """Corrupting stored event_hash must be caught as tampering."""
    events = await _create_sample_chain(length=5)

    # Tamper with the event hash of index 3
    events[3].event_hash = "0123456789abcdef" * 4

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is False
    assert broken_idx == 3
    assert "Tampering detected at index 3" in msg


# ── 5. Deleted Event ────────────────────────────────────────
@pytest.mark.asyncio
async def test_provenance_deleted_event():
    """Deleting an event from anywhere in the chain must break the hash link."""
    # 5a: Delete interior event (e.g. index 2)
    events = await _create_sample_chain(length=5)
    # Events: [E0, E1, E2, E3, E4] -> delete E2 -> [E0, E1, E3, E4]
    deleted_event = events.pop(2)
    assert len(events) == 4

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is False
    # E3 is now at index 2, but its previous_event_hash points to deleted E2, not E1
    assert broken_idx == 2
    assert "Chain broken at index 2" in msg

    # 5b: Delete genesis event
    events_g = await _create_sample_chain(length=5)
    events_g.pop(0)  # E1 is now index 0, but its previous_event_hash is not GENESIS_HASH
    is_valid_g, broken_idx_g, msg_g = verify_event_chain(events_g)
    assert is_valid_g is False
    assert broken_idx_g == 0
    assert "Genesis event previous hash mismatch" in msg_g


# ── 6. Reordered Event ──────────────────────────────────────
@pytest.mark.asyncio
async def test_provenance_reordered_event():
    """Permuting event sequence must break cryptographic order."""
    events = await _create_sample_chain(length=5)
    # Swap index 1 and index 2: [E0, E2, E1, E3, E4]
    events[1], events[2] = events[2], events[1]

    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is False
    assert broken_idx == 1
    assert "Chain broken at index 1" in msg


# ── 7. Database & Service Level Integration ─────────────────
import uuid
@pytest.mark.asyncio
async def test_provenance_database_service_verification():
    """Proves ExperimentService.verify_provenance operates against real SQLite records."""
    await init_db()
    async with AsyncSessionLocal() as db:
        exp = ExperimentModel(
            id=f"exp_provenance_db_{uuid.uuid4().hex[:8]}",
            name="DB Provenance Verification",
            goal="Test real database event chain verification",
            status="CREATED",
        )
        db.add(exp)
        await db.commit()

        # Emit events through EventRecorder and persist into DB
        recorder = EventRecorder(exp.id)
        e1 = await recorder.emit(EventType.EXPERIMENT_CREATED, {"goal": "test"})
        e2 = await recorder.emit(EventType.GENERATION_CREATED, {"gen": 0})
        e3 = await recorder.emit(EventType.AGENT_COMPLETED, {"result": "success"})

        for ev in [e1, e2, e3]:
            db.add(TraceEventModel(
                id=ev.event_id,
                experiment_id=exp.id,
                timestamp=ev.timestamp,
                type=ev.type.value,
                payload=ev.payload,
                previous_event_hash=ev.previous_event_hash,
                event_hash=ev.event_hash,
            ))
        await db.commit()

        # Valid chain verification
        result = await ExperimentService.verify_provenance(db, exp.id)
        assert result["is_valid"] is True
        assert result["total_events"] == 3
        assert result["broken_index"] is None

        # Tamper with row in DB
        db_events = (await db.execute(
            select(TraceEventModel)
            .where(TraceEventModel.experiment_id == exp.id)
            .order_by(TraceEventModel.timestamp)
        )).scalars().all()
        db_events[1].payload = {"gen": 999, "tampered": True}
        await db.commit()

        # Verification must detect DB-level tampering
        tampered_result = await ExperimentService.verify_provenance(db, exp.id)
        assert tampered_result["is_valid"] is False
        assert tampered_result["broken_index"] == 1
        assert "Tampering detected" in tampered_result["message"]
