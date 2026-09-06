from pydantic import BaseModel, Field
import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current directory or up to project root
env_path = Path(__file__).resolve().parents[4] / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


class Settings(BaseModel):
    tensormux_api_key: str = Field(default_factory=lambda: os.getenv("TENSORMUX_API_KEY", ""))
    tensormux_base_url: str = Field(default_factory=lambda: os.getenv("TENSORMUX_BASE_URL", "https://api.tensormux.com/v1"))
    tensormux_model: str = Field(default_factory=lambda: os.getenv("TENSORMUX_MODEL", "glm-4-7-flash"))

    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///forge.db"))
    forge_env: str = Field(default_factory=lambda: os.getenv("FORGE_ENV", "development"))
    forge_test_mode: str = Field(default_factory=lambda: os.getenv("FORGE_TEST_MODE", "0"))
    forge_llm_provider: str = Field(default_factory=lambda: os.getenv("FORGE_LLM_PROVIDER", "tensormux"))
    forge_architect_provider: str = Field(default_factory=lambda: os.getenv("FORGE_ARCHITECT_PROVIDER", "tensormux"))
    forge_executor_provider: str = Field(default_factory=lambda: os.getenv("FORGE_EXECUTOR_PROVIDER", "tensormux"))
    forge_reflector_provider: str = Field(default_factory=lambda: os.getenv("FORGE_REFLECTOR_PROVIDER", "openai"))
    forge_mutator_provider: str = Field(default_factory=lambda: os.getenv("FORGE_MUTATOR_PROVIDER", "tensormux"))

    # Sponsor Provider Configs
    aigrants_api_key: str = Field(default_factory=lambda: os.getenv("AIGRANTS_API_KEY") or os.getenv("OPENAI_API_KEY", ""))
    aigrants_base_url: str = Field(default_factory=lambda: os.getenv("AIGRANTS_BASE_URL", "https://api.openai.com/v1"))
    aigrants_model: str = Field(default_factory=lambda: os.getenv("AIGRANTS_MODEL", "gpt-5-nano"))

    smallest_api_key: str = Field(default_factory=lambda: os.getenv("SMALLEST_API_KEY", ""))
    smallest_base_url: str = Field(default_factory=lambda: os.getenv("SMALLEST_BASE_URL", "https://waves-api.smallest.ai/api/v1/lightning-v3.1/get_speech"))
    smallest_voice_id: str = Field(default_factory=lambda: os.getenv("SMALLEST_VOICE_ID", "emily"))

    explabs_api_key: str = Field(default_factory=lambda: os.getenv("EXPLABS_API_KEY", ""))
    explabs_base_url: str = Field(default_factory=lambda: os.getenv("EXPLABS_BASE_URL", "https://api.experientiallabs.ai/v1"))
    explabs_model: str = Field(default_factory=lambda: os.getenv("EXPLABS_MODEL", "gpt-6-astra"))

    max_agent_steps: int = Field(default_factory=lambda: int(os.getenv("MAX_AGENT_STEPS", "20")))
    max_tool_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "30")))
    max_agent_runtime_seconds: int = Field(default_factory=lambda: int(os.getenv("MAX_AGENT_RUNTIME_SECONDS", "180")))
    max_model_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_MODEL_RETRIES", "2")))

    root_dir: Path = Path(__file__).resolve().parents[4]
    benchmarks_dir: Path = Path(__file__).resolve().parents[4] / "benchmarks"


settings = Settings()
