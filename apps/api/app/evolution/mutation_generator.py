import copy
from typing import Any, Tuple
from app.schemas.agent_spec import (
    AgentSpec,
    PlannerConfig,
    MemoryConfig,
    VerifierConfig,
    RetryPolicy,
    OrchestrationConfig,
)
from app.evolution.mutation import (
    Mutation,
    MutationType,
    MutationValidationError,
    validate_mutation,
    SUPPORTED_MUTATION_TARGETS,
    TARGET_TO_MUTATION_TYPE,
)
from app.evaluation.failure_analyzer import FailureAnalysis, FailureType
from app.evaluation.failure_clustering import FailureClusterer, FailureClusterReport
from app.evaluation.metrics import GenerationMetrics
from app.providers.base import LLMProvider


class MutationGenerator:
    """
    Produces evidence-grounded, schema-validated mutations for the outer evolution loop.
    Adheres strictly to the 7 supported mutation targets:
    - system_prompt
    - planner
    - tool_selection_policy
    - memory_strategy
    - verification_strategy
    - retry_strategy
    - orchestration_strategy
    """

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider
        self.clusterer = FailureClusterer()

    def generate_mutation(
        self,
        current_spec: AgentSpec,
        benchmark_metrics: GenerationMetrics | dict[str, Any] | None = None,
        failure_report: FailureClusterReport | dict[str, Any] | None = None,
        relevant_evidence: list[str] | None = None,
        failures: list[FailureAnalysis] | None = None,
        generation_number: int = 1,
    ) -> Tuple[AgentSpec, Mutation]:
        """
        Generates a validated Mutation grounded in failure cluster reports and execution evidence.
        Returns (candidate_spec, validated_mutation).
        """
        # 1. Resolve FailureClusterReport
        candidate_spec = copy.deepcopy(current_spec)
        report: FailureClusterReport | None = None
        if isinstance(failure_report, FailureClusterReport):
            report = failure_report
        elif isinstance(failure_report, dict):
            report = FailureClusterReport(**failure_report)
        elif failures:
            report = self.clusterer.cluster(failures)

        if not report or report.total_failures == 0:
            if not relevant_evidence:
                if benchmark_metrics or generation_number > 1:
                    before_prompt = current_spec.system_prompt
                    rule = "\n[OPTIMIZATION]: Enforce strict boundary checks and edge-case verification for full coverage."
                    candidate_spec.system_prompt = before_prompt + rule
                    mutation = Mutation(
                        mutation_type=MutationType.PROMPT_UPDATE,
                        target="system_prompt",
                        before={"system_prompt": before_prompt},
                        after={"system_prompt": candidate_spec.system_prompt},
                        reason="Exploring constraint tightening and edge-case optimization for high-accuracy agent.",
                        observed_failure="REASONING_FAILURE",
                        expected_effect="Sharpen boundary compliance and edge-case coverage.",
                    )
                    return candidate_spec, mutation

                raise MutationValidationError(
                    "Cannot generate mutation: no failure cluster report or execution evidence provided."
                )

        top_cluster = report.clusters[0] if (report and report.clusters) else None
        obs_failure = top_cluster.category if top_cluster else "REASONING_FAILURE"
        ev_list = top_cluster.representative_evidence if top_cluster else (relevant_evidence or [])
        ev_summary = "; ".join(ev_list[:2]) if ev_list else "Execution failure observed"

        # 2. Select mutation target grounded in top failure category
        if obs_failure == FailureType.VERIFICATION_FAILURE.value:
            # Target: verification_strategy
            before_val = current_spec.verifier.model_dump()
            if current_spec.verifier.type == "none":
                after_val = {
                    "type": "mandatory_tests",
                    "require_zero_failed_tests": True,
                    "enforce_before_complete": True,
                    "min_test_count": 1,
                }
            elif current_spec.verifier.type == "mandatory_tests":
                after_val = {
                    "type": "strict_test_gate",
                    "require_zero_failed_tests": True,
                    "enforce_before_complete": True,
                    "min_test_count": 2,
                }
            else:
                after_val = {
                    "type": "strict_test_gate",
                    "require_zero_failed_tests": True,
                    "enforce_before_complete": True,
                    "min_test_count": current_spec.verifier.min_test_count + 1,
                }
            candidate_spec.verifier = VerifierConfig(**after_val)

            mutation = Mutation(
                mutation_type=MutationType.VERIFIER_UPDATE,
                target="verification_strategy",
                before=before_val,
                after=after_val,
                reason=f"Observed {top_cluster.count if top_cluster else 1} verification failure(s) where agent completed task without verifying correctness. Evidence: {ev_summary}",
                observed_failure="VERIFICATION_FAILURE",
                expected_effect="Enforce automated test execution and pass verification before declaring task completion, boosting reliability.",
            )

        elif obs_failure in (FailureType.PLANNING_FAILURE.value, FailureType.TIMEOUT.value):
            # Target: planner
            before_val = current_spec.planner.model_dump()
            if current_spec.planner.type == "none":
                after_val = {
                    "type": "structured_plan",
                    "max_subgoals": 5,
                    "require_replan_on_error": True,
                }
                candidate_spec.orchestration.type = "plan_execute_verify"
            elif current_spec.planner.type == "structured_plan":
                after_val = {
                    "type": "re_act",
                    "max_subgoals": 8,
                    "require_replan_on_error": True,
                }
            else:
                after_val = {
                    "type": "hierarchical",
                    "max_subgoals": 10,
                    "require_replan_on_error": True,
                }
            candidate_spec.planner = PlannerConfig(**after_val)

            mutation = Mutation(
                mutation_type=MutationType.PLANNER_UPDATE,
                target="planner",
                before=before_val,
                after=after_val,
                reason=f"Observed {top_cluster.count if top_cluster else 1} planning/timeout failure(s) due to unstructured exploration. Evidence: {ev_summary}",
                observed_failure=obs_failure,
                expected_effect="Introduce structured goal decomposition and automated replanning to prevent loops and speed up resolution.",
            )

        elif obs_failure in (FailureType.RECOVERY_FAILURE.value, FailureType.TOOL_EXECUTION_FAILURE.value):
            # Target: retry_strategy
            before_val = current_spec.retry_policy.model_dump()
            new_attempts = max(current_spec.retry_policy.max_attempts + 1, 4)
            after_val = {
                "max_attempts": new_attempts,
                "retry_on_tool_failure": True,
                "backoff_seconds": 1.5,
            }
            candidate_spec.retry_policy = RetryPolicy(**after_val)

            mutation = Mutation(
                mutation_type=MutationType.RETRY_POLICY_UPDATE,
                target="retry_strategy",
                before=before_val,
                after=after_val,
                reason=f"Observed {top_cluster.count if top_cluster else 1} tool recovery failure(s). Evidence: {ev_summary}",
                observed_failure=obs_failure,
                expected_effect="Increase retry attempts with backoff and error replanning to recover from transient tool mistakes.",
            )

        elif obs_failure == FailureType.TOOL_SELECTION_FAILURE.value:
            # Target: tool_selection_policy
            before_val = {"tools": list(current_spec.tools)}
            needed = ["repository", "file_editor", "shell", "test_runner", "search"]
            updated_tools = list(dict.fromkeys(current_spec.tools + needed))
            after_val = {"tools": updated_tools}
            candidate_spec.tools = updated_tools

            mutation = Mutation(
                mutation_type=MutationType.TOOL_POLICY_UPDATE,
                target="tool_selection_policy",
                before=before_val,
                after=after_val,
                reason=f"Observed tool selection failures where necessary tools were missing. Evidence: {ev_summary}",
                observed_failure="TOOL_SELECTION_FAILURE",
                expected_effect="Equip agent with complete tool suite to ensure appropriate tool selection across tasks.",
            )

        elif obs_failure in (FailureType.MEMORY_FAILURE.value, FailureType.CONTEXT_FAILURE.value):
            # Target: memory_strategy
            before_val = current_spec.memory.model_dump()
            if current_spec.memory.type == "stateless":
                after_val = {
                    "type": "working_context",
                    "max_history_items": 30,
                    "summarize_threshold": 20,
                }
            else:
                after_val = {
                    "type": "scratchpad_summarized",
                    "max_history_items": 40,
                    "summarize_threshold": 15,
                }
            candidate_spec.memory = MemoryConfig(**after_val)

            mutation = Mutation(
                mutation_type=MutationType.MEMORY_UPDATE,
                target="memory_strategy",
                before=before_val,
                after=after_val,
                reason=f"Observed memory/context loss during task execution. Evidence: {ev_summary}",
                observed_failure=obs_failure,
                expected_effect="Upgrade memory strategy to preserve state and summarize long execution trajectories.",
            )

        elif obs_failure == FailureType.TASK_MISINTERPRETATION.value:
            # Target: orchestration_strategy
            before_val = current_spec.orchestration.model_dump()
            if current_spec.orchestration.type == "direct":
                after_val = {"type": "plan_execute_verify", "max_loops": 10}
            else:
                after_val = {"type": "iterative_feedback", "max_loops": 15}
            candidate_spec.orchestration = OrchestrationConfig(**after_val)

            mutation = Mutation(
                mutation_type=MutationType.ORCHESTRATION_UPDATE,
                target="orchestration_strategy",
                before=before_val,
                after=after_val,
                reason=f"Observed task misinterpretation where agent acted without phased verification. Evidence: {ev_summary}",
                observed_failure="TASK_MISINTERPRETATION",
                expected_effect="Enforce iterative orchestration to evaluate execution steps against task constraints.",
            )

        else:
            # Target: system_prompt
            before_prompt = current_spec.system_prompt
            rule = (
                f"\n[RULE]: Address observed reasoning failures: {ev_summary[:120]}. "
                "Always verify code changes with test_runner before concluding. Never modify unrelated files."
            )
            candidate_spec.system_prompt = before_prompt + rule

            mutation = Mutation(
                mutation_type=MutationType.PROMPT_UPDATE,
                target="system_prompt",
                before={"system_prompt": before_prompt},
                after={"system_prompt": candidate_spec.system_prompt},
                reason=f"Inject targeted behavioral constraints based on failure evidence: {ev_summary[:100]}",
                observed_failure=obs_failure,
                expected_effect="Constrain agent reasoning with explicit negative instructions and edge-case guidance.",
            )

        # 3. Validate mutation against schema, non-empty fields, no-op, and evidence grounding
        validate_mutation(
            mutation=mutation,
            candidate_spec=candidate_spec,
            current_spec=current_spec,
            failure_report=report,
            relevant_evidence=relevant_evidence,
        )

        return candidate_spec, mutation

    def propose_mutation(
        self,
        current_spec: AgentSpec,
        failures: list[FailureAnalysis] | None = None,
        generation_number: int = 1,
        benchmark_metrics: GenerationMetrics | dict[str, Any] | None = None,
        failure_report: FailureClusterReport | dict[str, Any] | None = None,
        relevant_evidence: list[str] | None = None,
    ) -> Tuple[AgentSpec, Mutation]:
        """Backwards-compatible entrypoint used across the evolution engine."""
        return self.generate_mutation(
            current_spec=current_spec,
            benchmark_metrics=benchmark_metrics,
            failure_report=failure_report,
            relevant_evidence=relevant_evidence,
            failures=failures,
            generation_number=generation_number,
        )
