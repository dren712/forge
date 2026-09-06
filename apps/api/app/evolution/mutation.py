import copy
import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.agent_spec import (
    AgentSpec,
    PlannerConfig,
    MemoryConfig,
    VerifierConfig,
    RetryPolicy,
    OrchestrationConfig,
)


class MutationType(str, Enum):
    PROMPT_UPDATE = "PROMPT_UPDATE"
    PLANNER_UPDATE = "PLANNER_UPDATE"
    TOOL_POLICY_UPDATE = "TOOL_POLICY_UPDATE"
    MEMORY_UPDATE = "MEMORY_UPDATE"
    VERIFIER_UPDATE = "VERIFIER_UPDATE"
    RETRY_POLICY_UPDATE = "RETRY_POLICY_UPDATE"
    ORCHESTRATION_UPDATE = "ORCHESTRATION_UPDATE"


SUPPORTED_MUTATION_TARGETS = {
    "system_prompt",
    "planner",
    "tool_selection_policy",
    "memory_strategy",
    "verification_strategy",
    "retry_strategy",
    "orchestration_strategy",
}

TARGET_ALIASES = {
    "verifier": "verification_strategy",
    "retry_policy": "retry_strategy",
    "memory": "memory_strategy",
    "tools": "tool_selection_policy",
    "orchestration": "orchestration_strategy",
}

TARGET_TO_MUTATION_TYPE: dict[str, MutationType] = {
    "system_prompt": MutationType.PROMPT_UPDATE,
    "planner": MutationType.PLANNER_UPDATE,
    "tool_selection_policy": MutationType.TOOL_POLICY_UPDATE,
    "memory_strategy": MutationType.MEMORY_UPDATE,
    "verification_strategy": MutationType.VERIFIER_UPDATE,
    "retry_strategy": MutationType.RETRY_POLICY_UPDATE,
    "orchestration_strategy": MutationType.ORCHESTRATION_UPDATE,
}


class MutationValidationError(ValueError):
    """Raised when a proposed mutation violates schema, constraints, or lacks evidence grounding."""
    pass


class Mutation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mutation_type: MutationType
    target: str
    before: Any
    after: Any
    reason: str
    observed_failure: str
    expected_effect: str

    def apply(self, spec: AgentSpec) -> AgentSpec:
        """Applies this mutation to an AgentSpec and returns a new candidate."""
        return apply_mutation(spec, self)


def validate_mutation(
    mutation: Mutation,
    candidate_spec: AgentSpec | None = None,
    current_spec: AgentSpec | None = None,
    failure_report: Any | None = None,
    allowed_failures: set[str] | None = None,
    relevant_evidence: list[str] | None = None,
) -> None:
    """
    Validates a Mutation object against FORGE S6-D invariants:
    1. Target must be one of the supported mutation targets.
    2. Required fields must be non-empty.
    3. 'before' and 'after' states must not be identical (no no-op mutations).
    4. 'after' state must be schema-valid for AgentSpec.
    5. Proposed change must be grounded in actual failure evidence.
    """
    # 1. Target check
    canonical_target = TARGET_ALIASES.get(mutation.target, mutation.target)
    if canonical_target not in SUPPORTED_MUTATION_TARGETS:
        raise MutationValidationError(
            f"Unsupported mutation target '{mutation.target}'. "
            f"Supported targets are: {sorted(SUPPORTED_MUTATION_TARGETS)}"
        )

    # 2. Required fields check
    for field_name in ["target", "reason", "observed_failure", "expected_effect"]:
        val = getattr(mutation, field_name, None)
        if not val or not str(val).strip():
            raise MutationValidationError(f"Mutation field '{field_name}' must be non-empty.")

    if mutation.before is None or mutation.after is None:
        raise MutationValidationError("Mutation 'before' and 'after' states cannot be None.")

    # 3. No-op check
    if mutation.before == mutation.after:
        raise MutationValidationError(
            f"Mutation 'before' and 'after' states are identical for target '{mutation.target}' (no-op mutation)."
        )

    # 4. Schema soundness of 'after'
    try:
        if canonical_target == "planner":
            if isinstance(mutation.after, dict):
                PlannerConfig(**mutation.after)
        elif canonical_target == "verification_strategy":
            if isinstance(mutation.after, dict):
                VerifierConfig(**mutation.after)
        elif canonical_target == "retry_strategy":
            if isinstance(mutation.after, dict):
                RetryPolicy(**mutation.after)
        elif canonical_target == "memory_strategy":
            if isinstance(mutation.after, dict):
                MemoryConfig(**mutation.after)
        elif canonical_target == "orchestration_strategy":
            if isinstance(mutation.after, dict):
                OrchestrationConfig(**mutation.after)
        elif canonical_target == "tool_selection_policy":
            tools_list = mutation.after.get("tools") if isinstance(mutation.after, dict) else mutation.after
            if not isinstance(tools_list, list) or not all(isinstance(t, str) for t in tools_list):
                raise MutationValidationError("tool_selection_policy must specify a list of tool name strings.")
        elif canonical_target == "system_prompt":
            prompt = mutation.after.get("system_prompt") if isinstance(mutation.after, dict) else mutation.after
            if not isinstance(prompt, str) or not prompt.strip():
                raise MutationValidationError("system_prompt 'after' state must be a non-empty string.")
    except Exception as e:
        if isinstance(e, MutationValidationError):
            raise
        raise MutationValidationError(f"Mutation 'after' state failed schema validation for {mutation.target}: {e}")

    # 5. Evidence grounding check
    if allowed_failures is not None:
        if mutation.observed_failure not in allowed_failures:
            raise MutationValidationError(
                f"Mutation observed_failure '{mutation.observed_failure}' is not grounded in observed failures: {sorted(allowed_failures)}"
            )
    elif failure_report is not None:
        report_cats = {c.category for c in getattr(failure_report, "clusters", [])}
        if report_cats and mutation.observed_failure not in report_cats:
            raise MutationValidationError(
                f"Mutation observed_failure '{mutation.observed_failure}' is not grounded in failure cluster report categories: {sorted(report_cats)}"
            )


