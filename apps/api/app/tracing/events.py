from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, Field


class EventType(str, Enum):
    EXPERIMENT_CREATED = "EXPERIMENT_CREATED"
    GENERATION_CREATED = "GENERATION_CREATED"
    AGENT_STARTED = "AGENT_STARTED"
    MODEL_CALL = "MODEL_CALL"
    MODEL_RESPONSE = "MODEL_RESPONSE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    STATE_UPDATE = "STATE_UPDATE"
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_RESULT = "VERIFICATION_RESULT"
    EVALUATION_STARTED = "EVALUATION_STARTED"
    EVALUATION_COMPLETED = "EVALUATION_COMPLETED"
    FAILURE_DETECTED = "FAILURE_DETECTED"
    MUTATION_PROPOSED = "MUTATION_PROPOSED"
    MUTATION_APPLIED = "MUTATION_APPLIED"
    GENERATION_ACCEPTED = "GENERATION_ACCEPTED"
    GENERATION_REJECTED = "GENERATION_REJECTED"
    SELF_REFLECTION_STARTED = "SELF_REFLECTION_STARTED"
    SELF_REFLECTION_COMPLETED = "SELF_REFLECTION_COMPLETED"
    TOOL_PLAYBOOK_LEARNED = "TOOL_PLAYBOOK_LEARNED"


class TraceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    generation_id: str | None = None
    execution_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str = "0" * 64
    event_hash: str = ""
