import time
import json
import asyncio
from typing import Any
import os
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from app.core.errors import ProviderError, ProviderTimeoutError, ProviderRateLimitError
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem


class ExperientialProvider(LLMProvider):
    """
    Inference provider for gpt-6-astra routed through Experiential Labs gateway
    (https://api.experientiallabs.ai/v1).
    Uses standard OpenAI-compatible completions format.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
    ):
        self.api_key = api_key or os.getenv("EXPLABS_API_KEY", "")
        self.base_url = base_url or os.getenv("EXPLABS_BASE_URL", "https://api.experientiallabs.ai/v1")
        self.model = model or os.getenv("EXPLABS_MODEL", "gpt-6-astra")
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
                "EXPLABS_API_KEY is not configured. Set EXPLABS_API_KEY in environment or .env."
            )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            formatted_tools = []
            for t in tools:
                if "type" in t and t["type"] == "function":
                    formatted_tools.append(t)
                else:
                    formatted_tools.append({"type": "function", "function": t})
            kwargs["tools"] = formatted_tools
            kwargs["tool_choice"] = "auto"

        if response_format:
            kwargs["response_format"] = response_format

        start_time = time.perf_counter()
        try:
            resp = await self.client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            choice = resp.choices[0]
            content = choice.message.content

            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    except Exception:
                        args = {"raw": tc.function.arguments}
                    tool_calls.append(
                        ToolCallItem(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=args,
                        )
                    )

            usage = resp.usage
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency_ms=latency_ms,
                raw_response=resp,
            )
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"Experiential Labs timeout: {e}") from e
        except RateLimitError as e:
            raise ProviderRateLimitError(f"Experiential Labs rate limit: {e}") from e
        except APIError as e:
            raise ProviderError(f"Experiential Labs API error: {e}") from e
        except Exception as e:
            raise ProviderError(f"Unexpected error calling gpt-6-astra via Experiential: {e}") from e
