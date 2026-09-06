import pytest
from app.schemas.agent_spec import AgentSpec
from app.evolution.mutation import (
    Mutation,
    MutationType,
    MutationValidationError,
    validate_mutation,
    SUPPORTED_MUTATION_TARGETS,
)
from app.evolution.mutation_generator import MutationGenerator
from app.evaluation.failure_analyzer import FailureAnalysis, FailureType
from app.evaluation.failure_clustering import FailureClusterReport, FailureCluster


def test_supported_mutation_targets_set():
    """Confirms all 7 targets required by S6-D are supported."""
    expected_targets = {
        "system_prompt",
        "planner",
        "tool_selection_policy",
        "memory_strategy",
        "verification_strategy",
        "retry_strategy",
        "orchestration_strategy",
    }
    assert SUPPORTED_MUTATION_TARGETS == expected_targets


def test_valid_mutation_generation_verification_strategy():
    """Tests generating a verified mutation for verification_strategy from VERIFICATION_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(verifier={"type": "none"})

    report = FailureClusterReport(
        total_failures=4,
        total_tasks_evaluated=4,
        clusters=[
            FailureCluster(
                category="VERIFICATION_FAILURE",
                count=4,
                affected_tasks=["t1", "t2", "t3", "t4"],
                percentage=100.0,
                representative_evidence=["No test assertions executed", "Premature task exit"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    # Validate mutation properties
    assert mutation.target == "verification_strategy"
    assert mutation.mutation_type == MutationType.VERIFIER_UPDATE
    assert mutation.before["type"] == "none"
    assert mutation.after["type"] == "mandatory_tests"
    assert mutation.after["require_zero_failed_tests"] is True
    assert mutation.observed_failure == "VERIFICATION_FAILURE"
    assert "No test assertions executed" in mutation.reason or "Premature task exit" in mutation.reason
    assert "Enforce automated test execution" in mutation.expected_effect
    assert candidate.verifier.type == "mandatory_tests"


def test_valid_mutation_generation_planner():
    """Tests generating a validated mutation for planner from PLANNING_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(planner={"type": "none"})

    report = FailureClusterReport(
        total_failures=3,
        total_tasks_evaluated=3,
        clusters=[
            FailureCluster(
                category="PLANNING_FAILURE",
                count=3,
                affected_tasks=["t5", "t6", "t7"],
                percentage=100.0,
                representative_evidence=["Infinite loop in file search", "No subgoal progression"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "planner"
    assert mutation.mutation_type == MutationType.PLANNER_UPDATE
    assert mutation.before["type"] == "none"
    assert mutation.after["type"] == "structured_plan"
    assert mutation.after["require_replan_on_error"] is True
    assert mutation.observed_failure == "PLANNING_FAILURE"
    assert candidate.planner.type == "structured_plan"


def test_valid_mutation_generation_retry_strategy():
    """Tests generating a validated mutation for retry_strategy from RECOVERY_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(retry_policy={"max_attempts": 2, "retry_on_tool_failure": False, "backoff_seconds": 1.0})

    report = FailureClusterReport(
        total_failures=2,
        total_tasks_evaluated=2,
        clusters=[
            FailureCluster(
                category="RECOVERY_FAILURE",
                count=2,
                affected_tasks=["t1", "t2"],
                percentage=100.0,
                representative_evidence=["Tool error unrecovered: ConnectionReset"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "retry_strategy"
    assert mutation.mutation_type == MutationType.RETRY_POLICY_UPDATE
    assert mutation.after["max_attempts"] >= 4
    assert mutation.after["retry_on_tool_failure"] is True
    assert mutation.observed_failure == "RECOVERY_FAILURE"
    assert candidate.retry_policy.retry_on_tool_failure is True


def test_valid_mutation_generation_tool_selection_policy():
    """Tests generating a validated mutation for tool_selection_policy from TOOL_SELECTION_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(tools=["shell"])

    report = FailureClusterReport(
        total_failures=1,
        total_tasks_evaluated=1,
        clusters=[
            FailureCluster(
                category="TOOL_SELECTION_FAILURE",
                count=1,
                affected_tasks=["t1"],
                percentage=100.0,
                representative_evidence=["Agent needed test_runner and file_editor tools"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "tool_selection_policy"
    assert mutation.mutation_type == MutationType.TOOL_POLICY_UPDATE
    assert "test_runner" in mutation.after["tools"]
    assert "file_editor" in mutation.after["tools"]
    assert candidate.tools == mutation.after["tools"]


def test_valid_mutation_generation_memory_strategy():
    """Tests generating a validated mutation for memory_strategy from MEMORY_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(memory={"type": "stateless"})

    report = FailureClusterReport(
        total_failures=1,
        total_tasks_evaluated=1,
        clusters=[
            FailureCluster(
                category="MEMORY_FAILURE",
                count=1,
                affected_tasks=["t1"],
                percentage=100.0,
                representative_evidence=["Agent lost track of previously discovered bug line"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "memory_strategy"
    assert mutation.mutation_type == MutationType.MEMORY_UPDATE
    assert mutation.before["type"] == "stateless"
    assert mutation.after["type"] == "working_context"
    assert candidate.memory.type == "working_context"


def test_valid_mutation_generation_orchestration_strategy():
    """Tests generating a validated mutation for orchestration_strategy from TASK_MISINTERPRETATION."""
    generator = MutationGenerator()
    spec = AgentSpec(orchestration={"type": "direct"})

    report = FailureClusterReport(
        total_failures=1,
        total_tasks_evaluated=1,
        clusters=[
            FailureCluster(
                category="TASK_MISINTERPRETATION",
                count=1,
                affected_tasks=["t1"],
                percentage=100.0,
                representative_evidence=["Agent modified README instead of source code"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "orchestration_strategy"
    assert mutation.mutation_type == MutationType.ORCHESTRATION_UPDATE
    assert mutation.before["type"] == "direct"
    assert mutation.after["type"] == "plan_execute_verify"
    assert candidate.orchestration.type == "plan_execute_verify"


def test_valid_mutation_generation_system_prompt():
    """Tests generating a validated mutation for system_prompt from REASONING_FAILURE."""
    generator = MutationGenerator()
    spec = AgentSpec(system_prompt="Base engineer instructions.")

    report = FailureClusterReport(
        total_failures=1,
        total_tasks_evaluated=1,
        clusters=[
            FailureCluster(
                category="REASONING_FAILURE",
                count=1,
                affected_tasks=["t1"],
                percentage=100.0,
                representative_evidence=["Agent made flawed assumption about API response format"],
                severity="HIGH",
            )
        ],
    )

    candidate, mutation = generator.generate_mutation(
        current_spec=spec,
        failure_report=report,
    )

    assert mutation.target == "system_prompt"
    assert mutation.mutation_type == MutationType.PROMPT_UPDATE
    assert "Base engineer instructions." in mutation.after["system_prompt"]
    assert "[RULE]:" in mutation.after["system_prompt"]
    assert candidate.system_prompt == mutation.after["system_prompt"]


# ---------------- INVALID MUTATION REJECTION TESTS ----------------

def test_reject_unsupported_target():
    """Validates rejection of mutations with unsupported targets."""
    mut = Mutation(
        mutation_type=MutationType.PROMPT_UPDATE,
        target="invalid_nonexistent_target",
        before={"val": 1},
        after={"val": 2},
        reason="Test",
        observed_failure="REASONING_FAILURE",
        expected_effect="Test",
    )
    with pytest.raises(MutationValidationError, match="Unsupported mutation target"):
        validate_mutation(mut)


def test_reject_no_op_mutation():
    """Validates rejection when before and after states are identical."""
    mut = Mutation(
        mutation_type=MutationType.PLANNER_UPDATE,
        target="planner",
        before={"type": "structured_plan"},
        after={"type": "structured_plan"},  # Identical!
        reason="Test",
        observed_failure="PLANNING_FAILURE",
        expected_effect="Test",
    )
    with pytest.raises(MutationValidationError, match="no-op mutation"):
        validate_mutation(mut)


def test_reject_missing_required_fields():
    """Validates rejection when required fields are empty or None."""
    mut = Mutation(
        mutation_type=MutationType.PLANNER_UPDATE,
        target="planner",
        before={"type": "none"},
        after={"type": "structured_plan"},
        reason="   ",  # Empty whitespace!
        observed_failure="PLANNING_FAILURE",
        expected_effect="Test",
    )
    with pytest.raises(MutationValidationError, match="Mutation field 'reason' must be non-empty"):
        validate_mutation(mut)


def test_reject_schema_invalid_after_state():
    """Validates rejection when 'after' state contains invalid schema values."""
    mut = Mutation(
        mutation_type=MutationType.PLANNER_UPDATE,
        target="planner",
        before={"type": "none"},
        after={"type": "completely_invalid_planner_type"},
        reason="Test",
        observed_failure="PLANNING_FAILURE",
        expected_effect="Test",
    )
    with pytest.raises(MutationValidationError, match="failed schema validation"):
        validate_mutation(mut)


def test_reject_ungrounded_observed_failure():
    """Validates rejection when observed_failure does not exist in failure report."""
    report = FailureClusterReport(
        total_failures=1,
        total_tasks_evaluated=1,
        clusters=[
            FailureCluster(
                category="VERIFICATION_FAILURE",
                count=1,
                affected_tasks=["t1"],
                percentage=100.0,
                representative_evidence=["Tests failed"],
            )
        ],
    )

    mut = Mutation(
        mutation_type=MutationType.MEMORY_UPDATE,
        target="memory_strategy",
        before={"type": "stateless"},
        after={"type": "working_context"},
        reason="Test",
        observed_failure="MEMORY_FAILURE",  # Not in the report!
        expected_effect="Test",
    )

    with pytest.raises(MutationValidationError, match="not grounded in failure cluster report"):
        validate_mutation(mut, failure_report=report)


def test_reject_generation_without_evidence():
    """Validates that generating a mutation with 0 failures and no evidence is rejected."""
    generator = MutationGenerator()
    spec = AgentSpec()
    with pytest.raises(MutationValidationError, match="no failure cluster report or execution evidence"):
        generator.generate_mutation(spec, failure_report=FailureClusterReport())
