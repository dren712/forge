import pytest
import asyncio
from pathlib import Path
from pydantic import BaseModel

from app.schemas.agent_spec import AgentSpec, VerifierConfig, RetryPolicy, MemoryConfig
from app.schemas.execution import ExecutionResult
from app.agents.state import AgentState, VALID_TRANSITIONS
from app.agents.runtime import AgentRuntime
from app.agents.verifier import AgentVerifier, VerificationResult, VerificationCheck
from app.tools.base import Tool, ToolResult, sanitize_path
from app.tools.registry import ToolRegistry
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem
from app.core.config import settings
from app.memory.tool_memory import ToolMemoryStore


class MockScriptedProvider(LLMProvider):
    """Scripted LLM provider to test deterministic multi-step agent runtime behaviors."""
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.call_count = 0
        self.received_messages: list[list[dict]] = []

    async def generate(self, messages, tools=None, temperature=0.2):
        self.received_messages.append([dict(m) for m in messages])
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return LLMResponse(content="Done.", tool_calls=[])


def test_agent_state_lifecycle_transitions():
    state = AgentState(goal="Test State Transitions")
    assert state.status == "CREATED"

    # Valid transition
    state.transition_to("RUNNING")
    assert state.status == "RUNNING"

    state.transition_to("WAITING_FOR_TOOL")
    assert state.status == "WAITING_FOR_TOOL"

    state.transition_to("RECOVERING")
    assert state.status == "RECOVERING"

    state.transition_to("VERIFYING")
    assert state.status == "VERIFYING"

    state.transition_to("COMPLETED")
    assert state.status == "COMPLETED"

    # Terminal state cannot transition
    with pytest.raises(RuntimeError) as exc_info:
        state.transition_to("RUNNING")
    assert "Invalid state transition" in str(exc_info.value)


def test_execution_result_conversion():
    state = AgentState(
        goal="Deploy Hotfix",
        status="COMPLETED",
        final_output="Deployment successful.",
        model_call_count=3,
        input_tokens=150,
        output_tokens=50,
        total_tokens=200,
        latency_ms=123.4,
    )
    res = state.to_execution_result()
    assert isinstance(res, ExecutionResult)
    assert res.status == "COMPLETED"
    assert res.final_output == "Deployment successful."
    assert res.model_calls == 3
    assert res.usage["total_tokens"] == 200


def test_sanitize_path_security_boundary(tmp_path: Path):
    workspace = tmp_path / "sandbox"
    workspace.mkdir()

    # Valid in-sandbox path
    valid_file = sanitize_path(workspace, "app/main.py")
    assert valid_file == (workspace / "app/main.py").resolve()

    # Directory traversal escapes
    with pytest.raises(PermissionError):
        sanitize_path(workspace, "../../etc/passwd")

    with pytest.raises(PermissionError):
        sanitize_path(workspace, "/etc/passwd")


@pytest.mark.asyncio
async def test_runtime_pre_execution_tool_validation(tmp_path: Path):
    """Tests that invalid tool calls produce structured ToolResult observations without crashing."""
    # Scripted model calls non-existent tool, then invalid args, then completes
    provider = MockScriptedProvider([
        LLMResponse(
            content="Calling unknown tool",
            tool_calls=[ToolCallItem(id="c1", name="non_existent_tool", arguments={})],
        ),
        LLMResponse(
            content="Calling crm_api with invalid arguments",
            tool_calls=[ToolCallItem(id="c2", name="crm_api", arguments={"action": 12345})],
        ),
        LLMResponse(
            content="Done with investigation.",
            tool_calls=[],
        ),
    ])

    spec = AgentSpec(
        tools=["crm_api"],
        verifier=VerifierConfig(type="none"),
    )
    runtime = AgentRuntime(spec=spec, provider=provider)
    state = await runtime.run("Investigate issue", tmp_path)

    assert state.status == "COMPLETED"
    assert state.tool_call_count == 2
    # Verify both tool errors were recorded as structured observations
    assert len(state.tool_results) == 2
    assert state.tool_results[0]["error_type"] == "TOOL_NOT_FOUND"
    assert state.tool_results[0]["status_code"] == 404
    assert state.tool_results[1]["error_type"] == "INVALID_TOOL_ARGUMENTS"
    assert state.tool_results[1]["status_code"] == 400


