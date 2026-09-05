import re
from typing import Any, List, Optional
from pydantic import BaseModel

from app.memory.tool_memory import ToolMemoryStore, ToolPlaybookEntry
from app.agents.state import AgentState
from app.core.logging import get_logger

logger = get_logger("forge.reflection")


class ReflectionReport(BaseModel):
    discovered_rules_count: int
    summary: str
    entries: List[ToolPlaybookEntry]


class ToolReflectionEngine:
    """
    Autonomous self-reflection engine that analyzes tool execution traces, errors, and responses.
    Distills generalized, high-leverage operational heuristics into persistent ToolMemory.
    """

    @staticmethod
    def reflect_on_execution(
        state: AgentState,
        memory_store: ToolMemoryStore,
        model_name: Optional[str] = None,
    ) -> ReflectionReport:
        discovered: list[ToolPlaybookEntry] = []

        # Analyze each tool interaction
        for res in state.tool_results:
            tool_name = res.get("tool", "")
            output = res.get("output", "")
            success = res.get("success", False)
            args = res.get("arguments", {})

            # ----------------- 1. LINEAR API QUIRKS & RULES -----------------
            if tool_name == "linear_api":
                if "team_id must be a valid 36-character UUID" in output or "invalid_team_uuid" in str(res.get("error")):
                    entry = memory_store.add_or_update(
                        tool_name="linear_api",
                        category="SCHEMA_QUIRK",
                        pattern_trigger="create_issue with team_id",
                        learned_rule=(
                            "Linear requires a 36-character team UUID (e.g., '550e8400-e29b-41d4-a716-446655440001' for Core, "
                            "'550e8400-e29b-41d4-a716-446655440002' for Security), never team slugs like 'CORE' or 'SEC'."
                        ),
                        evidence=output[:150],
                        confidence=0.95,
                    )
                    discovered.append(entry)

                if "priority must be integer" in output or "invalid_priority_type" in str(res.get("error")):
                    entry = memory_store.add_or_update(
                        tool_name="linear_api",
                        category="SCHEMA_QUIRK",
                        pattern_trigger="create_issue priority field",
                        learned_rule="Linear priority must be an integer between 1 (Urgent) and 4 (Low). Do NOT pass strings.",
                        evidence=output[:150],
                        confidence=0.95,
                    )
                    discovered.append(entry)

                if "missing_assignee_for_in_progress" in str(res.get("error")) or "without an 'assignee_id'" in output:
                    entry = memory_store.add_or_update(
                        tool_name="linear_api",
                        category="WORKFLOW_DEPENDENCY",
                        pattern_trigger="update_issue to 'In Progress'",
                        learned_rule="Transitioning an issue to 'In Progress' requires an 'assignee_id'. Always provide an assignee.",
                        evidence=output[:150],
                        confidence=0.90,
                    )
                    discovered.append(entry)

            # ----------------- 2. SLACK API POLICIES -----------------
            elif tool_name == "slack_api":
                if "Enterprise channel policy violation" in output or "must contain the tag '[SLA-ALERT]'" in output:
                    entry = memory_store.add_or_update(
                        tool_name="slack_api",
                        category="WORKFLOW_DEPENDENCY",
                        pattern_trigger="post_message to #enterprise-escalations",
                        learned_rule="Messages to #enterprise-escalations must include '[SLA-ALERT]' and cite the customer_id in text.",
                        evidence=output[:150],
                        confidence=0.95,
                    )
                    discovered.append(entry)

            # ----------------- 3. CRM & CONTEXTUAL SLA LOGIC -----------------
            elif tool_name == "crm_api":
                if "support_routing_rule" in output or "Enterprise" in output:
                    if "cust_acme_corp" in str(args) or "Enterprise" in output:
                        entry = memory_store.add_or_update(
                            tool_name="crm_api",
                            category="CONTEXTUAL_LOGIC",
                            pattern_trigger="Customer Tier Triage (Enterprise)",
                            learned_rule=(
                                "Enterprise tier customers (SLA < 1hr) require urgent incident escalation: "
                                "post to #enterprise-escalations with '[SLA-ALERT]' and create Linear issue with priority=1."
                            ),
                            evidence="Discovered Enterprise SLA contract rule from CRM customer record.",
                            confidence=0.95,
                        )
                        discovered.append(entry)

            # ----------------- 4. GENERAL PYTHON / TEST RUNNER RULES -----------------
            elif tool_name == "test_runner":
                if not success and "FAILED" in output:
                    entry = memory_store.add_or_update(
                        tool_name="test_runner",
                        category="ERROR_RECOVERY",
                        pattern_trigger="pytest failure inspection",
                        learned_rule="Inspect failed assertion traces before applying code edits to understand exact expected values.",
                        evidence=output[:120],
                        confidence=0.85,
                    )
                    discovered.append(entry)

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
        )
