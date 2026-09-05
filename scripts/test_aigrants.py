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

from app.providers.aigrants import AIGrantsIndiaProvider


async def test_aigrants():
    print("==================================================")
    print(" FORGE — AI Grants India (GPT-5 Nano) Check")
    print("==================================================")

    api_key = os.getenv("AIGRANTS_API_KEY", "")
    base_url = os.getenv("AIGRANTS_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("AIGRANTS_MODEL", "gpt-5-nano")

    print(f"Base URL: {base_url}")
    print(f"Model:    {model}")

    if not api_key:
        print("\n[INFO] AIGRANTS_API_KEY is not configured yet.")
        print("You can request GPT-5 Nano access from AI Grants India here:")
        print("👉 https://aigrants.in/form?ref=ao")
        sys.exit(1)

    print(f"API Key:  {api_key[:6]}...{api_key[-4:]}")
    print("\nSending ping prompt to GPT-5 Nano...")

    provider = AIGrantsIndiaProvider(api_key=api_key, base_url=base_url, model=model)
    try:
        response = await provider.generate(
            messages=[{"role": "user", "content": "Hello from FORGE! Reply with 'GPT-5 NANO ONLINE' and a 5-word confirmation."}],
            temperature=0.1,
        )
        print("\n[SUCCESS] Connected to GPT-5 Nano successfully!")
        print(f"Response: {response.content}")
        print(f"Latency:  {response.latency_ms:.1f} ms")
        print(f"Tokens:   {response.total_tokens}")
        print("==================================================")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAILURE] Error: {e}")
        print("==================================================")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_aigrants())
