import pytest
from pydantic import ValidationError

from app.agents.state import AgentState
from app.memory.tool_memory import ToolMemoryStore
from app.agents.reflection import (
    ToolReflectionEngine,
    ReflectedRule,
    GroundedEvidenceError,
    ReflectionCategory,
)


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
        {
            "tool": "github_api",
            "success": False,
            "error": "branch_naming_policy_violation",
            "output": "HTTP 403 Forbidden: Protected branch policy violation. Head branch 'patch-1' must start with one of: ['fix/', 'feat/', 'hotfix/', 'chore/'].",
            "arguments": {"action": "create_pull_request", "head_branch": "patch-1"},
        },
        {
            "tool": "sentry_api",
            "success": False,
            "error": "invalid_resolution_note",
            "output": "HTTP 422 Unprocessable Entity: 'resolution_note' must be detailed (min 15 characters).",
            "arguments": {"action": "resolve_incident", "resolution_note": "short"},
        },
    ]

    store = ToolMemoryStore(experiment_id="exp_reflection_test")
    report = ToolReflectionEngine.reflect_on_execution(state, store)

    assert report.discovered_rules_count == 6
    entries = store.get_entries()
    assert len(entries) == 6

    categories = {e.category for e in entries}
    assert "SCHEMA_QUIRK" in categories
    assert "WORKFLOW_DEPENDENCY" in categories
    assert "CONTEXTUAL_LOGIC" in categories

    # Verify that the generated prompt includes these distilled rules
    prompt = store.format_for_prompt(["linear_api", "slack_api", "crm_api", "github_api", "sentry_api"])
    assert "36-character team UUID" in prompt
    assert "priority must be an integer" in prompt
    assert "Enterprise tier customers" in prompt
    assert "GitHub branch protection" in prompt
    assert "Sentry incident resolution" in prompt


def test_valid_reflection_structured_output():
    """
    Test 1: Valid reflection produces structured, validated ReflectedRule records
    with category, observed_problem, evidence, learned_rule, and confidence.
    """
    trace = [
        {"type": "TOOL_CALL", "payload": {"tool": "linear_api", "action": "create_issue"}},
        {"type": "TOOL_RESULT", "payload": {"status_code": 422, "error": "invalid_team_uuid"}},
    ]
    tool_errors = ["Error 422 Unprocessable Entity: team_id must be a valid 36-character UUID"]
    tool_results = [
        {
            "tool": "linear_api",
            "success": False,
            "error": "invalid_team_uuid",
            "output": "Error 422 Unprocessable Entity: Linear requires a 36-character team UUID.",
            "arguments": {"team_id": "CORE"},
        },
        {
            "tool": "slack_api",
            "success": False,
            "error": "policy_violation_enterprise_channel",
            "output": "Error 400 Bad Request: Enterprise channel policy violation. Messages posted to #enterprise-escalations must contain the tag '[SLA-ALERT]'.",
            "arguments": {"channel": "#enterprise-escalations"},
        },
    ]
    task_context = "Escalate enterprise customer ticket to Linear and Slack"

    rules = ToolReflectionEngine.reflect(
        execution_trace=trace,
        tool_errors=tool_errors,
        tool_results=tool_results,
        task_context=task_context,
    )

    assert len(rules) >= 2
    valid_categories = {"SCHEMA_QUIRK", "CONTEXTUAL_LOGIC", "WORKFLOW_DEPENDENCY", "ERROR_RECOVERY"}

    for r in rules:
        assert isinstance(r, ReflectedRule)
        assert r.category in valid_categories
        assert len(r.observed_problem) >= 3
        assert len(r.evidence) >= 1
        assert len(r.learned_rule) >= 5
        assert 0.0 <= r.confidence <= 1.0
        assert len(r.tool_name) >= 1
        assert len(r.pattern_trigger) >= 1

    # Check Linear rule specific fields
    linear_rules = [r for r in rules if r.tool_name == "linear_api"]
    assert len(linear_rules) == 1
    assert linear_rules[0].category == "SCHEMA_QUIRK"
    assert "36-character team UUID" in linear_rules[0].evidence


