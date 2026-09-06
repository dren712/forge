import pytest
import asyncio
from pathlib import Path
from pydantic import BaseModel

from app.schemas.agent_spec import AgentSpec, VerifierConfig, RetryPolicy
from app.schemas.execution import ExecutionResult
from app.agents.state import AgentState, VALID_TRANSITIONS
from app.agents.runtime import AgentRuntime
from app.agents.verifier import AgentVerifier, VerificationResult, VerificationCheck
from app.tools.base import Tool, ToolResult, sanitize_path
from app.tools.registry import ToolRegistry
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem
from app.core.config import settings


class MockScriptedProvider(LLMProvider):
    """Scripted LLM provider to test deterministic multi-step agent runtime behaviors."""
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.call_count = 0

    async def generate(self, messages, tools=None, temperature=0.2):
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
