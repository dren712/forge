import json
import re
from typing import Any
from app.core.errors import ProviderInvalidResponseError, ForgeError
from app.providers.base import LLMProvider
from app.schemas.agent_spec import AgentSpec


ARCHITECT_SYSTEM_PROMPT = """You are the FORGE Chief Agent Architect.
Your role is to design the optimal declarative AgentSpec for an autonomous AI agent to accomplish a specific goal under benchmark evaluation.

You must output a single valid JSON object matching the AgentSpec schema:
{
  "model": "glm-4-7-flash",
  "system_prompt": "Clear instructions for the agent's behavior",
  "planner": {
    "type": "none" | "structured_plan" | "re_act" | "hierarchical",
    "max_subgoals": 5,
    "require_replan_on_error": false
  },
  "tools": ["repository", "file_editor", "shell", "test_runner", "search"],
  "memory": {
    "type": "working_context" | "stateless" | "scratchpad_summarized",
    "max_history_items": 30
  },
  "verifier": {
    "type": "none" | "self_check" | "mandatory_tests" | "strict_test_gate",
    "require_zero_failed_tests": true,
    "enforce_before_complete": true
  },
  "retry_policy": {
    "max_attempts": 3,
    "retry_on_tool_failure": true,
    "backoff_seconds": 1.0
  },
  "orchestration": {
    "type": "direct" | "plan_execute_verify" | "iterative_feedback"
  }
}

Do NOT generate application code. Output ONLY the valid JSON object.
"""


class AgentArchitect:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def _repair_json(self, raw_text: str) -> dict[str, Any]:
        """Attempts to extract and repair JSON from markdown blocks or surrounding text."""
        # Check for json code fence
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        candidate = match.group(1) if match else raw_text

        # Try to find the outermost curly braces
        first_brace = candidate.find("{")
        last_brace = candidate.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = candidate[first_brace:last_brace + 1]

        return json.loads(candidate)

    async def design_agent(
        self,
        goal: str,
        available_tools: list[str],
        benchmark_description: str,
        generation_number: int = 0,
    ) -> AgentSpec:
        """Designs a customized AgentSpec based on goal, tools, and benchmark."""
        prompt = (
            f"Goal: {goal}\n"
            f"Available Tools: {available_tools}\n"
            f"Benchmark Context: {benchmark_description}\n"
            f"Generation: {generation_number}\n\n"
        )
        if generation_number == 0:
            prompt += (
                "Design a baseline Generation 0 agent architecture. "
                "Keep the architecture simple, direct, and focused on basic repository interaction."
            )
        else:
            prompt += "Design an evolved agent architecture tailored to high reliability and precision."

        messages = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        for attempt in range(3):
            response = await self.provider.generate(
                messages=messages,
                temperature=0.2,
            )

            raw_content = response.content or "{}"
            try:
                data = self._repair_json(raw_content)
                # Filter tools to only those allowed
                if "tools" in data and isinstance(data["tools"], list):
                    data["tools"] = [t for t in data["tools"] if t in available_tools]
                else:
                    data["tools"] = available_tools

                # Validate with Pydantic
                spec = AgentSpec(**data)
                return spec
            except Exception as e:
                if attempt == 2:
                    raise ProviderInvalidResponseError(
                        f"Architect failed to produce a valid AgentSpec after 3 attempts. Last error: {e}. Raw: {raw_content[:200]}"
                    )
                messages.append({"role": "assistant", "content": raw_content})
                messages.append({
                    "role": "user",
                    "content": f"The response was not valid JSON matching the schema: {e}. Please output ONLY valid JSON.",
                })

        raise ForgeError("Unexpected failure in AgentArchitect")
