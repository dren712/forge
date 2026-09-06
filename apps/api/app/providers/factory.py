import os
from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.tensormux import TensorMuxProvider
from app.providers.aigrants import AIGrantsIndiaProvider
from app.providers.mock import DeterministicMockProvider
from app.providers.experiential import ExperientialProvider


def get_llm_provider() -> LLMProvider:
    """Returns configured LLMProvider instance based on centralized settings."""
    if settings.forge_test_mode == "1" or os.getenv("FORGE_TEST_MODE") == "1":
        return DeterministicMockProvider(mode="baseline")

    preferred = (settings.forge_llm_provider or "tensormux").lower()
    if preferred in ("aigrants", "openai"):
        ai_key = settings.aigrants_api_key
        if ai_key and not ai_key.startswith("sk-proj-placeholder"):
            return AIGrantsIndiaProvider(api_key=ai_key, base_url=settings.aigrants_base_url, model=settings.aigrants_model)

    if preferred in ("experiential", "explabs", "astra"):
        exp_key = settings.explabs_api_key
        if exp_key:
            return ExperientialProvider(api_key=exp_key, base_url=settings.explabs_base_url, model=settings.explabs_model)

    key = settings.tensormux_api_key
    if key and not key.startswith("tmx_your_api_key") and len(key) > 5:
        return TensorMuxProvider(api_key=key, base_url=settings.tensormux_base_url, model=settings.tensormux_model)

    ai_key = settings.aigrants_api_key
    if ai_key and len(ai_key) > 10 and not ai_key.startswith("sk-proj-placeholder"):
        return AIGrantsIndiaProvider(api_key=ai_key, base_url=settings.aigrants_base_url, model=settings.aigrants_model)

    return DeterministicMockProvider(mode="baseline")
