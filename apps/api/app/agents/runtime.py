import time
import json
import asyncio
from pathlib import Path
from typing import Any
from app.core.config import settings
from app.schemas.agent_spec import AgentSpec
from app.schemas.execution import ExecutionResult
from app.agents.state import AgentState
from app.agents.verifier import AgentVerifier, VerificationResult
from app.tools.base import Tool, ToolResult, sanitize_path
from app.tools.registry import ToolRegistry, default_registry
from app.providers.base import LLMProvider, ToolCallItem
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

    def _validate_tool_call(
        self, tool: Tool | None, tool_name: str, args: Any, workspace: Path
    ) -> tuple[bool, ToolResult | None]:
        """
        Validates tool existence, argument parsing, schema compliance, and security constraints.
        Returns (is_valid, error_result_or_none).
        """
        start_t = time.perf_counter()

        if tool is None:
            return False, ToolResult(
                success=False,
                output=f"Error 404 Not Found: Tool '{tool_name}' is not recognized or permitted.",
                error=f"Tool '{tool_name}' not found in registry.",
                error_type="TOOL_NOT_FOUND",
                status_code=404,
                latency_ms=(time.perf_counter() - start_t) * 1000.0,
            )

        if not isinstance(args, dict):
            return False, ToolResult(
                success=False,
                output=f"Error 400 Bad Request: Arguments for tool '{tool_name}' must be a JSON object (dict), received: {type(args).__name__}",
                error=f"Invalid arguments type: {type(args).__name__}",
                error_type="INVALID_TOOL_ARGUMENTS",
                status_code=400,
                latency_ms=(time.perf_counter() - start_t) * 1000.0,
            )

        schema = tool.input_schema or {}
        required = schema.get("required", [])
        for req in required:
            if req not in args or args[req] is None:
                return False, ToolResult(
                    success=False,
                    output=f"Error 400 Bad Request: Missing required parameter '{req}' for tool '{tool_name}'.",
                    error=f"Missing required parameter '{req}'",
                    error_type="INVALID_TOOL_ARGUMENTS",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_t) * 1000.0,
                )

        properties = schema.get("properties", {})
        for prop_name, prop_spec in properties.items():
            if prop_name in args and args[prop_name] is not None:
                val = args[prop_name]
                expected_type = prop_spec.get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be a string, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be a string",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )
                elif expected_type == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be an integer, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be an integer",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )
                elif expected_type == "number" and (not isinstance(val, (int, float)) or isinstance(val, bool)):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be a number, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be a number",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )
                elif expected_type == "boolean" and not isinstance(val, bool):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be a boolean, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be a boolean",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )
                elif expected_type == "array" and not isinstance(val, list):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be a list, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be a list",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )
                elif expected_type == "object" and not isinstance(val, dict):
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Parameter '{prop_name}' must be a dict, received {type(val).__name__}.",
                        error=f"Parameter '{prop_name}' must be a dict",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )

                if "enum" in prop_spec and val not in prop_spec["enum"]:
                    return False, ToolResult(
                        success=False,
                        output=f"Error 400 Bad Request: Invalid value '{val}' for parameter '{prop_name}'. Allowed: {prop_spec['enum']}",
                        error=f"Invalid value for '{prop_name}'",
                        error_type="INVALID_TOOL_ARGUMENTS",
                        status_code=400,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )

        # Path traversal security check for filesystem arguments
        for k in ("path", "file_path", "filepath", "target_path", "rel_path"):
            if k in args and isinstance(args[k], str):
                try:
                    sanitize_path(workspace, args[k])
                except PermissionError as pe:
                    return False, ToolResult(
                        success=False,
                        output=f"Error 403 Forbidden: Security violation - {str(pe)}",
                        error=str(pe),
                        error_type="SECURITY_VIOLATION",
                        status_code=403,
                        latency_ms=(time.perf_counter() - start_t) * 1000.0,
                    )

        return True, None

    def _extract_embedded_tool_calls(self, content: str) -> list[Any]:
        import re, json
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
        """Executes the agent loop inside the target workspace with canonical lifecycle management."""
        state = AgentState(goal=goal)
        state.transition_to("RUNNING")

        # Initialize conversation messages and planner guidance
        system_instruction = (
            f"{self.spec.system_prompt}\n\n"
            f"Available tools: {', '.join(self.spec.tools)}.\n"
            f"Planner Mode: {self.spec.planner.type}.\n"
            f"Verifier Mode: {self.spec.verifier.type}."
        )

        if self.spec.planner.type == "structured_plan":
            system_instruction += "\nPLANNER INSTRUCTION: Outline your plan with numbered subgoals before taking actions."
        elif self.spec.planner.type == "re_act":
            system_instruction += "\nPLANNER INSTRUCTION: Reason step-by-step using the Thought -> Action -> Observation cycle."
        elif self.spec.planner.type == "hierarchical":
            system_instruction += "\nPLANNER INSTRUCTION: Break goals into subgoals, execute with tools, and synthesize results."

        if self.memory_store:
            playbook_text = self.memory_store.format_for_prompt(self.spec.tools)
            if playbook_text:
                system_instruction += f"\n\n{playbook_text}"
                state.memory_context.append(playbook_text)

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

        while state.current_step < max_steps and state.status in ("RUNNING", "WAITING_FOR_TOOL", "RECOVERING"):
            state.current_step += 1

            # Check total execution runtime limit
            elapsed = time.perf_counter() - start_runtime
            if elapsed > settings.max_agent_runtime_seconds:
                state.transition_to("TIMEOUT")
                state.errors.append(f"Execution exceeded max runtime limit of {settings.max_agent_runtime_seconds}s")
                break

            if state.tool_call_count >= max_tool_calls:
                state.transition_to("MAX_STEPS")
                state.errors.append(f"Exceeded maximum allowed tool calls ({max_tool_calls})")
                break

            # Model Call
            await self._emit_event(
                EventType.MODEL_CALL,
                {"step": state.current_step, "messages_count": len(state.messages)},
                generation_id,
                execution_id,
            )

            # Model generation with bounded retries for transient errors
            llm_response = None
            max_model_retries = max(1, settings.max_model_retries)
            for m_attempt in range(max_model_retries):
                try:
                    llm_response = await self.provider.generate(
                        messages=state.messages,
                        tools=tool_definitions if tool_definitions else None,
                        temperature=0.2,
                    )
                    break
                except Exception as e:
                    if m_attempt == max_model_retries - 1:
                        state.errors.append(f"Model generation error at step {state.current_step}: {str(e)}")
                        await self._emit_event(
                            EventType.AGENT_ERROR,
                            {"error": str(e), "step": state.current_step},
                            generation_id,
                            execution_id,
                        )
                        state.transition_to("FAILED")
                        break
                    await asyncio.sleep(0.5 * (m_attempt + 1))

            if llm_response is None:
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
                state.transition_to("WAITING_FOR_TOOL")
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

                has_failure_in_turn = False

                # Execute each tool call sequentially
                for tc in effective_tool_calls:
                    state.tool_call_count += 1
                    tool = self.registry.get(tc.name)

                    # Parse arguments if string
                    tc_args = tc.arguments
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except Exception as pe:
                            pass

                    await self._emit_event(
                        EventType.TOOL_CALL,
                        {"tool": tc.name, "arguments": tc_args, "call_id": tc.id},
                        generation_id,
                        execution_id,
                    )

                    # Pre-execution tool validation
                    is_valid, validation_error = self._validate_tool_call(tool, tc.name, tc_args, workspace)
                    if not is_valid and validation_error is not None:
                        tool_result = validation_error
                        has_failure_in_turn = True
                        state.errors.append(tool_result.error or tool_result.output)
                    else:
                        # Execute with retry policy for transient exceptions
                        attempts = 0
                        max_attempts = self.spec.retry_policy.max_attempts if self.spec.retry_policy.retry_on_tool_failure else 1
                        tool_result = None

                        while attempts < max_attempts:
                            attempts += 1
                            try:
                                tool_result = await tool.execute(tc_args, workspace)
                                if tool_result.success or not self.spec.retry_policy.retry_on_tool_failure:
                                    break
                            except Exception as te:
                                if attempts >= max_attempts:
                                    tool_result = ToolResult(
                                        success=False,
                                        output=f"Tool execution exception after {attempts} attempts: {te}",
                                        error=str(te),
                                        error_type="TOOL_EXECUTION_EXCEPTION",
                                        status_code=500,
                                    )
                                    state.errors.append(f"Tool execution exception: {te}")
                                    has_failure_in_turn = True
                                    break
                                await asyncio.sleep(self.spec.retry_policy.backoff_seconds)

                        if tool_result is None:
                            tool_result = ToolResult(
                                success=False,
                                output=f"Tool execution failed after {attempts} attempts.",
                                error="Max attempts exceeded",
                                error_type="MAX_RETRIES_EXCEEDED",
                                status_code=500,
                            )
                            has_failure_in_turn = True

                        if not tool_result.success:
                            has_failure_in_turn = True
                            if tool_result.error:
                                state.errors.append(tool_result.error)

                    tool_output = tool_result.output if tool_result.success else (
                        tool_result.output or f"Error: {tool_result.error}"
                    )
                    success = tool_result.success

                    # Record structured tool result and observation
                    result_record = {
                        "tool": tc.name,
                        "success": success,
                        "arguments": tc_args,
                        "output": tool_output[:2000],
                        "error_type": tool_result.error_type,
                        "status_code": tool_result.status_code,
                        "metadata": tool_result.metadata,
                    }
                    state.tool_results.append(result_record)
                    state.observations.append({
                        "step": state.current_step,
                        "type": "tool_result",
                        "tool": tc.name,
                        "success": success,
                        "output": tool_output[:2000],
                        "error_type": tool_result.error_type,
                        "status_code": tool_result.status_code,
                    })

                    await self._emit_event(
                        EventType.TOOL_RESULT,
                        {
                            "tool": tc.name,
                            "success": success,
                            "status_code": tool_result.status_code,
                            "error_type": tool_result.error_type,
                            "output_preview": tool_output[:300],
                        },
                        generation_id,
                        execution_id,
                    )

                    state.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": f"Tool Result ({tc.name}):\n{tool_output}",
                    })

                # State transition post tool execution
                if has_failure_in_turn:
                    state.transition_to("RECOVERING")
                else:
                    state.transition_to("RUNNING")

            else:
                # No tool calls: Agent produced terminal text or declared completion
                state.final_output = llm_response.content
                state.messages.append({"role": "assistant", "content": llm_response.content or ""})

                # RUN VERIFIER GATE
                state.transition_to("VERIFYING")
                await self._emit_event(
                    EventType.VERIFICATION_STARTED,
                    {"verifier_type": self.spec.verifier.type},
                    generation_id,
                    execution_id,
                )

                verification_result = await self.verifier.verify(state, workspace)
                state.verification_result = verification_result
                state.verification_passed = verification_result.passed
                feedback = verification_result.failure_reason or (
                    verification_result.checks[0].evidence if verification_result.checks else "Verification passed."
                )
                state.verification_feedback = feedback

                await self._emit_event(
                    EventType.VERIFICATION_RESULT,
                    {
                        "passed": verification_result.passed,
                        "feedback": feedback,
                        "checks": [c.model_dump() for c in verification_result.checks],
                    },
                    generation_id,
                    execution_id,
                )

                if verification_result.passed:
                    state.transition_to("COMPLETED")
                    break
                else:
                    # Verification failed: inject feedback into conversation so agent can recover
                    state.transition_to("RECOVERING")
                    state.errors.append(f"Verification rejected completion: {feedback}")
                    state.observations.append({
                        "step": state.current_step,
                        "type": "verification_rejection",
                        "feedback": feedback,
                    })
                    state.messages.append({
                        "role": "user",
                        "content": (
                            f"[VERIFIER NOTICE]: Your attempt to conclude the task was REJECTED.\n"
                            f"Reason: {feedback}\n"
                            "Please address this requirement immediately."
                        ),
                    })

        if state.status in ("RUNNING", "WAITING_FOR_TOOL", "RECOVERING"):
            state.transition_to("MAX_STEPS")

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
