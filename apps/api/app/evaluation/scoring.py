from app.evaluation.metrics import (
    ExecutionMetrics,
    GenerationMetrics,
    PRICE_PER_1K_PROMPT_TOKENS,
    PRICE_PER_1K_COMPLETION_TOKENS,
)
from app.agents.state import AgentState
from app.benchmarks.base import TaskEvaluation


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates estimated cost in USD based on token usage."""
    cost = (input_tokens / 1000.0 * PRICE_PER_1K_PROMPT_TOKENS) + (
        output_tokens / 1000.0 * PRICE_PER_1K_COMPLETION_TOKENS
    )
    return round(cost, 6)


def compute_reliability(state: AgentState, evaluation: TaskEvaluation) -> float:
    """
    Computes reliability score in range [0.0, 1.0]:
    - 40%: Verification passed
    - 30%: Tool success rate (low error frequency)
    - 20%: Clean termination (no timeouts or runaway steps)
    - 10%: Recovery capability (if errors occurred, did it recover)
    """
    verif_score = 1.0 if (state.verification_passed or evaluation.verification_passed) else 0.0

    total_tc = max(state.tool_call_count, 1)
    tool_errors = len([tr for tr in state.tool_results if not tr.get("success", False)])
    tool_success_rate = max(0.0, 1.0 - (tool_errors / total_tc))

    clean_exit = 1.0 if state.status == "COMPLETED" else 0.0

    had_errors = (tool_errors > 0 or len(state.errors) > 0)
    recovered = 1.0 if (had_errors and evaluation.passed) else (0.5 if not had_errors else 0.0)

    reliability = (
        0.40 * verif_score
        + 0.30 * tool_success_rate
        + 0.20 * clean_exit
        + 0.10 * recovered
    )
    return round(max(0.0, min(1.0, reliability)), 4)


def compute_composite_score(
    accuracy: float,
    reliability: float,
    avg_cost_per_task: float,
    avg_latency_ms: float,
) -> float:
    """
    Primary: Correctness (50%) + Reliability (30%)
    Secondary: Cost efficiency (10%) + Latency efficiency (10%)
    Normalized to [0.0, 1.0].
    """
    # Baseline reference: $0.10 cost per task, 30.0s latency
    cost_score = max(0.0, min(1.0, 1.0 - (avg_cost_per_task / 0.10)))
    speed_score = max(0.0, min(1.0, 1.0 - (avg_latency_ms / 30000.0)))

    composite = (
        0.50 * accuracy
        + 0.30 * reliability
        + 0.10 * cost_score
        + 0.10 * speed_score
    )
    return round(max(0.0, min(1.0, composite)), 4)


def aggregate_generation_metrics(
    generation_number: int,
    task_metrics: list[ExecutionMetrics],
    failure_counts: dict[str, int] | None = None,
) -> GenerationMetrics:
    total_tasks = len(task_metrics)
    if total_tasks == 0:
        return GenerationMetrics(
            generation_number=generation_number,
            total_tasks=0,
            successful_tasks=0,
            accuracy=0.0,
            reliability=0.0,
            total_cost_usd=0.0,
            avg_cost_per_task=0.0,
            avg_latency_ms=0.0,
            composite_score=0.0,
        )

    successful = sum(1 for tm in task_metrics if tm.task_success)
    accuracy = round(successful / total_tasks, 4)
    avg_reliability = round(sum(tm.reliability for tm in task_metrics) / total_tasks, 4)
    total_cost = round(sum(tm.cost_usd for tm in task_metrics), 6)
    avg_cost = round(total_cost / total_tasks, 6)
    avg_latency = round(sum(tm.latency_ms for tm in task_metrics) / total_tasks, 1)

    total_tokens = sum(tm.total_tokens for tm in task_metrics)
    total_model_calls = sum(tm.model_calls for tm in task_metrics)
    total_tool_calls = sum(tm.tool_calls for tm in task_metrics)
    verif_rate = round(sum(1 for tm in task_metrics if tm.verification_passed) / total_tasks, 4)

    comp_score = compute_composite_score(accuracy, avg_reliability, avg_cost, avg_latency)

    return GenerationMetrics(
        generation_number=generation_number,
        total_tasks=total_tasks,
        successful_tasks=successful,
        accuracy=accuracy,
        reliability=avg_reliability,
        total_cost_usd=total_cost,
        avg_cost_per_task=avg_cost,
        avg_latency_ms=avg_latency,
        composite_score=comp_score,
        total_tokens=total_tokens,
        total_model_calls=total_model_calls,
        total_tool_calls=total_tool_calls,
        verification_pass_rate=verif_rate,
        failure_breakdown=failure_counts or {},
    )
