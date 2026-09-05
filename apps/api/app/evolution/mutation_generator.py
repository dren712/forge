import copy
from typing import Tuple
from collections import Counter
from app.schemas.agent_spec import AgentSpec
from app.evolution.mutation import Mutation, MutationType
from app.evaluation.failure_analyzer import FailureAnalysis, FailureType
from app.providers.base import LLMProvider


class MutationGenerator:
    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider

    def propose_mutation(
        self,
        current_spec: AgentSpec,
        failures: list[FailureAnalysis],
        generation_number: int,
    ) -> Tuple[AgentSpec, Mutation]:
        """
        Analyzes failure distribution and applies an evidence-driven architectural mutation.
        Returns (candidate_spec, mutation_record).
        """
        candidate_spec = copy.deepcopy(current_spec)
        failure_counts = Counter(f.failure_type for f in failures)

        # 1. Address Verification Failures (Top priority if verifier is unconfigured)
        if failure_counts.get(FailureType.VERIFICATION_FAILURE, 0) > 0 and current_spec.verifier.type == "none":
            before_val = current_spec.verifier.model_dump()
            candidate_spec.verifier.type = "mandatory_tests"
            candidate_spec.verifier.require_zero_failed_tests = True
            candidate_spec.verifier.enforce_before_complete = True

            mutation = Mutation(
                mutation_type=MutationType.VERIFIER_UPDATE,
                target="verifier",
                before=before_val,
                after=candidate_spec.verifier.model_dump(),
                reason=f"Observed {failure_counts[FailureType.VERIFICATION_FAILURE]} verification failure(s) where agent prematurely declared completion.",
                observed_failure="VERIFICATION_FAILURE",
                expected_effect="Enforce automated test execution and pass check before declaring task success, boosting reliability.",
            )
            return candidate_spec, mutation

        # 2. Address Planning Failures & Timeouts
        if (failure_counts.get(FailureType.PLANNING_FAILURE, 0) > 0 or failure_counts.get(FailureType.TIMEOUT, 0) > 0) and current_spec.planner.type == "none":
            before_val = current_spec.planner.model_dump()
            candidate_spec.planner.type = "structured_plan"
            candidate_spec.planner.require_replan_on_error = True
            candidate_spec.orchestration.type = "plan_execute_verify"

            mutation = Mutation(
                mutation_type=MutationType.PLANNER_UPDATE,
                target="planner",
                before=before_val,
                after=candidate_spec.planner.model_dump(),
                reason="Planning failures and timeouts detected due to unstructured exploration.",
                observed_failure="PLANNING_FAILURE",
                expected_effect="Introduce structured goal decomposition to reduce random exploration and speed up resolution.",
            )
            return candidate_spec, mutation

        # 3. Address Tool Failures & Recovery
        if (failure_counts.get(FailureType.TOOL_EXECUTION_FAILURE, 0) > 0 or failure_counts.get(FailureType.RECOVERY_FAILURE, 0) > 0):
            before_val = current_spec.retry_policy.model_dump()
            candidate_spec.retry_policy.max_attempts = max(candidate_spec.retry_policy.max_attempts, 4)
            candidate_spec.retry_policy.retry_on_tool_failure = True
            candidate_spec.retry_policy.backoff_seconds = 0.5

            mutation = Mutation(
                mutation_type=MutationType.RETRY_POLICY_UPDATE,
                target="retry_policy",
                before=before_val,
                after=candidate_spec.retry_policy.model_dump(),
                reason="Observed tool execution errors without automated recovery.",
                observed_failure="RECOVERY_FAILURE",
                expected_effect="Increase retry attempts with backoff and error replanning to recover from transient tool mistakes.",
            )
            return candidate_spec, mutation

        # 4. Strict Test Gate Upgrade
        if current_spec.verifier.type == "mandatory_tests" and candidate_spec.verifier.type != "strict_test_gate":
            before_val = current_spec.verifier.model_dump()
            candidate_spec.verifier.type = "strict_test_gate"

            mutation = Mutation(
                mutation_type=MutationType.VERIFIER_UPDATE,
                target="verifier",
                before=before_val,
                after=candidate_spec.verifier.model_dump(),
                reason="Elevating verification to strict independent sandbox verification gate.",
                observed_failure="VERIFICATION_FAILURE",
                expected_effect="Guarantees independent test suite pass verification in a pristine sub-environment.",
            )
            return candidate_spec, mutation

        # 5. Targeted System Prompt Refinement
        before_prompt = current_spec.system_prompt
        added_constraint = (
            "\n[RULE]: Always read the existing test files to understand edge cases. "
            "Never modify unrelated files or configurations. Always execute test_runner before concluding."
        )
        candidate_spec.system_prompt = before_prompt + added_constraint

        mutation = Mutation(
            mutation_type=MutationType.PROMPT_UPDATE,
            target="system_prompt",
            before={"system_prompt": before_prompt},
            after={"system_prompt": candidate_spec.system_prompt},
            reason="Inject targeted negative constraints and edge-case inspection instructions based on execution feedback.",
            observed_failure="REASONING_FAILURE",
            expected_effect="Sharpen boundary compliance and test alignment.",
        )
        return candidate_spec, mutation
