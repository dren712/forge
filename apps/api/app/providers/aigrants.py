import time
import json
import asyncio
from typing import Any
import os
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from app.core.errors import ProviderError, ProviderTimeoutError, ProviderRateLimitError
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem


class AIGrantsIndiaProvider(LLMProvider):
    """
    Inference provider for GPT-5 Nano provided by AI Grants India (https://aigrants.in/form?ref=ao).
    Uses standard OpenAI-compatible completions format.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("AIGRANTS_API_KEY", "")
        self.base_url = base_url or os.getenv("AIGRANTS_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("AIGRANTS_MODEL", "gpt-5-nano")
        self.timeout = timeout

        self.client = AsyncOpenAI(
            api_key=self.api_key or "missing_key",
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if not self.api_key or self.api_key == "missing_key":
            raise ProviderError(
                "AIGRANTS_API_KEY is not configured. Request access at https://aigrants.in/form?ref=ao "
                "and set AIGRANTS_API_KEY in .env."
            )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            # temperature omitted for gpt-5-nano reasoning models
        }

        if tools:
            formatted_tools = []
            for t in tools:
                if "type" in t and t["type"] == "function":
                    formatted_tools.append(t)
                else:
                    formatted_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema", {}),
                        },
                    })
            kwargs["tools"] = formatted_tools

        if response_format:
            kwargs["response_format"] = response_format

        start_time = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            choice = response.choices[0]
            message = choice.message
            content = message.content

            tool_calls: list[ToolCallItem] = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {"raw": tc.function.arguments}
                    tool_calls.append(
                        ToolCallItem(id=tc.id, name=tc.function.name, arguments=args)
                    )

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else (input_tokens + output_tokens)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else str(response),
            )

        except APITimeoutError as e:
            raise ProviderTimeoutError(f"AI Grants GPT-5 Nano timed out: {e}")
        except RateLimitError as e:
            raise ProviderRateLimitError(f"AI Grants rate limit exceeded: {e}")
        except Exception as e:
            raise ProviderError(f"AI Grants GPT-5 Nano API error: {e}")