@pytest.mark.asyncio
async def test_runtime_recovery_after_tool_failure(tmp_path: Path):
    """Tests that an agent receives structured observation and self-corrects on next step."""
    provider = MockScriptedProvider([
        # Step 1: Model calls linear_api with invalid team_id slug 'CORE'
        LLMResponse(
            content="Creating ticket",
            tool_calls=[
                ToolCallItem(
                    id="call_1",
                    name="linear_api",
                    arguments={"action": "create_issue", "team_id": "CORE", "title": "DB bug", "priority": 1},
                )
            ],
        ),
        # Step 2: Model recovers using valid UUID and completes
        LLMResponse(
            content="Correcting team_id with UUID",
            tool_calls=[
                ToolCallItem(
                    id="call_2",
                    name="linear_api",
                    arguments={
                        "action": "create_issue",
                        "team_id": "550e8400-e29b-41d4-a716-446655440001",
                        "title": "DB bug",
                        "priority": 1,
                    },
                )
            ],
        ),
        # Step 3: Conclude
        LLMResponse(content="Issue created successfully.", tool_calls=[]),
    ])

    spec = AgentSpec(
        tools=["linear_api"],
        verifier=VerifierConfig(type="none"),
    )
    runtime = AgentRuntime(spec=spec, provider=provider)
    state = await runtime.run("Create Linear Issue", tmp_path)

    assert state.status == "COMPLETED"
    assert state.tool_call_count == 2
    # First call failed with 422
    assert state.tool_results[0]["success"] is False
    assert state.tool_results[0]["status_code"] == 422
    assert state.tool_results[0]["error_type"] == "invalid_team_uuid"
    # Second call succeeded with 201
    assert state.tool_results[1]["success"] is True
    assert state.tool_results[1]["status_code"] == 201


@pytest.mark.asyncio
async def test_runtime_verifier_gating_blocks_premature_declaration(tmp_path: Path):
    """Tests that agent cannot bypass verifier by simply declaring task is complete."""
    # Model declares completion without running tests under mandatory_tests verifier
    provider = MockScriptedProvider([
        LLMResponse(content="I have implemented the feature and everything works!", tool_calls=[]),
        LLMResponse(content="I really am finished!", tool_calls=[]),
    ])

    spec = AgentSpec(
        tools=["test_runner"],
        verifier=VerifierConfig(type="mandatory_tests"),
    )
    runtime = AgentRuntime(spec=spec, provider=provider)
    state = await runtime.run("Fix repository bug", tmp_path)

    # Verification rejected completion because test_runner was never executed
    assert state.verification_passed is False
    assert "Verification Failed: You have not executed the test runner" in state.verification_feedback
    # Agent received verifier notice in conversation
    verifier_messages = [m for m in state.messages if "[VERIFIER NOTICE]" in m.get("content", "")]
    assert len(verifier_messages) >= 1


@pytest.mark.asyncio
async def test_runtime_enforces_max_steps(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "max_agent_steps", 3)
    provider = MockScriptedProvider([
        LLMResponse(content="Step 1", tool_calls=[ToolCallItem(id="c1", name="crm_api", arguments={"action": "list_customers"})]),
        LLMResponse(content="Step 2", tool_calls=[ToolCallItem(id="c2", name="crm_api", arguments={"action": "list_customers"})]),
        LLMResponse(content="Step 3", tool_calls=[ToolCallItem(id="c3", name="crm_api", arguments={"action": "list_customers"})]),
        LLMResponse(content="Step 4", tool_calls=[ToolCallItem(id="c4", name="crm_api", arguments={"action": "list_customers"})]),
    ])

    spec = AgentSpec(tools=["crm_api"], verifier=VerifierConfig(type="none"))
    runtime = AgentRuntime(spec=spec, provider=provider)
    state = await runtime.run("Infinite steps task", tmp_path)

    assert state.status == "MAX_STEPS"
    assert state.current_step == 3