def test_malformed_reflection_and_ungrounded_evidence_rejection():
    """
    Test 2: Malformed reflection is rejected by schema validation,
    and candidate rules with invented/hallucinated evidence are rejected.
    """
    corpus_trace = [
        {"type": "TOOL_RESULT", "payload": {"error": "Linear requires a 36-character team UUID."}}
    ]
    tool_results = [
        {"tool": "linear_api", "output": "Linear requires a 36-character team UUID.", "success": False}
    ]

    # 1. Invalid Category rejected by schema
    with pytest.raises(ValidationError):
        ReflectedRule(
            category="HALLUCINATED_CATEGORY",  # Not in Literal
            observed_problem="Valid problem description",
            evidence="Linear requires a 36-character team UUID.",
            learned_rule="Use UUID instead of team slug.",
            confidence=0.9,
            tool_name="linear_api",
            pattern_trigger="create_issue",
        )

    # 2. Out-of-bounds confidence (> 1.0 or < 0.0) rejected by schema
    with pytest.raises(ValidationError):
        ReflectedRule(
            category="SCHEMA_QUIRK",
            observed_problem="Valid problem description",
            evidence="Linear requires a 36-character team UUID.",
            learned_rule="Use UUID instead of team slug.",
            confidence=1.5,  # Invalid
            tool_name="linear_api",
            pattern_trigger="create_issue",
        )

    # 3. Missing required field (e.g. empty observed_problem)
    with pytest.raises(ValidationError):
        ReflectedRule(
            category="SCHEMA_QUIRK",
            observed_problem="",  # min_length=3
            evidence="Linear requires a 36-character team UUID.",
            learned_rule="Use UUID instead of team slug.",
            confidence=0.9,
            tool_name="linear_api",
            pattern_trigger="create_issue",
        )

    # 4. Invented / Hallucinated evidence absent from trace rejected
    fake_candidate = [
        {
            "category": "WORKFLOW_DEPENDENCY",
            "observed_problem": "Imaginary permission error on Linear API",
            "evidence": "CRITICAL 403: User lacks Enterprise Administrator RBAC permissions for OAuth scope",
            "learned_rule": "Request enterprise OAuth token before calling Linear.",
            "confidence": 0.95,
            "tool_name": "linear_api",
            "pattern_trigger": "oauth_scope",
        }
    ]

    with pytest.raises(GroundedEvidenceError) as exc_info:
        ToolReflectionEngine.reflect(
            execution_trace=corpus_trace,
            tool_results=tool_results,
            candidate_rules=fake_candidate,
        )
    assert "absent from execution trace" in str(exc_info.value)


def test_irrelevant_noisy_trace_produces_no_rules():
    """
    Test 3: An execution trace with only benign, successful actions and zero errors
    produces an empty list of reflected rules (no spurious playbooks).
    """
    benign_trace = [
        {"type": "AGENT_STARTED", "payload": {"goal": "List repository files"}},
        {"type": "TOOL_CALL", "payload": {"tool": "file_editor", "action": "list_dir"}},
        {"type": "TOOL_RESULT", "payload": {"status_code": 200, "success": True}},
        {"type": "AGENT_COMPLETED", "payload": {"status": "COMPLETED"}},
    ]
    tool_results = [
        {"tool": "file_editor", "output": "app.py\nREADME.md\ntests/", "success": True, "error": None},
        {"tool": "shell_tool", "output": "Python 3.13.1", "success": True, "error": None},
        {"tool": "search_tool", "output": "Found 3 matching files.", "success": True, "error": None},
    ]

    rules = ToolReflectionEngine.reflect(
        execution_trace=benign_trace,
        tool_errors=[],
        tool_results=tool_results,
        task_context="Explore directory layout",
    )

    # No errors or policy violations -> zero learned rules
    assert rules == []


def test_repeated_observation_reinforces_confidence():
    """
    Test 4: Repeated observation of the same tool error reinforces confidence
    and increments observation count without duplicating playbooks.
    """
    state = AgentState(goal="Triage Linear team issues")
    # Same error encountered twice across steps
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
            "error": "invalid_team_uuid",
            "output": "Error 422 Unprocessable Entity: Linear requires a 36-character team UUID.",
            "arguments": {"action": "create_issue", "team_id": "ENG"},
        },
    ]

    store = ToolMemoryStore(experiment_id="exp_repeat_obs")
    report = ToolReflectionEngine.reflect_on_execution(state, store)

    # Both results matched the same pattern trigger -> exactly 1 entry in store
    entries = store.get_entries()
    assert len(entries) == 1

    entry = entries[0]
    assert entry.tool_name == "linear_api"
    assert entry.category == "SCHEMA_QUIRK"
    assert entry.observation_count == 2
    assert entry.confidence == 1.0  # Boosted from 0.95 + 0.05

