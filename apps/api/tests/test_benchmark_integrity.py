import pytest
import json
from pathlib import Path
from app.benchmarks.registry import benchmark_registry
from app.benchmarks.third_party_benchmark import ThirdPartyAppBenchmark
from app.benchmarks.base import BenchmarkTask, TaskEvaluation, TaskCheck
from app.agents.state import AgentState
from app.agents.ao_integration import ao_bridge


@pytest.fixture
def benchmark():
    return ThirdPartyAppBenchmark()


def test_benchmark_metadata_and_versioning(benchmark: ThirdPartyAppBenchmark):
    """Verifies canonical benchmark versioning metadata contracts."""
    assert benchmark.benchmark_id == "third_party_automation"
    assert benchmark.name == "third_party_automation"
    assert benchmark.version == "2.0.0"
    assert benchmark.evaluator_version == "2.0.0"
    assert benchmark.created_at == "2026-03-01T00:00:00Z"

    tasks = benchmark.list_tasks()
    assert len(tasks) == 10

    # Test registry integration
    reg_bench = benchmark_registry.get("third_party_automation")
    assert reg_bench is not None
    assert reg_bench.version == "2.0.0"

    bench_meta = benchmark_registry.list_benchmarks()
    tpa_meta = next(b for b in bench_meta if b["name"] == "third_party_automation")
    assert tpa_meta["tasks_count"] == 10
    assert len(tpa_meta["task_ids"]) == 10


def test_task_schema_and_matrix(benchmark: ThirdPartyAppBenchmark):
    """Verifies that all 10 tasks define primary skills, tools, constraints, and hidden constraints."""
    tasks = benchmark.list_tasks()
    for task in tasks:
        assert task.id.startswith("task_")
        assert len(task.title) > 0
        assert len(task.allowed_tools) > 0
        assert len(task.constraints) > 0
        assert len(task.hidden_constraints) > 0
        assert len(task.primary_skill) > 0
        assert len(task.main_failure_mode) > 0
        assert len(task.expected_behavior) > 0


