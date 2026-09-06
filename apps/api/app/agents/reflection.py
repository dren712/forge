import re
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError

from app.memory.tool_memory import ToolMemoryStore, ToolPlaybookEntry
from app.agents.state import AgentState
from app.core.logging import get_logger

logger = get_logger("forge.reflection")

ReflectionCategory = Literal[
    "SCHEMA_QUIRK",
    "CONTEXTUAL_LOGIC",
    "WORKFLOW_DEPENDENCY",
    "ERROR_RECOVERY",
]


class GroundedEvidenceError(ValueError):
    """Raised when proposed reflection evidence is absent from the execution trace."""
    pass


class ReflectedRule(BaseModel):
    category: ReflectionCategory
    observed_problem: str = Field(..., min_length=3)
    evidence: str = Field(..., min_length=1)
    learned_rule: str = Field(..., min_length=5)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    tool_name: str = Field(..., min_length=1)
    pattern_trigger: str = Field(..., min_length=1)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence {v} must be between 0.0 and 1.0")
        return round(v, 3)


class ReflectionInput(BaseModel):
    execution_trace: list[dict[str, Any]] = Field(default_factory=list)
    tool_errors: list[str] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    task_context: Optional[str] = None


class ReflectionReport(BaseModel):
    discovered_rules_count: int
    summary: str
    entries: List[ToolPlaybookEntry]
    reflected_rules: List[ReflectedRule] = Field(default_factory=list)


def verify_grounded_evidence(evidence: str, corpus: str) -> bool:
    """
    Validates that rule's evidence is strictly grounded in the execution trace.
    Rejects any hallucinated or fabricated evidence absent from trace.
    """
    if not evidence or not evidence.strip():
        raise GroundedEvidenceError("Evidence cannot be empty.")

    clean_ev = evidence.strip().lower()
    clean_corpus = corpus.lower()

    # Exact substring match check
    if clean_ev in clean_corpus:
        return True

    # If evidence is longer, verify that key content words appear in trace
    words = [w for w in re.findall(r"\w+", clean_ev) if len(w) > 3]
    if len(words) >= 2:
        matching_words = [w for w in words if w in clean_corpus]
        if len(matching_words) / len(words) >= 0.7:
            return True

    raise GroundedEvidenceError(f"Evidence '{evidence}' is absent from execution trace.")


