import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.providers.base import LLMResponse, ToolCallItem, ToolCall
from app.providers.router import ModelRouter, ModelRole
from app.providers.mock import DeterministicMockProvider
from app.agents.architect import AgentArchitect
from app.evaluation.failure_analyzer import FailureAnalyzer, FailureType
from app.evolution.mutation_generator import MutationGenerator
from app.schemas.agent_spec import AgentSpec
from app.agents.state import AgentState
from app.benchmarks.base import BenchmarkTask, TaskEvaluation
from app.evaluation.metrics import ExecutionMetrics
from app.core.errors import (
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
    ProviderInvalidRequestError,
    ProviderResponseFormatError,
)


def test_llm_response_metadata_and_tool_call_alias():
    tc = ToolCall(id="tc_1", name="search", arguments={"query": "test"})
    assert isinstance(tc, ToolCallItem)
    assert tc.name == "search"

    res = LLMResponse(
        content="Success",
        tool_calls=[tc],
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        latency_ms=250.5,
        finish_reason="stop",
        provider="tensormux",
        model="glm-4-7-flash",
    )

    assert res.provider == "tensormux"
    assert res.model == "glm-4-7-flash"
    assert res.finish_reason == "stop"
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].id == "tc_1"


def test_provider_error_hierarchy():
    auth_err = ProviderAuthenticationError("Bad Key")
    assert isinstance(auth_err, ProviderError)

    req_err = ProviderInvalidRequestError("Bad schema")
    assert isinstance(req_err, ProviderError)

    resp_err = ProviderResponseFormatError("Bad JSON")
    assert isinstance(resp_err, ProviderError)

    timeout_err = ProviderTimeoutError("Timed out")
    assert isinstance(timeout_err, ProviderError)

    rate_err = ProviderRateLimitError("Rate limit")
    assert isinstance(rate_err, ProviderError)


def test_model_router_roles():
    router = ModelRouter()
    # In test mode, all roles return DeterministicMockProvider
    arch_prov = router.get_provider(ModelRole.ARCHITECT)
    exec_prov = router.get_provider(ModelRole.EXECUTOR)
    refl_prov = router.get_provider(ModelRole.REFLECTOR)
    mut_prov = router.get_provider(ModelRole.MUTATOR)

    assert isinstance(arch_prov, DeterministicMockProvider)
    assert isinstance(exec_prov, DeterministicMockProvider)
    assert isinstance(refl_prov, DeterministicMockProvider)
    assert isinstance(mut_prov, DeterministicMockProvider)


@pytest.mark.asyncio
async def test_provider_diagnostics_endpoint_has_no_secrets():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/providers/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "active_primary_provider" in data
        assert "providers" in data
        assert "tensormux" in data["providers"]
        assert "aigrants" in data["providers"]
        assert "smallest_voice" in data["providers"]

        # Assert no sensitive keys are leaked
        raw_json = resp.text.lower()
        assert "sk-" not in raw_json
        assert "tmx_" not in raw_json
        assert "secret" not in raw_json
        assert "password" not in raw_json


@pytest.mark.asyncio
async def test_agent_architect_structured_spec_generation():
    provider = DeterministicMockProvider(mode="baseline")
    architect = AgentArchitect(provider)

    spec = await architect.design_agent(
        goal="Test architect structured output",
        available_tools=["repository", "file_editor", "shell"],
        benchmark_description="Benchmark Suite",
        generation_number=0,
    )

    assert isinstance(spec, AgentSpec)
    assert spec.model == "glm-4-7-flash"
    assert spec.planner.type == "none"
    assert spec.verifier.type == "none"
    assert len(spec.tools) <= 3


@pytest.mark.asyncio
async def test_failure_analyzer_and_mutation_generator():
    provider = DeterministicMockProvider(mode="baseline")
    analyzer = FailureAnalyzer(provider)
    generator = MutationGenerator(provider)

    spec = AgentSpec(verifier={"type": "none"})
    state = AgentState(goal="Fix bug")
    state.status = "COMPLETED"
    state.verification_passed = False

    task = BenchmarkTask(
        id="task_1",
        title="Fix pagination",
        description="Fix bug",
        repository="repo",
        issue="issue",
        expected_behavior="tests pass",
    )
    eval_res = TaskEvaluation(
        task_id="task_1",
        passed=False,
        score=0.0,
        reason="Tests were not executed before declaring task complete.",
        verification_passed=False,
    )
    metrics = ExecutionMetrics(
        task_id="task_1",
        task_success=False,
        accuracy=0.0,
        reliability=0.0,
        cost_usd=0.001,
        latency_ms=100.0,
    )

    analysis = await analyzer.analyze(spec, state, task, eval_res, metrics)
    assert analysis.failure_type == FailureType.VERIFICATION_FAILURE
    assert analysis.severity == "HIGH"

    candidate_spec, mutation = generator.propose_mutation(spec, [analysis], generation_number=1)
    assert candidate_spec.verifier.type == "mandatory_tests"
    assert mutation.target in ("verifier", "verification_strategy")
