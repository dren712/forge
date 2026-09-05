from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExperimentModel(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    benchmark_id: Mapped[str] = mapped_column(String(64), default="software_engineering")
    tool_ids: Mapped[list] = mapped_column(JSON, default=list)
    current_generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED")  # CREATED, RUNNING, COMPLETED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    generations: Mapped[list["GenerationModel"]] = relationship(
        "GenerationModel", back_populates="experiment", cascade="all, delete-orphan"
    )
    events: Mapped[list["TraceEventModel"]] = relationship(
        "TraceEventModel", back_populates="experiment", cascade="all, delete-orphan"
    )


class GenerationModel(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(64), ForeignKey("experiments.id"), nullable=False)
    parent_generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    mutation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    benchmark_id: Mapped[str] = mapped_column(String(64), default="software_engineering")
    status: Mapped[str] = mapped_column(String(32), default="CREATED")  # RUNNING, COMPLETED, ACCEPTED, REJECTED, FAILED
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    experiment: Mapped["ExperimentModel"] = relationship("ExperimentModel", back_populates="generations")
    executions: Mapped[list["ExecutionModel"]] = relationship(
        "ExecutionModel", back_populates="generation", cascade="all, delete-orphan"
    )


class ExecutionModel(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(64), ForeignKey("experiments.id"), nullable=False)
    generation_id: Mapped[str] = mapped_column(String(64), ForeignKey("generations.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    generation: Mapped["GenerationModel"] = relationship("GenerationModel", back_populates="executions")


class TraceEventModel(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(64), ForeignKey("experiments.id"), nullable=False)
    generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    experiment: Mapped["ExperimentModel"] = relationship("ExperimentModel", back_populates="events")


class MutationModel(Base):
    __tablename__ = "mutations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    observed_failure: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_effect: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
