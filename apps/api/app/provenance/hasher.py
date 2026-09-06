import hashlib
import json
from typing import Any, Tuple
from app.tracing.events import TraceEvent

GENESIS_HASH = "0" * 64


def canonicalize_payload(payload: dict[str, Any]) -> str:
    """Produces deterministic, canonical JSON representation of a payload."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_event_hash(previous_hash: str, event_type: str, timestamp: str, canonical_payload: str) -> str:
    """
    Computes cryptographic SHA256 over:
    previous_hash + event_type + timestamp + canonical_payload
    """
    hasher = hashlib.sha256()
    hasher.update(previous_hash.encode("utf-8"))
    hasher.update(event_type.encode("utf-8"))
    hasher.update(timestamp.encode("utf-8"))
    hasher.update(canonical_payload.encode("utf-8"))
    return hasher.hexdigest()


def sign_event(event: TraceEvent, previous_hash: str | None = None) -> TraceEvent:
    """Signs an event with a cryptographic hash linked to its predecessor."""
    prev = previous_hash if previous_hash is not None else event.previous_event_hash
    event.previous_event_hash = prev
    canonical = canonicalize_payload(event.payload)
    type_str = event.type.value if hasattr(event.type, "value") else str(event.type)
    event.event_hash = compute_event_hash(prev, type_str, event.timestamp, canonical)
    return event


def verify_event_chain(events: list[TraceEvent]) -> Tuple[bool, int | None, str]:
    """
    Verifies that the entire sequence of events forms an unbroken cryptographic chain.
    Returns (is_valid, broken_index, description).
    """
    if not events:
        return True, None, "Empty chain is valid."

    expected_prev = GENESIS_HASH

    for idx, event in enumerate(events):
        if idx == 0:
            if event.previous_event_hash != GENESIS_HASH:
                return (
                    False,
                    0,
                    f"Genesis event previous hash mismatch. Expected {GENESIS_HASH}, got {event.previous_event_hash}",
                )
        else:
            if event.previous_event_hash != expected_prev:
                return (
                    False,
                    idx,
                    f"Chain broken at index {idx}: previous_hash ({event.previous_event_hash}) does not match predecessor hash ({expected_prev}).",
                )

        canonical = canonicalize_payload(event.payload)
        type_str = event.type.value if hasattr(event.type, "value") else str(event.type)
        recalculated_hash = compute_event_hash(
            event.previous_event_hash,
            type_str,
            event.timestamp,
            canonical,
        )

        if recalculated_hash != event.event_hash:
            return (
                False,
                idx,
                f"Tampering detected at index {idx}: calculated hash {recalculated_hash} != stored hash {event.event_hash}.",
            )

        expected_prev = event.event_hash

    return True, None, "Cryptographic provenance chain valid and unbroken."
