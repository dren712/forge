import time
import json
import asyncio
from typing import Any
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError, BadRequestError

from app.core.config import settings
from app.core.errors import (
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderInvalidResponseError,
)
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem


class TensorMuxProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or settings.tensormux_api_key
        self.base_url = base_url or settings.tensormux_base_url
        self.model = model or settings.tensormux_model
        self.timeout = timeout

        if not self.api_key:
            # We allow instantiating without an immediate key, but calls will validate
            pass

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
                "TENSORMUX_API_KEY is not configured. Please set TENSORMUX_API_KEY in .env or environment."
            )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
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

        max_retries = settings.max_model_retries
        last_exception = None

        for attempt in range(max_retries + 1):
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
                            ToolCallItem(
                                id=tc.id,
                                name=tc.function.name,
                                arguments=args,
                            )
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
                last_exception = ProviderTimeoutError(f"TensorMux request timed out: {e}")
            except RateLimitError as e:
                last_exception = ProviderRateLimitError(f"TensorMux rate limit exceeded: {e}")
            except BadRequestError as e:
                raise ProviderInvalidResponseError(f"Invalid request to TensorMux: {e}") from e
            except APIError as e:
                last_exception = ProviderError(f"TensorMux API error: {e}")
            except Exception as e:
                last_exception = ProviderError(f"Unexpected error communicating with TensorMux: {e}")

            if attempt < max_retries:
                await asyncio.sleep(1.0 * (attempt + 1))

        raise last_exception or ProviderError("Failed to generate response after retries")
