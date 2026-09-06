import pytest
from pathlib import Path
from app.memory.tool_memory import ToolMemoryStore, ToolPlaybookEntry
from app.core.database import AsyncSessionLocal, init_db
from app.services.experiment_service import ExperimentService
from app.schemas.api import ExperimentCreateRequest


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


def test_empty_memory_store_returns_no_learned_context():
    """Proves that an uninitialized or empty memory store returns zero prompt injection."""
    empty_store = ToolMemoryStore(experiment_id="exp_empty_test")

    # Raw entries must be empty
    assert empty_store.get_entries() == []
    assert empty_store.retrieve_playbooks() == []
    assert empty_store.retrieve_playbooks(tool_names=["linear_api", "slack_api"]) == []

    # Prompt format must strictly evaluate to empty string
    assert empty_store.format_for_prompt() == ""
    assert empty_store.format_for_prompt(["linear_api"]) == ""
    assert empty_store.format_for_prompt(["github_api", "sentry_api", "crm_api"]) == ""


@pytest.mark.asyncio
async def test_save_persist_new_execution_retrieve_cycle():
    """
    Proves the full persistence contract:
    save → persist to database → new execution instance → retrieve relevant playbooks
    """
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create experiment parent entity
        req = ExperimentCreateRequest(
            name="Persistence Contract Verification",
            goal="Test memory persistence across separate execution lifecycles",
            benchmark_id="third_party_automation",
            tools=["linear_api", "slack_api", "sentry_api"],
        )
        exp = await ExperimentService.create_experiment(db, req)
        exp_id = exp.id

        # --- EXECUTION 1: Learn and Save Playbooks ---
        store_exec1 = ToolMemoryStore(experiment_id=exp_id)
        assert store_exec1.format_for_prompt() == ""

        # Save playbook with all contract fields
        saved1 = store_exec1.save_playbook(
            tool_name="linear_api",
            category="SCHEMA_QUIRK",
            pattern_trigger="create_issue with team_id",
            learned_rule="Linear requires a 36-char team UUID (550e8400-e29b-41d4-a716-446655440001).",
            evidence="HTTP 422 invalid_team_uuid: Expected UUIDv4.",
            confidence=0.95,
        )
        assert saved1.created_at is not None
        assert saved1.updated_at is not None
        assert saved1.confidence == 0.95

        saved2 = store_exec1.save_playbook(
            tool_name="slack_api",
            category="WORKFLOW_DEPENDENCY",
            pattern_trigger="post_message to #enterprise-escalations",
            learned_rule="Messages must include [SLA-ALERT] and cite customer_id.",
            evidence="HTTP 400 policy_violation_enterprise_channel.",
            confidence=0.90,
        )

        saved3 = store_exec1.save_playbook(
            tool_name="sentry_api",
            category="SCHEMA_QUIRK",
            pattern_trigger="resolve_incident resolution_note",
            learned_rule="Sentry incident resolution requires a note with >= 15 chars.",
            evidence="HTTP 422 invalid_resolution_note.",
            confidence=0.88,
        )

        # Persist execution 1 memory store to SQLite database
        await store_exec1.sync_to_db(db)

        # --- EXECUTION 2: Brand New Store Instance (Simulating New Execution) ---
        store_exec2 = ToolMemoryStore(experiment_id=exp_id)
        # Prior to database sync, new execution has zero playbooks
        assert len(store_exec2.get_entries()) == 0
        assert store_exec2.format_for_prompt(["linear_api"]) == ""

        # Sync from persistent storage
        await store_exec2.sync_from_db(db)

        # Retrieve relevant playbooks in new execution
        retrieved_all = store_exec2.get_entries()
        assert len(retrieved_all) == 3

        # Verify exact field preservation across executions
        linear_entries = store_exec2.retrieve_playbooks(tool_names=["linear_api"])
        assert len(linear_entries) == 1
        retrieved_linear = linear_entries[0]
        assert retrieved_linear.tool_name == "linear_api"
        assert retrieved_linear.category == "SCHEMA_QUIRK"
        assert retrieved_linear.pattern_trigger == "create_issue with team_id"
        assert "550e8400" in retrieved_linear.learned_rule
        assert "HTTP 422 invalid_team_uuid" in retrieved_linear.evidence
        assert retrieved_linear.confidence == 0.95
        assert retrieved_linear.created_at is not None

        # Verify selective category and confidence filtering
        high_conf = store_exec2.retrieve_playbooks(min_confidence=0.92)
        assert len(high_conf) == 1
        assert high_conf[0].tool_name == "linear_api"

        quirks = store_exec2.retrieve_playbooks(category="SCHEMA_QUIRK")
        assert len(quirks) == 2
        assert {q.tool_name for q in quirks} == {"linear_api", "sentry_api"}

        # Verify prompt injection in new execution
        new_prompt = store_exec2.format_for_prompt(["linear_api", "sentry_api"])
        assert "LINEAR_API" in new_prompt
        assert "SENTRY_API" in new_prompt
        assert "SLACK_API" not in new_prompt  # Filtered out
        assert "550e8400-e29b-41d4-a716-446655440001" in new_prompt
        assert "Confidence: 95%" in new_prompt


def test_deterministic_serialization_and_file_persistence(tmp_path: Path):
    """Proves deterministic serialization and local file persistence."""
    store1 = ToolMemoryStore(experiment_id="exp_det_1")
    store2 = ToolMemoryStore(experiment_id="exp_det_1")

    # Add entries in order A, B
    store1.save_playbook("linear_api", "SCHEMA_QUIRK", "trigger_a", "rule_a", confidence=0.9)
    store1.save_playbook("slack_api", "WORKFLOW_DEPENDENCY", "trigger_b", "rule_b", confidence=0.8)

    # Add entries in opposite order B, A
    store2.save_playbook("slack_api", "WORKFLOW_DEPENDENCY", "trigger_b", "rule_b", confidence=0.8)
    store2.save_playbook("linear_api", "SCHEMA_QUIRK", "trigger_a", "rule_a", confidence=0.9)

    # Both must produce identical canonical JSON strings regardless of insertion sequence
    json1 = store1.to_canonical_json()
    json2 = store2.to_canonical_json()

    # Normalize IDs for comparison since uuid4 generates random IDs
    import json
    parsed1 = json.loads(json1)
    parsed2 = json.loads(json2)
    for p in parsed1:
        del p["id"]
        del p["created_at"]
        del p["updated_at"]
    for p in parsed2:
        del p["id"]
        del p["created_at"]
        del p["updated_at"]

    assert parsed1 == parsed2

    # File persistence round-trip
    file_path = tmp_path / "playbooks.json"
    store1.save_to_file(file_path)
    assert file_path.exists()

    loaded_store = ToolMemoryStore(experiment_id="exp_det_1")
    loaded_store.load_from_file(file_path)
    assert len(loaded_store.get_entries()) == 2
    assert loaded_store.retrieve_playbooks(tool_names=["linear_api"])[0].learned_rule == "rule_a"

