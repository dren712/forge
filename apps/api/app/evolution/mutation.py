import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class MutationType(str, Enum):
    PROMPT_UPDATE = "PROMPT_UPDATE"
    PLANNER_UPDATE = "PLANNER_UPDATE"
    TOOL_POLICY_UPDATE = "TOOL_POLICY_UPDATE"
    MEMORY_UPDATE = "MEMORY_UPDATE"
    VERIFIER_UPDATE = "VERIFIER_UPDATE"
    RETRY_POLICY_UPDATE = "RETRY_POLICY_UPDATE"
    ORCHESTRATION_UPDATE = "ORCHESTRATION_UPDATE"


class Mutation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mutation_type: MutationType
    target: str
    before: Any
    after: Any
    reason: str
    observed_failure: str
    expected_effect: str
