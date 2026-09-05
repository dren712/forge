import pytest
from app.tracing.recorder import EventRecorder
from app.tracing.events import EventType
from app.provenance.hasher import verify_event_chain


@pytest.mark.asyncio
async def test_provenance_chain_integrity_and_tamper_detection():
    recorder = EventRecorder(experiment_id="exp_tamper_test")

    e1 = await recorder.emit(EventType.EXPERIMENT_CREATED, {"name": "Test Exp"})
    e2 = await recorder.emit(EventType.GENERATION_CREATED, {"generation": 0})
    e3 = await recorder.emit(EventType.AGENT_STARTED, {"agent": "g0"})
    e4 = await recorder.emit(EventType.TOOL_CALL, {"tool": "repository"})

    events = recorder.get_events()
    assert len(events) == 4

    # Verification on pristine chain must be valid
    is_valid, broken_idx, msg = verify_event_chain(events)
    assert is_valid is True
    assert broken_idx is None

    # Alter event payload (Tampering)
    events[2].payload["agent"] = "hacked_agent"

    # Verification must detect tampering
    is_valid_tampered, broken_idx_tampered, msg_tampered = verify_event_chain(events)
    assert is_valid_tampered is False
    assert broken_idx_tampered == 2
    assert "Tampering detected" in msg_tampered
