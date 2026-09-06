from enum import Enum
from typing import Optional
from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.providers.tensormux import TensorMuxProvider
from app.providers.aigrants import AIGrantsIndiaProvider
from app.providers.mock import DeterministicMockProvider
from app.providers.experiential import ExperientialProvider


class ModelRole(str, Enum):
    ARCHITECT = "ARCHITECT"
    EXECUTOR = "EXECUTOR"
    REFLECTOR = "REFLECTOR"
    MUTATOR = "MUTATOR"
    NARRATOR = "NARRATOR"


class ModelRouter:
    """
    Lightweight model router directing tasks to specialized providers based on configured roles.
    Allows decoupling domain logic from hardcoded model names.
    """

    def __init__(self):
        pass

    def get_provider_for_name(self, name: str) -> LLMProvider:
        name = (name or "").lower()
        if settings.forge_test_mode == "1":
            return DeterministicMockProvider(mode="baseline")

        if name in ("aigrants", "openai"):
            ai_key = settings.aigrants_api_key
            if ai_key and not ai_key.startswith("sk-proj-placeholder"):
                return AIGrantsIndiaProvider(
                    api_key=ai_key,
                    base_url=settings.aigrants_base_url,
                    model=settings.aigrants_model,
                )

        if name in ("experiential", "explabs", "astra"):
            exp_key = settings.explabs_api_key
            if exp_key:
                return ExperientialProvider(
                    api_key=exp_key,
                    base_url=settings.explabs_base_url,
                    model=settings.explabs_model,
                )

        key = settings.tensormux_api_key
        if key and not key.startswith("tmx_your_api_key") and len(key) > 5:
            return TensorMuxProvider(
                api_key=key,
                base_url=settings.tensormux_base_url,
                model=settings.tensormux_model,
            )

        return get_llm_provider()

    def get_provider(self, role: ModelRole) -> LLMProvider:
        if settings.forge_test_mode == "1":
            return DeterministicMockProvider(mode="baseline")

        role_target_map = {
            ModelRole.ARCHITECT: settings.forge_architect_provider,
            ModelRole.EXECUTOR: settings.forge_executor_provider,
            ModelRole.REFLECTOR: settings.forge_reflector_provider,
            ModelRole.MUTATOR: settings.forge_mutator_provider,
            ModelRole.NARRATOR: settings.forge_llm_provider,
        }

        target_provider_name = role_target_map.get(role, settings.forge_llm_provider)
        return self.get_provider_for_name(target_provider_name)


model_router = ModelRouter()
