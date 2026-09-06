#!/usr/bin/env python3
"""
FORGE TensorMux Connectivity & Verification Script
Reads configuration securely and executes a minimal generation test.
"""
import sys
import asyncio
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.core.config import settings
from app.providers.tensormux import TensorMuxProvider
from app.core.errors import ProviderError


async def main() -> int:
    print("=" * 60)
    print("FORGE — TensorMux Connectivity Verification")
    print("=" * 60)

    # 1. Read configuration securely
    api_key = settings.tensormux_api_key
    base_url = settings.tensormux_base_url
    model = settings.tensormux_model

    # 2. Verify API key exists without printing it
    if not api_key or api_key.startswith("tmx_your_api_key"):
        print("[ERROR] TENSORMUX_API_KEY is not configured in .env or environment.")
        return 1

    masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
    print(f"Configured Provider: TensorMux")
    print(f"Base URL:            {base_url}")
    print(f"Target Model:        {model}")
    print(f"Key Status:          Configured (Key: {masked_key}, length={len(api_key)})")

    # 3. Instantiate provider
    provider = TensorMuxProvider(api_key=api_key, base_url=base_url, model=model)

    # 4. Make minimal request
    print("\nSending minimal ping request...")
    messages = [
        {"role": "system", "content": "You are a concise AI assistant. Respond strictly as instructed."},
        {"role": "user", "content": "Respond with the word 'pong' and nothing else."},
    ]

    try:
        res = await provider.generate(messages, temperature=0.0)
    except ProviderError as e:
        print(f"[FAIL] TensorMux ProviderError: {e}")
        return 2
    except Exception as e:
        print(f"[FAIL] Unexpected error during TensorMux generation: {e}")
        return 3

    # 5. Verify success and print normalized response
    print("\n[SUCCESS] Response received from TensorMux API:")
    print(f"  Content:      {res.content!r}")
    print(f"  Tool Calls:   {len(res.tool_calls)}")
    print(f"  Input Tokens: {res.input_tokens}")
    print(f"  Output Tokens:{res.output_tokens}")
    print(f"  Total Tokens: {res.total_tokens}")
    print(f"  Latency:      {res.latency_ms:.2f} ms")
    print(f"  Finish Reason:{getattr(res, 'finish_reason', 'stop')}")

    if not res.content:
        print("[FAIL] Model returned empty content.")
        return 4

    print("\nConnectivity verification: PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
