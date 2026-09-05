import pytest
from app.agents.state import AgentState
from app.memory.tool_memory import ToolMemoryStore
from app.agents.reflection import ToolReflectionEngine


def test_reflection_engine_distills_playbooks_from_errors():
    state = AgentState(goal="Create incident issue in Linear and notify Slack")
    state.tool_results = [
        {
            "tool": "linear_api",
            "success": False,
            "error": "invalid_team_uuid",
            "output": "Error 422 Unprocessable Entity: Linear requires a 36-character team UUID.",
            "arguments": {"action": "create_issue", "team_id": "CORE"},
        },
        {
            "tool": "linear_api",
            "success": False,
            "error": "invalid_priority_type",
            "output": "Error 400 Bad Request: priority must be integer 1 (Urgent), 2 (High), 3 (Normal), or 4 (Low). Received: high",
            "arguments": {"action": "create_issue", "priority": "high"},
        },
        {
            "tool": "slack_api",
            "success": False,
            "error": "policy_violation_enterprise_channel",
            "output": "Error 400 Bad Request: Enterprise channel policy violation. Messages posted to #enterprise-escalations must contain the tag '[SLA-ALERT]'.",
            "arguments": {"action": "post_message", "channel": "#enterprise-escalations", "text": "Alert"},
        },
        {
            "tool": "crm_api",
            "success": True,
            "output": '{"customer": {"tier": "Enterprise", "support_routing_rule": "Urgent enterprise incidents must be broadcast to #enterprise-escalations with [SLA-ALERT] and assigned Linear priority 1."}}',
            "arguments": {"action": "get_customer", "customer_id": "cust_acme_corp"},
        },
    ]

    store = ToolMemoryStore(experiment_id="exp_reflection_test")
    report = ToolReflectionEngine.reflect_on_execution(state, store)

    assert report.discovered_rules_count == 4
    entries = store.get_entries()
    assert len(entries) == 4

    categories = {e.category for e in entries}
    assert "SCHEMA_QUIRK" in categories
    assert "WORKFLOW_DEPENDENCY" in categories
    assert "CONTEXTUAL_LOGIC" in categories

    # Verify that the generated prompt includes these distilled rules
    prompt = store.format_for_prompt(["linear_api", "slack_api", "crm_api"])
    assert "36-character team UUID" in prompt
    assert "priority must be an integer" in prompt
    assert "Enterprise tier customers" in prompt
