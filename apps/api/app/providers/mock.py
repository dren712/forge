import json
from typing import Any
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem


class DeterministicMockProvider(LLMProvider):
    """
    Simulates intelligent agent generations and tool usage deterministically.
    Baseline mode: skips running tests or makes premature completion claims.
    Evolved mode: fixes the code, runs tests, verifies passing, and succeeds.
    """

    def __init__(self, mode: str = "baseline"):
        self.mode = mode
        self.call_count = 0

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.call_count += 1
        last_msg = messages[-1]["content"] if messages else ""
        system_msg = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""

        # Architect request detection (producing AgentSpec)
        if "generate an AgentSpec" in last_msg or "Architect" in system_msg or "agent_spec" in str(response_format):
            is_evolved = (self.mode == "evolved")
            spec_json = {
                "model": "glm-4-7-flash",
                "system_prompt": "You are an expert autonomous software engineer. Diagnose bugs, fix code, and verify with tests.",
                "planner": {"type": "structured_plan" if is_evolved else "none"},
                "tools": ["repository", "file_editor", "shell", "test_runner", "search"],
                "memory": {"type": "working_context"},
                "verifier": {"type": "mandatory_tests" if is_evolved else "none"},
                "retry_policy": {"max_attempts": 3, "retry_on_tool_failure": True},
                "orchestration": {"type": "plan_execute_verify" if is_evolved else "direct"}
            }
            return LLMResponse(
                content=json.dumps(spec_json),
                tool_calls=[],
                input_tokens=180,
                output_tokens=140,
                total_tokens=320,
                latency_ms=120.0,
            )

        # Failure analysis request detection
        if "Failure Analyzer" in system_msg or "analyze failure" in last_msg.lower():
            analysis = {
                "failure_type": "VERIFICATION_FAILURE",
                "severity": "HIGH",
                "evidence": ["Tests were not run before declaring completion", "Exit claimed with unverified assertions"],
                "root_cause": "The agent lacks a mandatory verification gate before declaring task completion.",
                "recommended_mutation": {
                    "mutation_type": "VERIFIER_UPDATE",
                    "target": "verifier",
                    "change": "Enforce automated test execution before completing the task."
                },
                "confidence": 0.96
            }
            return LLMResponse(
                content=json.dumps(analysis),
                input_tokens=350,
                output_tokens=160,
                total_tokens=510,
                latency_ms=150.0,
            )

        # Mutation generation request detection
        if "Mutation Generator" in system_msg or "propose mutation" in last_msg.lower():
            mutation = {
                "mutation_type": "VERIFIER_UPDATE",
                "target": "verifier",
                "before": {"type": "none"},
                "after": {"type": "mandatory_tests"},
                "reason": "Observed verification failures where agent declared completion prematurely.",
                "observed_failure": "VERIFICATION_FAILURE",
                "expected_effect": "Increase accuracy and reliability by enforcing test verification."
            }
            return LLMResponse(
                content=json.dumps(mutation),
                input_tokens=220,
                output_tokens=120,
                total_tokens=340,
                latency_ms=110.0,
            )

        # AGENT EXECUTION FLOW
        if self.mode == "baseline":
            # Baseline: Inspects then exits prematurely without fixing or verifying
            if "Tool Result" in last_msg:
                return LLMResponse(
                    content="I have reviewed the code and concluded the fix is ready.",
                    tool_calls=[],
                    input_tokens=300,
                    output_tokens=40,
                    total_tokens=340,
                    latency_ms=95.0,
                )
            else:
                return LLMResponse(
                    content="Inspecting repository files.",
                    tool_calls=[ToolCallItem(id="call_repo_base", name="repository", arguments={"action": "list_files", "path": "."})],
                    input_tokens=200,
                    output_tokens=30,
                    total_tokens=230,
                    latency_ms=80.0,
                )

        else:
            # Evolved mode:
            # Step 1: list files -> Step 2: edit fix -> Step 3: run test_runner -> Step 4: complete!
            if "Tool Result (test_runner)" in last_msg:
                return LLMResponse(
                    content="All unit tests passed and verification is confirmed. The bug fix is complete.",
                    tool_calls=[],
                    input_tokens=450,
                    output_tokens=35,
                    total_tokens=485,
                    latency_ms=110.0,
                )
            elif "Tool Result (file_editor)" in last_msg:
                return LLMResponse(
                    content="Fix applied to pagination.py. Now executing tests to verify correctness.",
                    tool_calls=[ToolCallItem(id="call_test_ev", name="test_runner", arguments={"test_path": "tests"})],
                    input_tokens=400,
                    output_tokens=35,
                    total_tokens=435,
                    latency_ms=105.0,
                )
            elif "Tool Result (repository)" in last_msg:
                fix_code = (
                    "def paginate(items, page=1, page_size=10):\n"
                    "    if not items:\n"
                    "        return []\n"
                    "    start = (page - 1) * page_size\n"
                    "    if start >= len(items):\n"
                    "        return []\n"
                    "    end = start + page_size\n"
                    "    return items[start:end]\n"
                )
                return LLMResponse(
                    content="I have identified the off-by-one boundary bug. Applying fix in src/pagination.py.",
                    tool_calls=[ToolCallItem(
                        id="call_edit_ev",
                        name="file_editor",
                        arguments={"action": "replace", "path": "src/pagination.py", "content": fix_code},
                    )],
                    input_tokens=350,
                    output_tokens=60,
                    total_tokens=410,
                    latency_ms=115.0,
                )
            else:
                return LLMResponse(
                    content="Locating files in the repository to identify the defect.",
                    tool_calls=[ToolCallItem(id="call_repo_ev", name="repository", arguments={"action": "list_files", "path": "."})],
                    input_tokens=220,
                    output_tokens=30,
                    total_tokens=250,
                    latency_ms=85.0,
                )
