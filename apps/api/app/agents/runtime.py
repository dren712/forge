import time
import asyncio
from pathlib import Path
from typing import Any
from app.core.config import settings
from app.schemas.agent_spec import AgentSpec
from app.agents.state import AgentState
from app.agents.verifier import AgentVerifier
from app.tools.registry import ToolRegistry, default_registry
from app.providers.base import LLMProvider
from app.tracing.recorder import EventRecorder
from app.tracing.events import EventType


class AgentRuntime:
    def __init__(
        self,
        spec: AgentSpec,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
        recorder: EventRecorder | None = None,
    ):
        self.spec = spec
        self.provider = provider
        self.registry = tool_registry or default_registry
        self.recorder = recorder
        self.verifier = AgentVerifier(spec.verifier)

    async def _emit_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        generation_id: str | None = None,
        execution_id: str | None = None,
    ):
        if self.recorder:
            await self.recorder.emit(event_type, payload, generation_id, execution_id)

    async def run(
        self,
        goal: str,
        workspace: Path,
        generation_id: str | None = None,
        execution_id: str | None = None,
    ) -> AgentState:
        """Executes the agent loop inside the target workspace."""
        state = AgentState(goal=goal)

        # Initialize conversation messages
        system_instruction = (
            f"{self.spec.system_prompt}\n\n"
            f"Available tools: {', '.join(self.spec.tools)}.\n"
            f"Planner Mode: {self.spec.planner.type}.\n"
            f"Verifier Mode: {self.spec.verifier.type}."
        )
        if self.spec.verifier.type in ("mandatory_tests", "strict_test_gate"):
            system_instruction += (
                "\nCRITICAL REQUIREMENT: You MUST run automated tests using the 'test_runner' tool "
                "and ensure all tests pass before declaring that your work is done. "
                "Do NOT declare completion until tests pass."
            )

        state.messages.append({"role": "system", "content": system_instruction})
        state.messages.append({"role": "user", "content": f"Task Goal:\n{goal}"})

        await self._emit_event(
            EventType.AGENT_STARTED,
            {"goal": goal, "agent_model": self.spec.model, "tools": self.spec.tools},
            generation_id,
            execution_id,
        )

        tool_definitions = self.registry.get_definitions_for(self.spec.tools)
        max_steps = settings.max_agent_steps
        max_tool_calls = settings.max_tool_calls
        start_runtime = time.perf_counter()

        while state.current_step < max_steps and state.status == "RUNNING":
            state.current_step += 1

            # Check total execution runtime limit
            elapsed = time.perf_counter() - start_runtime
            if elapsed > settings.max_agent_runtime_seconds:
                state.status = "TIMEOUT"
                state.errors.append(f"Execution exceeded max runtime limit of {settings.max_agent_runtime_seconds}s")
                break

            if state.tool_call_count >= max_tool_calls:
                state.status = "MAX_STEPS"
                state.errors.append(f"Exceeded maximum allowed tool calls ({max_tool_calls})")
                break

            # Model Call
            await self._emit_event(
                EventType.MODEL_CALL,
                {"step": state.current_step, "messages_count": len(state.messages)},
                generation_id,
                execution_id,
            )

            try:
                llm_response = await self.provider.generate(
                    messages=state.messages,
                    tools=tool_definitions if tool_definitions else None,
                    temperature=0.2,
                )
            except Exception as e:
                state.errors.append(f"Model generation error at step {state.current_step}: {str(e)}")
                await self._emit_event(
                    EventType.AGENT_ERROR,
                    {"error": str(e), "step": state.current_step},
                    generation_id,
                    execution_id,
                )
                break

            # Update token metrics
            state.model_call_count += 1
            state.input_tokens += llm_response.input_tokens
            state.output_tokens += llm_response.output_tokens
            state.total_tokens += llm_response.total_tokens

            await self._emit_event(
                EventType.MODEL_RESPONSE,
                {
                    "content_preview": (llm_response.content or "")[:300],
                    "tool_calls_count": len(llm_response.tool_calls),
                    "tokens": llm_response.total_tokens,
                    "latency_ms": llm_response.latency_ms,
                },
                generation_id,
                execution_id,
            )

            # Check if model produced tool calls
            if llm_response.tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": llm_response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in llm_response.tool_calls
                    ],
                }
                state.messages.append(assistant_msg)

                # Execute each tool call
                for tc in llm_response.tool_calls:
                    state.tool_call_count += 1
                    tool = self.registry.get(tc.name)

                    await self._emit_event(
                        EventType.TOOL_CALL,
                        {"tool": tc.name, "arguments": tc.arguments, "call_id": tc.id},
                        generation_id,
                        execution_id,
                    )

                    if not tool:
                        res_str = f"Error: Tool '{tc.name}' is not recognized or permitted."
                        state.errors.append(res_str)
                        state.messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": res_str,
                        })
                        continue

                    # Execute with retry policy
                    attempts = 0
                    max_attempts = self.spec.retry_policy.max_attempts if self.spec.retry_policy.retry_on_tool_failure else 1
                    tool_result = None

                    while attempts < max_attempts:
                        attempts += 1
                        try:
                            tool_result = await tool.execute(tc.arguments, workspace)
                            if tool_result.success or not self.spec.retry_policy.retry_on_tool_failure:
                                break
                        except Exception as te:
                            if attempts >= max_attempts:
                                tool_result = None
                                state.errors.append(f"Tool execution exception: {te}")
                                break
                            await asyncio.sleep(self.spec.retry_policy.backoff_seconds)

                    if tool_result is None:
                        tool_output = f"Tool execution failed after {attempts} attempts."
                        success = False
                        metadata = {}
                    else:
                        tool_output = tool_result.output if tool_result.success else f"Error: {tool_result.error}\n{tool_result.output}"
                        success = tool_result.success
                        metadata = tool_result.metadata

                    state.tool_results.append({
                        "tool": tc.name,
                        "success": success,
                        "arguments": tc.arguments,
                        "output": tool_output[:2000],
                        "metadata": metadata,
                    })

                    await self._emit_event(
                        EventType.TOOL_RESULT,
                        {"tool": tc.name, "success": success, "output_preview": tool_output[:300]},
                        generation_id,
                        execution_id,
                    )

                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": f"Tool Result ({tc.name}):\n{tool_output}",
                    })

            else:
                # No tool calls: Agent produced terminal text or declared completion
                state.final_output = llm_response.content
                state.messages.append({"role": "assistant", "content": llm_response.content or ""})

                # RUN VERIFIER
                await self._emit_event(
                    EventType.VERIFICATION_STARTED,
                    {"verifier_type": self.spec.verifier.type},
                    generation_id,
                    execution_id,
                )

                verified, feedback = await self.verifier.verify(state, workspace)
                state.verification_passed = verified
                state.verification_feedback = feedback

                await self._emit_event(
                    EventType.VERIFICATION_RESULT,
                    {"passed": verified, "feedback": feedback},
                    generation_id,
                    execution_id,
                )

                if verified:
                    state.status = "COMPLETED"
                    break
                else:
                    # Verification failed: inject feedback into conversation so agent can recover
                    state.errors.append(f"Verification rejected completion: {feedback}")
                    state.messages.append({
                        "role": "user",
                        "content": (
                            f"[VERIFIER NOTICE]: Your attempt to conclude the task was REJECTED.\n"
                            f"Reason: {feedback}\n"
                            "Please address this requirement immediately."
                        ),
                    })

        if state.status == "RUNNING":
            state.status = "MAX_STEPS"

        await self._emit_event(
            EventType.AGENT_COMPLETED,
            {
                "status": state.status,
                "steps": state.current_step,
                "tool_calls": state.tool_call_count,
                "verification_passed": state.verification_passed,
                "errors_count": len(state.errors),
            },
            generation_id,
            execution_id,
        )

        return state
