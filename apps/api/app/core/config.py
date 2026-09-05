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

    max_agent_steps: int = Field(default_factory=lambda: int(os.getenv("MAX_AGENT_STEPS", "20")))
    max_tool_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "30")))
    max_agent_runtime_seconds: int = Field(default_factory=lambda: int(os.getenv("MAX_AGENT_RUNTIME_SECONDS", "180")))
    max_model_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_MODEL_RETRIES", "2")))

    root_dir: Path = Path(__file__).resolve().parents[4]
    benchmarks_dir: Path = Path(__file__).resolve().parents[4] / "benchmarks"


settings = Settings()