@pytest.mark.asyncio
async def test_task_reset_restores_state(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """Proves: task reset -> baseline state -> mutated state -> reset -> baseline restored."""
    task = benchmark.list_tasks()[0]

    # 1. Initial setup
    await benchmark.setup_task(task, tmp_path)
    linear_state = json.loads((tmp_path / ".linear_state.json").read_text())
    assert len(linear_state["issues"]) == 0
    assert linear_state["counter"] == 101

    # 2. Mutate state
    linear_state["issues"].append({
        "id": "MUTATED-999",
        "team_id": "dummy",
        "title": "Mutated state that should not persist",
        "priority": 1,
    })
    (tmp_path / ".linear_state.json").write_text(json.dumps(linear_state))
    assert len(json.loads((tmp_path / ".linear_state.json").read_text())["issues"]) == 1

    # 3. Call reset
    await benchmark.reset_task(task, tmp_path)

    # 4. Verify baseline restored
    restored_state = json.loads((tmp_path / ".linear_state.json").read_text())
    assert len(restored_state["issues"]) == 0
    assert restored_state["counter"] == 101


@pytest.mark.asyncio
async def test_task_isolation(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """Proves tasks executed in separate workspaces do not cross-contaminate."""
    ws_task1 = tmp_path / "ws_task1"
    ws_task2 = tmp_path / "ws_task2"

    t1 = benchmark.list_tasks()[0]
    t2 = benchmark.list_tasks()[1]

    await benchmark.setup_task(t1, ws_task1)
    await benchmark.setup_task(t2, ws_task2)

    # Mutate ws1
    (ws_task1 / ".linear_state.json").write_text(json.dumps({
        "issues": [{"id": "CORE-101", "priority": 1, "team_id": "550e8400-e29b-41d4-a716-446655440001"}]
    }))

    # Verify ws2 remains completely untouched
    ws2_linear = json.loads((ws_task2 / ".linear_state.json").read_text())
    assert len(ws2_linear["issues"]) == 0


@pytest.mark.asyncio
async def test_evaluator_self_test_correct_state(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """Proves evaluator accurately passes when real workspace state fulfills task criteria."""
    task = benchmark.list_tasks()[0]  # task_01_api_discovery
    await benchmark.setup_task(task, tmp_path)

    # Inject valid state
    (tmp_path / ".linear_state.json").write_text(json.dumps({
        "issues": [
            {
                "id": "CORE-102",
                "team_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Database Pool Exhaustion",
                "priority": 1,
            }
        ]
    }))

    state = AgentState(goal=task.goal, workspace_path=tmp_path)
    state.transition_to("RUNNING")
    state.transition_to("COMPLETED")

    evaluation = await benchmark.evaluate_task(state, task, tmp_path)
    assert evaluation.passed is True
    assert evaluation.score == 1.0
    assert len(evaluation.checks) == 3
    assert all(c.passed for c in evaluation.checks)


@pytest.mark.asyncio
async def test_evaluator_self_test_incorrect_state(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """Proves evaluator accurately fails when state violates constraints."""
    task = benchmark.list_tasks()[0]  # task_01_api_discovery
    await benchmark.setup_task(task, tmp_path)

    # Inject invalid team_id (slug instead of UUID)
    (tmp_path / ".linear_state.json").write_text(json.dumps({
        "issues": [
            {
                "id": "CORE-102",
                "team_id": "CORE",
                "title": "Database Pool Exhaustion",
                "priority": 1,
            }
        ]
    }))

    state = AgentState(goal=task.goal, workspace_path=tmp_path)
    state.transition_to("RUNNING")
    state.transition_to("COMPLETED")

    evaluation = await benchmark.evaluate_task(state, task, tmp_path)
    assert evaluation.passed is False
    assert evaluation.score == 0.5  # Partial credit for creating issue, but failed UUID check
    chk_uuid = next(c for c in evaluation.checks if c.name == "correct_team_uuid")
    assert chk_uuid.passed is False


@pytest.mark.asyncio
async def test_evaluator_false_positive_rejection(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """
    CRITICAL: Rejects agent verbal claims of success when required state is missing.
    Ensures FORGE measures physical reality rather than model hallucinations.
    """
    task = benchmark.list_tasks()[0]
    await benchmark.setup_task(task, tmp_path)

    # Empty state file (no issues created)
    (tmp_path / ".linear_state.json").write_text(json.dumps({"issues": []}))

    # Agent claims complete success in state
    state = AgentState(goal=task.goal, workspace_path=tmp_path)
    state.transition_to("RUNNING")
    state.transition_to("COMPLETED")
    state.messages.append({
        "role": "assistant",
        "content": "I have successfully resolved the issue! Database pool tracking issue is created with urgent priority under Core Platform.",
    })

    evaluation = await benchmark.evaluate_task(state, task, tmp_path)
    assert evaluation.passed is False
    assert evaluation.score == 0.0
    assert any(not c.passed for c in evaluation.checks)


@pytest.mark.asyncio
async def test_evaluator_false_negative_acceptance(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """
    Proves evaluator grants PASS when objective state is valid,
    even if the agent provided minimal natural language commentary.
    """
    task = benchmark.list_tasks()[4]  # task_05_sentry_p99_latency_investigation
    await benchmark.setup_task(task, tmp_path)

    # Valid Sentry state
    (tmp_path / ".sentry_state.json").write_text(json.dumps({
        "incidents": [
            {
                "id": "SENTRY-891",
                "service": "billing-api",
                "status": "resolved",
                "resolution_note": "Identified database connection leak and expanded pool capacity to 100.",
            }
        ]
    }))

    # Minimal state
    state = AgentState(goal=task.goal, workspace_path=tmp_path)
    state.transition_to("RUNNING")
    state.transition_to("COMPLETED")
    state.messages.append({"role": "assistant", "content": "Done."})

    evaluation = await benchmark.evaluate_task(state, task, tmp_path)
    assert evaluation.passed is True
    assert evaluation.score == 1.0


@pytest.mark.asyncio
async def test_evaluator_negative_constraint_enforcement(benchmark: ThirdPartyAppBenchmark, tmp_path: Path):
    """Proves evaluator penalizes negative constraint violations (Task 7 Growth tier)."""
    task = benchmark.list_tasks()[6]  # task_07_growth_tier_routing
    await benchmark.setup_task(task, tmp_path)

    # Improper escalation to #enterprise-escalations
    (tmp_path / ".slack_messages.json").write_text(json.dumps([
        {"channel": "#eng-backlog", "text": "UI bug"},
        {"channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_growth_start UI bug"},
    ]))

    state = AgentState(goal=task.goal, workspace_path=tmp_path)
    state.transition_to("RUNNING")
    state.transition_to("COMPLETED")

    evaluation = await benchmark.evaluate_task(state, task, tmp_path)
    assert evaluation.passed is False
    chk_no_esc = next(c for c in evaluation.checks if c.name == "no_improper_enterprise_escalation")
    assert chk_no_esc.passed is False


@pytest.mark.asyncio
async def test_ao_bridge_diagnostics():
    """
    Verifies AO diagnostic contracts:
    - Distinguishes binary installation from harness authentication
    - Accurately reports invocation_status as UNVERIFIED if unauthenticated
    """
    diag = await ao_bridge.get_diagnostics()
    assert isinstance(diag, dict)
    assert "ao_installed" in diag
    assert "daemon_reachable" in diag
    assert "authenticated" in diag
    assert "invocation_status" in diag
    assert "invocation_notes" in diag
    assert diag["invocation_status"] in ("UNVERIFIED", "VERIFIED", "FAILED")
    assert isinstance(diag["registered_projects"], list)
