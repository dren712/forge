import pytest
from pathlib import Path
import tempfile
import shutil
from pydantic import ValidationError

from app.providers.base import LLMProvider, LLMResponse, ToolCallItem
from app.providers.mock import DeterministicMockProvider
from app.tools.base import Tool, ToolResult, sanitize_path
from app.tools.registry import default_registry
from app.benchmarks.base import Benchmark, BenchmarkTask, TaskEvaluation
from app.benchmarks.registry import benchmark_registry
from app.schemas.agent_spec import AgentSpec, PlannerConfig, VerifierConfig
from app.evolution.acceptance import AcceptanceEngine, AcceptanceDecision
from app.evaluation.metrics import GenerationMetrics
from app.evolution.mutation import Mutation, MutationType
from app.provenance.hasher import (
    GENESIS_HASH,
    sign_event,
    verify_event_chain,
    compute_event_hash,
    canonicalize_payload,
)
from app.tracing.events import TraceEvent, EventType


def test_llm_provider_contract():
    provider = DeterministicMockProvider(mode="baseline")
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_llm_provider_generate_contract():
    provider = DeterministicMockProvider(mode="baseline")
    res = await provider.generate(
        messages=[{"role": "user", "content": "hello"}],
        tools=None,
        temperature=0.2,
    )
    assert isinstance(res, LLMResponse)
    assert hasattr(res, "content")
    assert hasattr(res, "tool_calls")
    assert hasattr(res, "input_tokens")
    assert hasattr(res, "output_tokens")
    assert hasattr(res, "latency_ms")
    assert isinstance(res.latency_ms, float)


def test_all_registered_tools_satisfy_contract():
    tools = default_registry.list_tools()
    assert len(tools) >= 5

    for tool_meta in tools:
        tool = default_registry.get(tool_meta["name"])
        assert tool is not None
        assert isinstance(tool, Tool)
        assert isinstance(tool.name, str) and len(tool.name) > 0
        assert isinstance(tool.description, str) and len(tool.description) > 0
        assert isinstance(tool.input_schema, dict)
        assert "type" in tool.input_schema


@pytest.mark.asyncio
async def test_benchmark_and_evaluator_contract():
    bench = benchmark_registry.get("software_engineering")
    assert bench is not None
    assert isinstance(bench, Benchmark)
    assert isinstance(bench.name, str)
    assert isinstance(bench.version, str)

    tasks = bench.list_tasks()
    assert len(tasks) > 0
    task = tasks[0]
    assert isinstance(task, BenchmarkTask)
    assert task.id and task.title and task.description


def test_agentspec_validation_rejects_invalid():
    # Valid spec
    spec = AgentSpec(model="glm-4-7-flash")
    assert spec.model == "glm-4-7-flash"

    # Invalid planner type
    with pytest.raises(ValidationError):
        AgentSpec(planner=PlannerConfig(type="unsupported_planner_xyz"))

    # Invalid verifier type
    with pytest.raises(ValidationError):
        AgentSpec(verifier=VerifierConfig(type="invalid_verifier_abc"))


def test_acceptance_engine_deterministic_contracts():
    engine = AcceptanceEngine()

    parent = GenerationMetrics(
        generation_number=0,
        total_tasks=10,
        successful_tasks=5,
        accuracy=0.50,
        reliability=0.50,
        total_cost_usd=0.010,
        avg_cost_per_task=0.001,
        avg_latency_ms=2000.0,
        composite_score=0.50,
        total_tokens=1000,
        total_model_calls=10,
        total_tool_calls=20,
        verification_pass_rate=0.50,
    )

    # Regressed accuracy must be rejected
    candidate_worse = parent.model_copy(update={"accuracy": 0.40, "composite_score": 0.40})
    decision_worse = engine.evaluate_candidate(parent, candidate_worse)
    assert isinstance(decision_worse, AcceptanceDecision)
    assert decision_worse.accepted is False
    assert decision_worse.status == "REJECTED"

    # Improved accuracy must be accepted
    candidate_better = parent.model_copy(update={"accuracy": 0.80, "reliability": 0.85, "composite_score": 0.82})
    decision_better = engine.evaluate_candidate(parent, candidate_better)
    assert decision_better.accepted is True
    assert decision_better.status == "ACCEPTED"


def test_provenance_tamper_detection_contract():
    ev0 = sign_event(
        TraceEvent(
            experiment_id="exp_test",
            type=EventType.EXPERIMENT_CREATED,
            payload={"name": "Audit Test"},
        ),
        previous_hash=GENESIS_HASH,
    )

    ev1 = sign_event(
        TraceEvent(
            experiment_id="exp_test",
            type=EventType.AGENT_STARTED,
            payload={"goal": "Verify Provenance"},
        ),
        previous_hash=ev0.event_hash,
    )

    is_valid, broken_idx, msg = verify_event_chain([ev0, ev1])
    assert is_valid is True
    assert broken_idx is None

    # Alter payload of ev1 -> tamper detection
    tampered_ev1 = ev1.model_copy(update={"payload": {"goal": "Tampered Goal"}})
    is_valid_tampered, broken_idx, msg = verify_event_chain([ev0, tampered_ev1])
    assert is_valid_tampered is False
    assert broken_idx == 1
    assert "Tampering detected" in msg