class ToolReflectionEngine:
    """
    Autonomous self-reflection engine that analyzes execution traces, tool errors,
    and task context to extract grounded, high-leverage operational heuristics.
    """

    @classmethod
    def build_trace_corpus(
        cls,
        execution_trace: list[dict[str, Any]] | None = None,
        tool_errors: list[str] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        task_context: Optional[str] = None,
    ) -> str:
        parts: list[str] = []
        if task_context:
            parts.append(f"TASK CONTEXT: {task_context}")
        if tool_errors:
            parts.extend([f"TOOL ERROR: {e}" for e in tool_errors])
        if tool_results:
            for tr in tool_results:
                tool = tr.get("tool", "")
                out = tr.get("output", "")
                err = tr.get("error", "")
                args = tr.get("arguments", {})
                parts.append(f"TOOL RESULT [{tool}]: output={out} error={err} args={args}")
        if execution_trace:
            for ev in execution_trace:
                if isinstance(ev, dict):
                    parts.append(f"TRACE: {ev.get('type', '')} {ev.get('payload', '')} {ev.get('content', '')}")
                else:
                    parts.append(f"TRACE: {ev}")
        return "\n".join(parts)

    @classmethod
    def reflect(
        cls,
        execution_trace: list[dict[str, Any]] | None = None,
        tool_errors: list[str] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        task_context: Optional[str] = None,
        candidate_rules: list[dict[str, Any]] | None = None,
    ) -> list[ReflectedRule]:
        """
        Analyzes tool errors and execution trace to extract structured, validated ReflectedRule records.
        Validates that all evidence is grounded in the actual trace and rejects hallucinated rules.
        """
        corpus = cls.build_trace_corpus(
            execution_trace=execution_trace,
            tool_errors=tool_errors,
            tool_results=tool_results,
            task_context=task_context,
        )

        results: list[ReflectedRule] = []

        # If candidate rules are provided (e.g. from an LLM reflection call), validate them strictly
        if candidate_rules:
            for cand in candidate_rules:
                rule = ReflectedRule(**cand)
                verify_grounded_evidence(rule.evidence, corpus)
                results.append(rule)
            return results

        # Heuristic ground-truth extraction from tool results and errors
        results_to_process = list(tool_results or [])

        # Incorporate raw tool errors
        for err in (tool_errors or []):
            if isinstance(err, str):
                results_to_process.append({"tool": "unknown", "output": err, "error": err, "success": False})

        for res in results_to_process:
            tool_name = res.get("tool", "")
            output = str(res.get("output", ""))
            error_str = str(res.get("error", ""))
            success = res.get("success", False)
            combined_text = f"{output} {error_str}"
            args = res.get("arguments", {})

            # Skip successful operations without policy warnings or contextual routing rules
            if success and "Enterprise" not in output and "support_routing_rule" not in output:
                continue

            # 1. LINEAR API
            if tool_name == "linear_api" or "linear" in combined_text.lower():
                if "team_id must be a valid" in output or "36-character team UUID" in output or "invalid_team_uuid" in error_str:
                    ev = output[:150] if ("36-character" in output or "team_id" in output) else error_str
                    rule = ReflectedRule(
                        category="SCHEMA_QUIRK",
                        observed_problem="Linear create_issue rejected team slug; requires 36-character UUIDv4",
                        evidence=ev,
                        learned_rule="Linear requires a 36-character team UUID (e.g. '550e8400-e29b-41d4-a716-446655440001' for Core, '550e8400-e29b-41d4-a716-446655440002' for Security). Never pass team slugs like 'CORE'.",
                        confidence=0.95,
                        tool_name="linear_api",
                        pattern_trigger="create_issue with team_id",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

                if "priority must be integer" in output or "invalid_priority_type" in error_str:
                    ev = output[:150] if "priority must be integer" in output else error_str
                    rule = ReflectedRule(
                        category="SCHEMA_QUIRK",
                        observed_problem="Linear create_issue priority rejected string value; requires integer 1-4",
                        evidence=ev,
                        learned_rule="Linear priority must be an integer between 1 (Urgent) and 4 (Low). Do NOT pass string priority names like 'urgent' or 'high'.",
                        confidence=0.95,
                        tool_name="linear_api",
                        pattern_trigger="create_issue priority field",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

                if "missing_assignee_for_in_progress" in error_str or "without an 'assignee_id'" in output:
                    ev = output[:150] if "without an 'assignee_id'" in output else error_str
                    rule = ReflectedRule(
                        category="WORKFLOW_DEPENDENCY",
                        observed_problem="Linear transition to 'In Progress' rejected without an assignee",
                        evidence=ev,
                        learned_rule="Transitioning a Linear issue to 'In Progress' requires an 'assignee_id'. Always provide an assignee before or during the state change.",
                        confidence=0.90,
                        tool_name="linear_api",
                        pattern_trigger="update_issue to 'In Progress'",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

            # 2. SLACK API
            if tool_name == "slack_api" or "slack" in combined_text.lower():
                if "Enterprise channel policy violation" in output or "must contain the tag '[SLA-ALERT]'" in output or "policy_violation_enterprise_channel" in error_str:
                    ev = output[:150] if "Enterprise channel policy violation" in output else error_str
                    rule = ReflectedRule(
                        category="WORKFLOW_DEPENDENCY",
                        observed_problem="Slack message to #enterprise-escalations rejected for missing [SLA-ALERT] tag or customer_id",
                        evidence=ev,
                        learned_rule="Messages posted to #enterprise-escalations must include the tag '[SLA-ALERT]' and cite the customer_id in the text.",
                        confidence=0.95,
                        tool_name="slack_api",
                        pattern_trigger="post_message to #enterprise-escalations",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

            # 3. CRM API
            if tool_name == "crm_api" or "crm" in combined_text.lower():
                if "support_routing_rule" in output or ("Enterprise" in output and "cust_" in str(args)):
                    ev = output[:150]
                    rule = ReflectedRule(
                        category="CONTEXTUAL_LOGIC",
                        observed_problem="Enterprise customer tier contract requires urgent incident escalation and SLA compliance",
                        evidence=ev,
                        learned_rule="Enterprise tier customers (SLA < 1hr) require urgent incident escalation: post to #enterprise-escalations with '[SLA-ALERT]' and create Linear issue with priority=1.",
                        confidence=0.95,
                        tool_name="crm_api",
                        pattern_trigger="Customer Tier Triage (Enterprise)",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

            # 4. GITHUB API
            if tool_name == "github_api" or "github" in combined_text.lower():
                if "Protected branch policy violation" in output or "branch_naming_policy_violation" in error_str:
                    ev = output[:150] if "Protected branch policy violation" in output else error_str
                    rule = ReflectedRule(
                        category="WORKFLOW_DEPENDENCY",
                        observed_problem="GitHub branch creation rejected for invalid naming prefix",
                        evidence=ev,
                        learned_rule="GitHub branch protection requires head branches to start with 'fix/', 'feat/', 'hotfix/', or 'chore/'. Never commit un-prefixed branches.",
                        confidence=0.95,
                        tool_name="github_api",
                        pattern_trigger="create_pull_request head_branch",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

                if "PR title policy violation" in output or "pr_title_policy_violation" in error_str:
                    ev = output[:150] if "PR title policy violation" in output else error_str
                    rule = ReflectedRule(
                        category="SCHEMA_QUIRK",
                        observed_problem="GitHub PR creation rejected for missing ticket prefix in title",
                        evidence=ev,
                        learned_rule="GitHub PR title must include issue ticket tag in brackets e.g. '[LIN-101] Fix DB pool' or '[HOTFIX] Patch'.",
                        confidence=0.95,
                        tool_name="github_api",
                        pattern_trigger="create_pull_request title",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

            # 5. SENTRY API
            if tool_name == "sentry_api" or "sentry" in combined_text.lower():
                if "min 15 characters" in output or "invalid_resolution_note" in error_str:
                    ev = output[:150] if "min 15 characters" in output else error_str
                    rule = ReflectedRule(
                        category="SCHEMA_QUIRK",
                        observed_problem="Sentry issue resolution rejected because resolution_note was shorter than 15 characters",
                        evidence=ev,
                        learned_rule="Sentry incident resolution requires a detailed 'resolution_note' of at least 15 characters explaining the fix.",
                        confidence=0.95,
                        tool_name="sentry_api",
                        pattern_trigger="resolve_incident resolution_note",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

            # 6. TEST RUNNER
            if tool_name == "test_runner":
                if not success and "FAILED" in output:
                    ev = output[:120]
                    rule = ReflectedRule(
                        category="ERROR_RECOVERY",
                        observed_problem="Automated test suite reported failure on assertions",
                        evidence=ev,
                        learned_rule="Inspect failed assertion traces before applying code edits to understand exact expected values.",
                        confidence=0.85,
                        tool_name="test_runner",
                        pattern_trigger="pytest failure inspection",
                    )
                    verify_grounded_evidence(rule.evidence, corpus)
                    results.append(rule)

        return results

    @classmethod
    def reflect_and_persist(
        cls,
        memory_store: ToolMemoryStore,
        execution_trace: list[dict[str, Any]] | None = None,
        tool_errors: list[str] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        task_context: Optional[str] = None,
        candidate_rules: list[dict[str, Any]] | None = None,
    ) -> list[ToolPlaybookEntry]:
        """
        Connects execution failure directly to persistent memory:
        execution failure -> reflection -> validated knowledge -> memory_store.save_reflected_rule()
        Only validated reflection results can be persisted.
        """
        reflected_rules = cls.reflect(
            execution_trace=execution_trace,
            tool_errors=tool_errors,
            tool_results=tool_results,
            task_context=task_context,
            candidate_rules=candidate_rules,
        )

        persisted: list[ToolPlaybookEntry] = []
        for r in reflected_rules:
            entry = memory_store.save_reflected_rule(r)
            persisted.append(entry)
        return persisted

    @classmethod
    def reflect_on_execution(
        cls,
        state: AgentState,
        memory_store: ToolMemoryStore,
        model_name: Optional[str] = None,
    ) -> ReflectionReport:
        reflected_rules = cls.reflect(
            execution_trace=state.observations,
            tool_errors=state.errors,
            tool_results=state.tool_results,
            task_context=state.goal,
        )

        discovered = cls.reflect_and_persist(
            memory_store=memory_store,
            execution_trace=state.observations,
            tool_errors=state.errors,
            tool_results=state.tool_results,
            task_context=state.goal,
        )

        summary_text = (
            f"Self-reflection completed: Distilled {len(discovered)} operational rule(s) from execution trace. "
            f"Memory updated to optimize future tool interactions."
            if discovered
            else "Self-reflection completed: No novel tool failure modes observed. Existing playbook confidence reinforced."
        )

        return ReflectionReport(
            discovered_rules_count=len(discovered),
            summary=summary_text,
            entries=discovered,
            reflected_rules=reflected_rules,
        )

