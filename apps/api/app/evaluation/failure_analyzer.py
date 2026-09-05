import json
import re
from enum import Enum
from typing import Literal, Any
from pydantic import BaseModel, Field

from app.schemas.agent_spec import AgentSpec
from app.agents.state import AgentState
from app.benchmarks.base import BenchmarkTask, TaskEvaluation
from app.evaluation.metrics import ExecutionMetrics
from app.providers.base import LLMProvider


class FailureType(str, Enum):
    REASONING_FAILURE = "REASONING_FAILURE"
    PLANNING_FAILURE = "PLANNING_FAILURE"
    TOOL_SELECTION_FAILURE = "TOOL_SELECTION_FAILURE"
    TOOL_EXECUTION_FAILURE = "TOOL_EXECUTION_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    MEMORY_FAILURE = "MEMORY_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    RECOVERY_FAILURE = "RECOVERY_FAILURE"
    TASK_MISINTERPRETATION = "TASK_MISINTERPRETATION"
    TIMEOUT = "TIMEOUT"
    COST_LIMIT = "COST_LIMIT"


class FailureAnalysis(BaseModel):
    task_id: str
    failure_type: FailureType
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    evidence: list[str] = Field(default_factory=list)
    root_cause: str
    recommended_mutation: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


ANALYZER_SYSTEM_PROMPT = """You are the FORGE Failure Diagnosis Engine.
Analyze the failed agent execution on a benchmark task and categorize the failure into the fixed FORGE taxonomy:
- REASONING_FAILURE
- PLANNING_FAILURE
- TOOL_SELECTION_FAILURE
- TOOL_EXECUTION_FAILURE
- CONTEXT_FAILURE
- MEMORY_FAILURE
- VERIFICATION_FAILURE
- RECOVERY_FAILURE
- TASK_MISINTERPRETATION
- TIMEOUT
- COST_LIMIT

Output a strict JSON object:
{
  "failure_type": "VERIFICATION_FAILURE",
  "severity": "HIGH",
  "evidence": ["Point 1", "Point 2"],
  "root_cause": "Detailed explanation of why the architecture failed",
  "recommended_mutation": {
    "target": "verifier" | "planner" | "system_prompt" | "retry_policy" | "tools",
    "change": "Specific proposed mutation"
  },
  "confidence": 0.95
}
"""


class FailureAnalyzer:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def _rule_based_diagnosis(
        self,
        agent_spec: AgentSpec,
        state: AgentState,
        task: BenchmarkTask,
        evaluation: TaskEvaluation,
    ) -> FailureAnalysis | None:
        """Fast, deterministic diagnosis for clear-cut failure modes."""
        # 1. Verification Failure: Agent claimed completion but never ran tests
        test_runs = [tr for tr in state.tool_results if tr.get("tool") == "test_runner"]
        if not test_runs and not evaluation.passed:
            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType.VERIFICATION_FAILURE,
                severity="HIGH",
                evidence=[
                    "The agent finished execution without invoking 'test_runner'",
                    f"Agent final status was '{state.status}'",
                    f"Verifier passed: {state.verification_passed}",
                ],
                root_cause="Agent lacks a mandatory test verification gate before declaring task completion.",
                recommended_mutation={
                    "target": "verifier",
                    "change": "Set verifier.type to 'mandatory_tests'",
                    "type": "VERIFIER_UPDATE",
                },
                confidence=0.98,
            )

        # 2. Timeout
        if state.status == "TIMEOUT":
            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType.TIMEOUT,
                severity="CRITICAL",
                evidence=[f"Execution exceeded timeout with {state.current_step} steps"],
                root_cause="Agent spent too many steps without converging on a solution.",
                recommended_mutation={
                    "target": "planner",
                    "change": "Enable structured planning to reduce exploration overhead",
                    "type": "PLANNER_UPDATE",
                },
                confidence=0.95,
            )

        # 3. Tool Execution / Recovery Failure
        tool_errors = [tr for tr in state.tool_results if not tr.get("success", False)]
        if len(tool_errors) >= 3 and not evaluation.passed:
            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType.RECOVERY_FAILURE,
                severity="HIGH",
                evidence=[f"{len(tool_errors)} tool executions resulted in errors without effective recovery."],
                root_cause="Agent repeatedly issued invalid tool arguments without adjusting strategy.",
                recommended_mutation={
                    "target": "retry_policy",
                    "change": "Strengthen retry policy and enable structured replan on error",
                    "type": "RETRY_POLICY_UPDATE",
                },
                confidence=0.91,
            )

        # 4. Constraint Violation
        if "Constraint violation" in evaluation.reason:
            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType.PLANNING_FAILURE,
                severity="HIGH",
                evidence=[evaluation.reason],
                root_cause="Agent modified forbidden or unrelated files due to lack of boundary enforcement.",
                recommended_mutation={
                    "target": "system_prompt",
                    "change": "Add explicit negative constraints forbidding modification of unrelated modules",
                    "type": "PROMPT_UPDATE",
                },
                confidence=0.94,
            )

        return None

    async def analyze(
        self,
        agent_spec: AgentSpec,
        state: AgentState,
        task: BenchmarkTask,
        evaluation: TaskEvaluation,
        metrics: ExecutionMetrics,
    ) -> FailureAnalysis:
        # Check rule-based diagnosis first for high reliability
        rule_diagnosis = self._rule_based_diagnosis(agent_spec, state, task, evaluation)
        if rule_diagnosis is not None:
            return rule_diagnosis

        # Otherwise synthesize with LLM
        prompt = (
            f"Task: {task.title}\n"
            f"Issue: {task.issue}\n"
            f"Expected: {task.expected_behavior}\n"
            f"Constraints: {task.constraints}\n"
            f"Evaluation Result: Passed={evaluation.passed}, Reason={evaluation.reason}\n"
            f"Agent State: Status={state.status}, Steps={state.current_step}, Tool Calls={state.tool_call_count}\n"
            f"Errors: {state.errors}\n"
            f"Agent Spec: {agent_spec.model_dump_json()}\n"
        )

        try:
            response = await self.provider.generate(
                messages=[
                    {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            raw = response.content or "{}"
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            candidate = match.group(1) if match else raw
            first_b = candidate.find("{")
            last_b = candidate.rfind("}")
            if first_b != -1 and last_b != -1:
                candidate = candidate[first_b:last_b + 1]
            data = json.loads(candidate)

            ft = data.get("failure_type", "REASONING_FAILURE")
            if ft not in [e.value for e in FailureType]:
                ft = "REASONING_FAILURE"

            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType(ft),
                severity=data.get("severity", "HIGH"),
                evidence=data.get("evidence", [evaluation.reason]),
                root_cause=data.get("root_cause", "Sub-optimal agent strategy during execution."),
                recommended_mutation=data.get("recommended_mutation", {}),
                confidence=float(data.get("confidence", 0.85)),
            )

        except Exception:
            return FailureAnalysis(
                task_id=task.id,
                failure_type=FailureType.REASONING_FAILURE,
                severity="HIGH",
                evidence=[evaluation.reason],
                root_cause="Agent failed to produce the correct solution matching benchmark assertions.",
                recommended_mutation={"target": "verifier", "change": "Enforce mandatory tests"},
                confidence=0.8,
            )
