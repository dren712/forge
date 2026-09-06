import copy
import pytest
from app.schemas.agent_spec import AgentSpec
from app.evolution.mutation import (
    Mutation,
    MutationType,
    MutationValidationError,
    apply_mutation,
)


def test_apply_valid_prompt_mutation():
    """
    Validates applying a valid prompt mutation:
    - Candidate receives updated system_prompt
    - Original AgentSpec remains completely unchanged
    """
    initial_prompt = "You are a basic coding assistant."
    new_prompt = "You are an autonomous engineer with strict verification rules."

    spec = AgentSpec(system_prompt=initial_prompt)
    original_copy = copy.deepcopy(spec)

    mutation = Mutation(
        mutation_type=MutationType.PROMPT_UPDATE,
        target="system_prompt",
        before={"system_prompt": initial_prompt},
        after={"system_prompt": new_prompt},
        reason="Strengthen engineering instructions",
        observed_failure="REASONING_FAILURE",
        expected_effect="Improve boundary compliance",
    )

    candidate = apply_mutation(spec, mutation)

    # Candidate updated
    assert candidate.system_prompt == new_prompt
    assert candidate is not spec

    # Original unchanged
    assert spec.system_prompt == initial_prompt
    assert spec.model_dump() == original_copy.model_dump()


def test_apply_valid_verifier_mutation():
    """
    Validates applying a valid verifier mutation:
    - Candidate receives updated verifier config
    - Original AgentSpec verifier remains 'none'
    """
    spec = AgentSpec(verifier={"type": "none"})
    original_copy = copy.deepcopy(spec)

    mutation = Mutation(
        mutation_type=MutationType.VERIFIER_UPDATE,
        target="verification_strategy",
        before={"type": "none", "require_zero_failed_tests": True, "enforce_before_complete": True, "min_test_count": 1},
        after={"type": "mandatory_tests", "require_zero_failed_tests": True, "enforce_before_complete": True, "min_test_count": 1},
        reason="Observed unverified task completion",
        observed_failure="VERIFICATION_FAILURE",
        expected_effect="Enforce automated test checks",
    )

    candidate = apply_mutation(spec, mutation)

    assert candidate.verifier.type == "mandatory_tests"
    assert candidate.verifier.require_zero_failed_tests is True
    assert spec.verifier.type == "none"
    assert spec.model_dump() == original_copy.model_dump()


def test_apply_valid_planner_mutation():
    """
    Validates applying a valid planner mutation:
    - Candidate receives updated planner config
    - Original AgentSpec planner remains unchanged
    """
    spec = AgentSpec(planner={"type": "none"})
    original_copy = copy.deepcopy(spec)

    mutation = Mutation(
        mutation_type=MutationType.PLANNER_UPDATE,
        target="planner",
        before={"type": "none", "max_subgoals": 5, "require_replan_on_error": False},
        after={"type": "structured_plan", "max_subgoals": 8, "require_replan_on_error": True},
        reason="Agent failed to plan multi-step operations",
        observed_failure="PLANNING_FAILURE",
        expected_effect="Provide structured subgoal decomposition",
    )

    candidate = apply_mutation(spec, mutation)

    assert candidate.planner.type == "structured_plan"
    assert candidate.planner.max_subgoals == 8
    assert candidate.planner.require_replan_on_error is True
    assert spec.planner.type == "none"
    assert spec.model_dump() == original_copy.model_dump()


def test_apply_unsupported_target_rejected():
    """
    Validates that attempting to apply a mutation with an unsupported target raises MutationValidationError.
    """
    spec = AgentSpec()
    original_copy = copy.deepcopy(spec)

    mutation = Mutation(
        mutation_type=MutationType.PROMPT_UPDATE,
        target="unknown_arbitrary_target",
        before={"val": 1},
        after={"val": 2},
        reason="Test",
        observed_failure="REASONING_FAILURE",
        expected_effect="Test",
    )

    with pytest.raises(MutationValidationError, match="Unsupported mutation target"):
        apply_mutation(spec, mutation)

    # Original spec remains untouched
    assert spec.model_dump() == original_copy.model_dump()


def test_apply_invalid_candidate_rejected():
    """
    Validates that if a mutation produces an invalid candidate AgentSpec, it is rejected.
    """
    spec = AgentSpec()
    original_copy = copy.deepcopy(spec)

    # 1. Invalid planner enum value
    invalid_planner_mutation = Mutation(
        mutation_type=MutationType.PLANNER_UPDATE,
        target="planner",
        before=spec.planner.model_dump(),
        after={"type": "invalid_magic_planner"},
        reason="Test",
        observed_failure="PLANNING_FAILURE",
        expected_effect="Test",
    )

    with pytest.raises(MutationValidationError, match="Invalid candidate AgentSpec generated"):
        apply_mutation(spec, invalid_planner_mutation)

    # 2. Empty string for system_prompt
    invalid_prompt_mutation = Mutation(
        mutation_type=MutationType.PROMPT_UPDATE,
        target="system_prompt",
        before={"system_prompt": spec.system_prompt},
        after={"system_prompt": "   "},
        reason="Test",
        observed_failure="REASONING_FAILURE",
        expected_effect="Test",
    )

    with pytest.raises(MutationValidationError, match="Candidate system_prompt must be a non-empty string"):
        apply_mutation(spec, invalid_prompt_mutation)

    # Original spec preserved
    assert spec.model_dump() == original_copy.model_dump()


def test_apply_mismatched_before_state_rejected():
    """
    Validates that if mutation 'before' state does not match the spec's current state,
    it is rejected to ensure accurate before/after representation.
    """
    spec = AgentSpec(verifier={"type": "none"})

    mutation = Mutation(
        mutation_type=MutationType.VERIFIER_UPDATE,
        target="verification_strategy",
        before={"type": "mandatory_tests", "require_zero_failed_tests": True, "enforce_before_complete": True, "min_test_count": 1},  # Does not match spec's 'none'!
        after={"type": "strict_test_gate", "require_zero_failed_tests": True, "enforce_before_complete": True, "min_test_count": 2},
        reason="Test",
        observed_failure="VERIFICATION_FAILURE",
        expected_effect="Test",
    )

    with pytest.raises(MutationValidationError, match="Mutation 'before' verifier state does not match"):
        apply_mutation(spec, mutation)


def test_mutation_apply_method_shortcut():
    """
    Validates that mutation.apply(spec) produces identical results to apply_mutation(spec, mutation).
    """
    spec = AgentSpec(system_prompt="Initial prompt.")
    mutation = Mutation(
        mutation_type=MutationType.PROMPT_UPDATE,
        target="system_prompt",
        before={"system_prompt": "Initial prompt."},
        after={"system_prompt": "Updated prompt via shortcut."},
        reason="Shortcut test",
        observed_failure="REASONING_FAILURE",
        expected_effect="Test",
    )

    candidate = mutation.apply(spec)
    assert candidate.system_prompt == "Updated prompt via shortcut."
    assert spec.system_prompt == "Initial prompt."