def apply_mutation(spec: AgentSpec, mutation: Mutation) -> AgentSpec:
    """
    Applies a validated Mutation to an AgentSpec and returns a new candidate AgentSpec.

    Rules:
    1. Original AgentSpec must remain unchanged (returns a new instance).
    2. Candidate must pass AgentSpec validation.
    3. Mutation target must be supported.
    4. Before/after state must be represented accurately.
    5. Pure function: zero database, network, filesystem, or benchmark side effects.
    """
    canonical_target = TARGET_ALIASES.get(mutation.target, mutation.target)
    if canonical_target not in SUPPORTED_MUTATION_TARGETS:
        raise MutationValidationError(
            f"Unsupported mutation target '{mutation.target}'. "
            f"Supported targets are: {sorted(SUPPORTED_MUTATION_TARGETS)}"
        )

    # Deep copy original spec dictionary to guarantee original spec remains unmodified
    candidate_dict = copy.deepcopy(spec.model_dump())

    # Verify and apply based on canonical target
    if canonical_target == "system_prompt":
        actual_current_prompt = spec.system_prompt
        mutation_before_prompt = (
            mutation.before.get("system_prompt")
            if isinstance(mutation.before, dict)
            else str(mutation.before)
        )
        if mutation_before_prompt != actual_current_prompt:
            raise MutationValidationError(
                "Mutation 'before' prompt does not match current AgentSpec system_prompt."
            )
        mutation_after_prompt = (
            mutation.after.get("system_prompt")
            if isinstance(mutation.after, dict)
            else str(mutation.after)
        )
        if not isinstance(mutation_after_prompt, str) or not mutation_after_prompt.strip():
            raise MutationValidationError("Candidate system_prompt must be a non-empty string.")
        candidate_dict["system_prompt"] = mutation_after_prompt

    elif canonical_target == "planner":
        actual_current = spec.planner.model_dump()
        if isinstance(mutation.before, dict) and mutation.before != actual_current:
            raise MutationValidationError(
                "Mutation 'before' planner state does not match current AgentSpec planner."
            )
        if not isinstance(mutation.after, dict):
            raise MutationValidationError("Planner mutation 'after' must be a dictionary.")
        candidate_dict["planner"] = mutation.after

    elif canonical_target == "verification_strategy":
        actual_current = spec.verifier.model_dump()
        if isinstance(mutation.before, dict) and mutation.before != actual_current:
            raise MutationValidationError(
                "Mutation 'before' verifier state does not match current AgentSpec verifier."
            )
        if not isinstance(mutation.after, dict):
            raise MutationValidationError("Verification strategy mutation 'after' must be a dictionary.")
        candidate_dict["verifier"] = mutation.after

    elif canonical_target == "retry_strategy":
        actual_current = spec.retry_policy.model_dump()
        if isinstance(mutation.before, dict) and mutation.before != actual_current:
            raise MutationValidationError(
                "Mutation 'before' retry_policy state does not match current AgentSpec retry_policy."
            )
        if not isinstance(mutation.after, dict):
            raise MutationValidationError("Retry strategy mutation 'after' must be a dictionary.")
        candidate_dict["retry_policy"] = mutation.after

    elif canonical_target == "memory_strategy":
        actual_current = spec.memory.model_dump()
        if isinstance(mutation.before, dict) and mutation.before != actual_current:
            raise MutationValidationError(
                "Mutation 'before' memory state does not match current AgentSpec memory."
            )
        if not isinstance(mutation.after, dict):
            raise MutationValidationError("Memory strategy mutation 'after' must be a dictionary.")
        candidate_dict["memory"] = mutation.after

    elif canonical_target == "orchestration_strategy":
        actual_current = spec.orchestration.model_dump()
        if isinstance(mutation.before, dict) and mutation.before != actual_current:
            raise MutationValidationError(
                "Mutation 'before' orchestration state does not match current AgentSpec orchestration."
            )
        if not isinstance(mutation.after, dict):
            raise MutationValidationError("Orchestration strategy mutation 'after' must be a dictionary.")
        candidate_dict["orchestration"] = mutation.after

    elif canonical_target == "tool_selection_policy":
        actual_current = spec.tools
        mutation_before_tools = (
            mutation.before.get("tools")
            if isinstance(mutation.before, dict)
            else mutation.before
        )
        if isinstance(mutation_before_tools, list) and mutation_before_tools != actual_current:
            raise MutationValidationError(
                "Mutation 'before' tools do not match current AgentSpec tools."
            )
        mutation_after_tools = (
            mutation.after.get("tools")
            if isinstance(mutation.after, dict)
            else mutation.after
        )
        if not isinstance(mutation_after_tools, list) or not all(isinstance(t, str) for t in mutation_after_tools):
            raise MutationValidationError("Tool selection policy 'after' state must be a list of tool names.")
        candidate_dict["tools"] = mutation_after_tools

    # Construct and validate candidate AgentSpec
    try:
        candidate_spec = AgentSpec(**candidate_dict)
    except Exception as e:
        raise MutationValidationError(f"Invalid candidate AgentSpec generated by mutation: {e}")

    return candidate_spec
