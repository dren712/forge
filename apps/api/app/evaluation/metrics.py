from pydantic import BaseModel, Field
from typing import Any

# Pricing abstraction (GLM-4.7-Flash estimated rates per 1,000 tokens)
PRICE_PER_1K_PROMPT_TOKENS = 0.0005
PRICE_PER_1K_COMPLETION_TOKENS = 0.0015


class ExecutionMetrics(BaseModel):
    task_id: str
    task_success: bool
    accuracy: float
    reliability: float
    cost_usd: float
    latency_ms: float

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    verification_passed: bool = False
    clean_exit: bool = False
    recovered_from_error: bool = False


class GenerationMetrics(BaseModel):
    generation_number: int
    total_tasks: int
    successful_tasks: int
    accuracy: float
    reliability: float
    total_cost_usd: float
    avg_cost_per_task: float
    avg_latency_ms: float
    composite_score: float

    total_tokens: int = 0
    total_model_calls: int = 0
    total_tool_calls: int = 0
    verification_pass_rate: float = 0.0
    failure_breakdown: dict[str, int] = Field(default_factory=dict)
