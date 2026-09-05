import pytest
from app.memory.tool_memory import ToolMemoryStore, ToolPlaybookEntry


def test_tool_memory_store_add_and_format():
    store = ToolMemoryStore(experiment_id="exp_test_123")

    # Add first rule
    entry1 = store.add_or_update(
        tool_name="linear_api",
        category="SCHEMA_QUIRK",
        pattern_trigger="create_issue with team_id",
        learned_rule="Linear requires a 36-char team UUID, not slug.",
        evidence="Error 422: Invalid team slug",
        confidence=0.9,
    )
    assert entry1.tool_name == "linear_api"
    assert entry1.observation_count == 1
    assert entry1.confidence == 0.9

    # Add second rule
    entry2 = store.add_or_update(
        tool_name="slack_api",
        category="WORKFLOW_DEPENDENCY",
        pattern_trigger="post_message to #enterprise-escalations",
        learned_rule="Messages must include [SLA-ALERT].",
        confidence=0.85,
    )

    # Re-observe first rule: confidence and count should increase
    entry1_updated = store.add_or_update(
        tool_name="linear_api",
        category="SCHEMA_QUIRK",
        pattern_trigger="create_issue with team_id",
        learned_rule="Linear requires a 36-char team UUID (e.g. 550e8400...).",
        confidence=0.9,
    )
    assert entry1_updated.observation_count == 2
    assert entry1_updated.confidence == 0.95
    assert len(store.get_entries()) == 2

    # Verify prompt formatting
    prompt_text = store.format_for_prompt(["linear_api"])
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" in prompt_text
    assert "LINEAR_API" in prompt_text
    assert "SLACK_API" not in prompt_text  # Filtered by active tools

    all_prompt = store.format_for_prompt(["linear_api", "slack_api"])
    assert "LINEAR_API" in all_prompt
    assert "SLACK_API" in all_prompt