@pytest.mark.asyncio
async def test_runtime_memory_retrieval_and_prompt_injection(tmp_path: Path):
    """Proves: memory exists → execution retrieves it → final model context contains it,

    filtering out irrelevant memories, preserving provenance, and distinguishing from task goal.
    """
    store = ToolMemoryStore(experiment_id="exp_s5e_test")
    # Relevant playbook for linear_api
    store.save_playbook(
        tool_name="linear_api",
        category="SCHEMA_QUIRK",
        pattern_trigger="create_issue with team_id",
        learned_rule="Linear requires a 36-char team UUID, not slug.",
        evidence="Error 422: Linear requires a 36-character team UUID.",
        confidence=0.95,
    )
    # Irrelevant playbook for sentry_api (not in agent's active tools)
    store.save_playbook(
        tool_name="sentry_api",
        category="ERROR_RECOVERY",
        pattern_trigger="resolve_incident with resolution_note",
        learned_rule="Sentry resolution note must be at least 15 characters.",
        evidence="HTTP 422: 'resolution_note' must be detailed (min 15 characters).",
        confidence=0.90,
    )

    provider = MockScriptedProvider([
        LLMResponse(content="Issue created using valid UUID.", tool_calls=[]),
    ])

    spec = AgentSpec(
        tools=["linear_api"],
        verifier=VerifierConfig(type="none"),
    )
    runtime = AgentRuntime(spec=spec, provider=provider, memory_store=store)
    state = await runtime.run(goal="Create incident issue in Linear", workspace=tmp_path)

    # 1. Execution retrieves memory and passes it directly to model input
    assert len(provider.received_messages) >= 1
    model_input = provider.received_messages[0]
    assert len(model_input) >= 2

    system_msg = model_input[0]["content"]
    user_msg = model_input[1]["content"]

    # 2. Retrieved memory is actually included in model context
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" in system_msg
    assert "LINEAR_API" in system_msg
    assert "Linear requires a 36-char team UUID, not slug." in system_msg
    # Provenance / evidence reference preserved
    assert "Learned from: Error 422: Linear requires a 36-character team UUID." in system_msg
    assert "Confidence: 95%" in system_msg

    # 3. Irrelevant memory is NOT injected
    assert "SENTRY_API" not in system_msg
    assert "resolve_incident" not in system_msg

    # 4. Memory injection is cleanly distinguishable from original task
    assert model_input[0]["role"] == "system"
    assert model_input[1]["role"] == "user"
    assert user_msg == "Task Goal:\nCreate incident issue in Linear"
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" not in user_msg

    # 5. Runtime state records memory context
    assert len(state.memory_context) == 1
    assert "LINEAR_API" in state.memory_context[0]


@pytest.mark.asyncio
async def test_runtime_no_memory_injection_when_absent_or_stateless(tmp_path: Path):
    """Proves: memory absent or stateless → no learned playbook injected into model context."""
    # Case A: memory_store is None
    provider_none = MockScriptedProvider([
        LLMResponse(content="Done without memory.", tool_calls=[]),
    ])
    spec_none = AgentSpec(tools=["linear_api"], verifier=VerifierConfig(type="none"))
    runtime_none = AgentRuntime(spec=spec_none, provider=provider_none, memory_store=None)
    state_none = await runtime_none.run(goal="Fix bug without memory store", workspace=tmp_path)

    model_input_none = provider_none.received_messages[0]
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" not in model_input_none[0]["content"]
    assert state_none.memory_context == []

    # Case B: memory store exists, but spec specifies stateless memory
    store = ToolMemoryStore(experiment_id="exp_stateless_test")
    store.save_playbook(
        tool_name="linear_api",
        category="SCHEMA_QUIRK",
        pattern_trigger="create_issue",
        learned_rule="Linear requires UUID",
        confidence=0.9,
    )
    provider_stateless = MockScriptedProvider([
        LLMResponse(content="Done stateless.", tool_calls=[]),
    ])
    spec_stateless = AgentSpec(
        tools=["linear_api"],
        memory=MemoryConfig(type="stateless"),
        verifier=VerifierConfig(type="none"),
    )
    runtime_stateless = AgentRuntime(spec=spec_stateless, provider=provider_stateless, memory_store=store)
    state_stateless = await runtime_stateless.run(goal="Fix bug in stateless mode", workspace=tmp_path)

    model_input_stateless = provider_stateless.received_messages[0]
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" not in model_input_stateless[0]["content"]
    assert state_stateless.memory_context == []

    # Case C: memory store has entries, but NONE match the agent's active tools
    provider_unmatched = MockScriptedProvider([
        LLMResponse(content="Done unmatched.", tool_calls=[]),
    ])
    spec_unmatched = AgentSpec(tools=["github_api"], verifier=VerifierConfig(type="none"))
    runtime_unmatched = AgentRuntime(spec=spec_unmatched, provider=provider_unmatched, memory_store=store)
    state_unmatched = await runtime_unmatched.run(goal="Fix bug with other tools", workspace=tmp_path)

    model_input_unmatched = provider_unmatched.received_messages[0]
    assert "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]" not in model_input_unmatched[0]["content"]
    assert state_unmatched.memory_context == []

