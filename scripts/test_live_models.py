import json
#!/usr/bin/env python3
"""
FORGE Live Model Experiment & Provider Verification Script
Tests TensorMux (glm-4-7-flash) and OpenAI AI Grants (gpt-5-nano) for:
1. Basic generation
2. Tool calling with normalized ToolCallItem
3. Multi-turn tool execution loop
4. Token accounting and latency measurement
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.core.config import settings
from app.providers.tensormux import TensorMuxProvider
from app.providers.aigrants import AIGrantsIndiaProvider
from app.tools.base import Tool, ToolResult


class SimpleReadFileTool(Tool):
    name = "read_file"
    description = "Reads the content of a local file in the project."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file"}
        },
        "required": ["path"],
    }

    async def execute(self, input_data: dict, workspace: Path) -> ToolResult:
        path = input_data.get("path", "")
        if "README" in path.upper():
            return ToolResult(
                success=True,
                output="# FORGE Hackathon Project\nAutonomous agent evolution engine.\nTagline: Agents don't just run. They evolve.",
            )
        return ToolResult(success=False, output="", error=f"File {path} not found")


async def test_provider_tool_calling(provider, name: str) -> dict:
    print(f"\n--- Testing Tool Calling & Multi-Turn with {name} ---")
    tool = SimpleReadFileTool()
    tool_defs = [{
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }]

    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant equipped with tools. When asked for file content, use the read_file tool.",
        },
        {
            "role": "user",
            "content": "Read the project README.md using the read_file tool and report its tagline.",
        },
    ]

    print(f"[Turn 1] Requesting model to call tool...")
    res1 = await provider.generate(messages, tools=tool_defs, temperature=0.0)
    print(f"  Content:      {res1.content!r}")
    print(f"  Tool Calls:   {len(res1.tool_calls)}")
    print(f"  Tokens:       in={res1.input_tokens}, out={res1.output_tokens}, total={res1.total_tokens}")
    print(f"  Latency:      {res1.latency_ms:.1f} ms")

    if not res1.tool_calls:
        print(f"  [NOTE] {name} did not emit a structured tool_call. Checking if tool call was in text...")
        return {
            "name": name,
            "tool_call_supported": False,
            "turns": 1,
            "tokens": res1.total_tokens,
            "latency_ms": res1.latency_ms,
            "text": res1.content,
        }

    tc = res1.tool_calls[0]
    print(f"  Normalized ToolCall: id={tc.id}, name={tc.name}, args={tc.arguments}")

    # Execute tool
    workspace = Path(".")
    tool_res = await tool.execute(tc.arguments, workspace)
    print(f"[Turn 2] Tool Execution Result: success={tool_res.success}, output={tool_res.output!r}")

    # Feed back to model for Turn 3
    messages.append({
        "role": "assistant",
        "content": res1.content,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
        ],
    })
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "name": tc.name,
        "content": tool_res.output,
    })

    print(f"[Turn 3] Sending tool output back to {name}...")
    res2 = await provider.generate(messages, tools=tool_defs, temperature=0.0)
    print(f"  Final Response: {res2.content!r}")
    print(f"  Tokens:       in={res2.input_tokens}, out={res2.output_tokens}, total={res2.total_tokens}")
    print(f"  Latency:      {res2.latency_ms:.1f} ms")

    total_tokens = res1.total_tokens + res2.total_tokens
    total_latency = res1.latency_ms + res2.latency_ms

    return {
        "name": name,
        "tool_call_supported": True,
        "tool_name": tc.name,
        "turns": 3,
        "total_tokens": total_tokens,
        "total_latency_ms": total_latency,
        "final_answer": res2.content,
    }


async def main():
    print("=" * 60)
    print("FORGE — Live Model Experiment (Section S2)")
    print("=" * 60)

    # 1. Test TensorMux
    tmx = TensorMuxProvider(
        api_key=settings.tensormux_api_key,
        base_url=settings.tensormux_base_url,
        model=settings.tensormux_model,
    )
    tmx_res = await test_provider_tool_calling(tmx, f"TensorMux ({settings.tensormux_model})")

    # 2. Test OpenAI / AI Grants
    ai_key = settings.aigrants_api_key
    ai_prov = AIGrantsIndiaProvider(
        api_key=ai_key,
        base_url=settings.aigrants_base_url,
        model=settings.aigrants_model,
    )
    ai_res = await test_provider_tool_calling(ai_prov, f"OpenAI AI Grants ({settings.aigrants_model})")

    print("\n" + "=" * 60)
    print("SUMMARY OF LIVE PROVIDER RESULTS")
    print("=" * 60)
    print(f"TensorMux: Tool Calling={tmx_res.get('tool_call_supported')}, Total Tokens={tmx_res.get('total_tokens')}, Latency={tmx_res.get('total_latency_ms', 0):.1f}ms")
    print(f"OpenAI:    Tool Calling={ai_res.get('tool_call_supported')}, Total Tokens={ai_res.get('total_tokens')}, Latency={ai_res.get('total_latency_ms', 0):.1f}ms")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
