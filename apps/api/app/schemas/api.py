from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.agent_spec import AgentSpec


class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "GitHub Issue Resolver"})
    goal: str = Field(
        ...,
        json_schema_extra={"example": "Build an agent capable of resolving software engineering issues in repositories."},
    )
    benchmark_id: str = Field(default="software_engineering")
    tools: list[str] = Field(
        default_factory=lambda: ["repository", "file_editor", "shell", "test_runner", "search"]
    )
    max_generations: int = Field(default=5, ge=1, le=20)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    goal: str
    benchmark_id: str
    tool_ids: list[str]
    current_generation_id: str | None
    best_generation_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    generations_count: int = 0
    best_accuracy: float | None = None
    best_reliability: float | None = None


class GenerationResponse(BaseModel):
    id: str
    experiment_id: str
    parent_generation_id: str | None
    generation_number: int
    agent_spec: dict[str, Any]
    mutation_id: str | None
    metrics: dict[str, Any] | None
    benchmark_id: str
    benchmark_version: str | None = None
    status: str
    rejection_reason: str | None
    created_at: datetime


class ExecutionResponse(BaseModel):
    id: str
    experiment_id: str
    generation_id: str
    task_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    result: dict[str, Any] | None
    metrics: dict[str, Any] | None


class EventResponse(BaseModel):
    event_id: str
    experiment_id: str
    generation_id: str | None
    execution_id: str | None
    timestamp: str
    type: str
    payload: dict[str, Any]
    previous_event_hash: str
    event_hash: str


class ProvenanceVerificationResponse(BaseModel):
    experiment_id: str
    is_valid: bool
    total_events: int
    broken_index: int | None
    message: str
    genesis_hash: str
    latest_hash: str


class EvidenceResponse(BaseModel):
    generation: str | None
    parent_generation: str | None
    metrics: dict[str, Any]
    failures: list[dict[str, Any]]
    memory: list[dict[str, Any]]
    mutations: list[dict[str, Any]]
    decision: dict[str, Any]
    provenance: dict[str, Any]

