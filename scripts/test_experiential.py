#!/usr/bin/env python3
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.providers.experiential import ExperientialProvider


async def test_experiential():
    print("==================================================")
    print(" Experiential Labs Gateway — gpt-6-astra Check")
    print("==================================================")

    api_key = os.getenv("EXPLABS_API_KEY", "")
    base_url = os.getenv("EXPLABS_BASE_URL", "https://api.experientiallabs.ai/v1")
    model = os.getenv("EXPLABS_MODEL", "gpt-6-astra")

    print(f"Base URL: {base_url}")
    print(f"Model:    {model}")

    if not api_key:
        print("\n[ERROR] EXPLABS_API_KEY is not set.")
        print("Please export EXPLABS_API_KEY or add it to your .env file.")
        sys.exit(1)

    masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
    print(f"API Key:  {masked_key}")
    print("\nSending test prompt to gpt-6-astra...")

    provider = ExperientialProvider(api_key=api_key, base_url=base_url, model=model)
    try:
        response = await provider.generate(
            messages=[
                {"role": "user", "content": "Hello! Confirm you are running on the Experiential Labs gateway."}
            ]
        )
        print("\n[SUCCESS] Connected to gpt-6-astra successfully!")
        print(f"Response: {response.content}")
        print(f"Latency:  {response.latency_ms:.1f} ms")
        print(f"Tokens:   Input: {response.input_tokens}, Output: {response.output_tokens}, Total: {response.total_tokens}")
        print("==================================================")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAILURE] Error calling gpt-6-astra: {e}")
        print("==================================================")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_experiential())
