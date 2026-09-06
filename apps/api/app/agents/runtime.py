import time
import json
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
from app.memory.tool_memory import ToolMemoryStore
from app.agents.reflection import ToolReflectionEngine


class AgentRuntime:
    def __init__(
        self,
        spec: AgentSpec,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
        recorder: EventRecorder | None = None,
        memory_store: ToolMemoryStore | None = None,
    ):
        self.spec = spec
        self.provider = provider
        self.registry = tool_registry or default_registry
        self.recorder = recorder
        self.verifier = AgentVerifier(spec.verifier)
        self.memory_store = memory_store

    async def _emit_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        generation_id: str | None = None,
        execution_id: str | None = None,
    ):
        if self.recorder:
            await self.recorder.emit(event_type, payload, generation_id, execution_id)

    def _extract_embedded_tool_calls(self, content: str) -> list[Any]:
        import re, json
        from app.providers.base import ToolCallItem
        items = []
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        for b in blocks:
            try:
                data = json.loads(b)
                if "tool" in data and data["tool"] in self.spec.tools:
                    items.append(ToolCallItem(id=f"call_{int(time.time()*1000)}", name=data["tool"], arguments=data.get("arguments", {})))
                elif "action" in data:
                    for t in self.spec.tools:
                        tool_obj = self.registry.get(t)
                        if tool_obj and "enum" in tool_obj.input_schema.get("properties", {}).get("action", {}):
                            if data["action"] in tool_obj.input_schema["properties"]["action"]["enum"]:
                                items.append(ToolCallItem(id=f"call_{int(time.time()*1000)}", name=t, arguments=data))
                                break
            except Exception:
                pass
        react_matches = re.findall(r"Action:\s*(\w+)\s*\nAction Input:\s*(\{.*?\})", content, re.DOTALL)
        for tname, arg_str in react_matches:
            if tname in self.spec.tools:
                try:
                    args = json.loads(arg_str)
                    items.append(ToolCallItem(id=f"call_{int(time.time()*1000)}", name=tname, arguments=args))
                except Exception:
                    pass
        return items

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

        if self.memory_store:
            playbook_text = self.memory_store.format_for_prompt(self.spec.tools)
            if playbook_text:
                system_instruction += f"\n\n{playbook_text}"

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
                    "provider": getattr(llm_response, "provider", "llm"),
                    "model": getattr(llm_response, "model", self.spec.model),
                    "finish_reason": getattr(llm_response, "finish_reason", "stop"),
                    "content_preview": (llm_response.content or "")[:300],
                    "tool_calls_count": len(llm_response.tool_calls),
                    "tokens": llm_response.total_tokens,
                    "latency_ms": llm_response.latency_ms,
                },
                generation_id,
                execution_id,
            )

            # Check if model produced tool calls (native or embedded)
            effective_tool_calls = list(llm_response.tool_calls)
            if not effective_tool_calls and llm_response.content:
                effective_tool_calls = self._extract_embedded_tool_calls(llm_response.content)

            if effective_tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": llm_response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments),
                            },
                        }
                        for tc in effective_tool_calls
                    ],
                }
                state.messages.append(assistant_msg)

                # Execute each tool call
                for tc in effective_tool_calls:
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

        # Autonomous Self-Reflection & Tool Memory Learning Loop
        if self.memory_store:
            await self._emit_event(
                EventType.SELF_REFLECTION_STARTED,
                {"tools": self.spec.tools, "tool_results_count": len(state.tool_results)},
                generation_id,
                execution_id,
            )
            reflection_report = ToolReflectionEngine.reflect_on_execution(
                state=state,
                memory_store=self.memory_store,
                model_name=self.spec.model,
            )
            for entry in reflection_report.entries:
                await self._emit_event(
                    EventType.TOOL_PLAYBOOK_LEARNED,
                    entry.model_dump(),
                    generation_id,
                    execution_id,
                )
            await self._emit_event(
                EventType.SELF_REFLECTION_COMPLETED,
                {
                    "discovered_rules_count": reflection_report.discovered_rules_count,
                    "summary": reflection_report.summary,
                },
                generation_id,
                execution_id,
            )

        state.latency_ms = (time.perf_counter() - start_runtime) * 1000.0
        return state
