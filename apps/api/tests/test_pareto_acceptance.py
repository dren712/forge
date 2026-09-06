import pytest
from app.evaluation.metrics import GenerationMetrics
from app.evolution.acceptance import (
    AcceptanceEngine,
    AcceptanceDecision,
    DominanceResult,
    TradeoffPolicy,
    evaluate_acceptance,
)


def test_case_1_candidate_dominates_parent_accept():
    """
    Case 1: Candidate dominates parent -> ACCEPT.
    Candidate is no worse on all 4 objectives and strictly better on at least one.
    """
    engine = AcceptanceEngine()

    parent = {
        "accuracy": 0.60,
        "reliability": 0.60,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }

    # 1. Strictly better on all 4 metrics
    cand_all_better = {
        "accuracy": 0.80,  # higher is better
        "reliability": 0.75,  # higher is better
        "cost_per_task": 0.008,  # lower is better
        "latency_per_task": 900.0,  # lower is better
    }
    decision = engine.evaluate_candidate(parent, cand_all_better)
    assert decision.accepted is True
    assert decision.status == "ACCEPTED"
    assert decision.dominance_result == DominanceResult.CANDIDATE_DOMINATES
    assert "Pareto-dominates" in decision.reason
    assert decision.metrics_delta["accuracy"] > 0
    assert decision.metrics_delta["cost_per_task"] < 0

    # 2. Strictly better on accuracy only, equal on the other 3
    cand_acc_only = {
        "accuracy": 0.75,
        "reliability": 0.60,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }
    decision_acc = engine.evaluate_candidate(parent, cand_acc_only)
    assert decision_acc.accepted is True
    assert decision_acc.dominance_result == DominanceResult.CANDIDATE_DOMINATES

    # 3. Strictly better on cost only (cheaper), equal on other 3
    cand_cost_only = {
        "accuracy": 0.60,
        "reliability": 0.60,
        "cost_per_task": 0.005,
        "latency_per_task": 1000.0,
    }
    decision_cost = engine.evaluate_candidate(parent, cand_cost_only)
    assert decision_cost.accepted is True
    assert decision_cost.dominance_result == DominanceResult.CANDIDATE_DOMINATES

    # 4. Tested with GenerationMetrics typed models
    p_model = GenerationMetrics(
        generation_number=0,
        total_tasks=10,
        successful_tasks=6,
        accuracy=0.60,
        reliability=0.60,
        total_cost_usd=0.10,
        avg_cost_per_task=0.010,
        avg_latency_ms=1000.0,
        composite_score=0.60,
    )
    c_model = p_model.model_copy(update={
        "accuracy": 0.85,
        "reliability": 0.80,
        "composite_score": 0.82,
    })
    decision_model = engine.evaluate_candidate(p_model, c_model)
    assert decision_model.accepted is True
    assert decision_model.dominance_result == DominanceResult.CANDIDATE_DOMINATES


def test_case_2_parent_dominates_candidate_reject():
    """
    Case 2: Parent dominates candidate -> REJECT.
    Parent is strictly better on at least one objective and candidate is no better on any.
    """
    engine = AcceptanceEngine()

    parent = {
        "accuracy": 0.70,
        "reliability": 0.70,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }

    # 1. Regressed on all 4 metrics
    cand_all_worse = {
        "accuracy": 0.50,
        "reliability": 0.55,
        "cost_per_task": 0.015,
        "latency_per_task": 1200.0,
    }
    decision = engine.evaluate_candidate(parent, cand_all_worse)
    assert decision.accepted is False
    assert decision.status == "REJECTED"
    assert decision.dominance_result == DominanceResult.PARENT_DOMINATES
    assert "Parent dominates" in decision.reason

    # 2. Regressed on cost only (more expensive), equal on other 3
    cand_cost_worse = {
        "accuracy": 0.70,
        "reliability": 0.70,
        "cost_per_task": 0.020,
        "latency_per_task": 1000.0,
    }
    decision_cost = engine.evaluate_candidate(parent, cand_cost_worse)
    assert decision_cost.accepted is False
    assert decision_cost.dominance_result == DominanceResult.PARENT_DOMINATES

    # 3. Regressed on accuracy only, equal on other 3
    cand_acc_worse = {
        "accuracy": 0.60,
        "reliability": 0.70,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }
    decision_acc = engine.evaluate_candidate(parent, cand_acc_worse)
    assert decision_acc.accepted is False
    assert decision_acc.dominance_result == DominanceResult.PARENT_DOMINATES


def test_case_3_tradeoff_no_dominance_uses_configured_policy():
    """
    Case 3: Tradeoff/no dominance -> use configured policy and explain decision.
    """
    # 1. Exact user prompt example:
    # Accuracy: +4%, Reliability: +2%, Cost: +74%, Latency: +39% -> REJECTED
    engine = AcceptanceEngine(
        tradeoff_policy=TradeoffPolicy.COMPOSITE_THRESHOLD,
        max_cost_regression_pct=50.0,
        max_latency_regression_pct=30.0,
        min_accuracy_gain_for_tradeoff=0.05,
    )

    parent = {
        "accuracy": 0.50,
        "reliability": 0.50,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }
    # Accuracy +4% points (0.50 -> 0.52 = +4%), Reliability +2% points (0.50 -> 0.51 = +2%)
    # Cost +74% (0.010 -> 0.0174 = +74%), Latency +39% (1000.0 -> 1390.0 = +39%)
    cand_prompt_example = {
        "accuracy": 0.52,
        "reliability": 0.51,
        "cost_per_task": 0.0174,
        "latency_per_task": 1390.0,
    }

    decision = engine.evaluate_candidate(parent, cand_prompt_example)
    assert decision.dominance_result == DominanceResult.TRADEOFF
    assert decision.accepted is False
    assert decision.status == "REJECTED"
    assert decision.reason == (
        "Candidate is dominated by parent because cost and latency regress substantially "
        "without sufficient compensating improvement."
    )

    # 2. Strict Pareto policy rejects any tradeoff
    engine_strict = AcceptanceEngine(tradeoff_policy=TradeoffPolicy.STRICT_PARETO)
    cand_mild_tradeoff = {
        "accuracy": 0.70,  # +20% improvement
        "reliability": 0.65,  # +15% improvement
        "cost_per_task": 0.0105,  # +5% mild cost regression
        "latency_per_task": 1020.0,  # +2% mild latency regression
    }
    decision_strict = engine_strict.evaluate_candidate(parent, cand_mild_tradeoff)
    assert decision_strict.dominance_result == DominanceResult.TRADEOFF
    assert decision_strict.accepted is False
    assert "strict Pareto policy" in decision_strict.reason

    # 3. Configured composite threshold policy accepts favorable tradeoff
    engine_composite = AcceptanceEngine(
        tradeoff_policy=TradeoffPolicy.COMPOSITE_THRESHOLD,
        max_cost_regression_pct=50.0,
        max_latency_regression_pct=30.0,
        min_composite_gain=0.01,
    )
    decision_favorable = engine_composite.evaluate_candidate(parent, cand_mild_tradeoff)
    assert decision_favorable.dominance_result == DominanceResult.TRADEOFF
    assert decision_favorable.accepted is True
    assert decision_favorable.status == "ACCEPTED"
    assert "Tradeoff accepted by configured policy" in decision_favorable.reason

    # 4. Custom callable tradeoff resolver
    def custom_tradeoff_resolver(metrics_delta, dominance):
        return False, "Custom policy rejected: enterprise budget ceiling reached."

    decision_custom = engine.evaluate_candidate(parent, cand_mild_tradeoff, tradeoff_policy=custom_tradeoff_resolver)
    assert decision_custom.accepted is False
    assert decision_custom.reason == "Custom policy rejected: enterprise budget ceiling reached."


def test_case_4_identical_metrics_reject():
    """
    Case 4: Identical metrics -> REJECT.
    Candidate produces no measurable change across all 4 objectives.
    """
    engine = AcceptanceEngine()

    parent = {
        "accuracy": 0.75,
        "reliability": 0.80,
        "cost_per_task": 0.005,
        "latency_per_task": 1200.0,
    }
    candidate = dict(parent)

    decision = engine.evaluate_candidate(parent, candidate)
    assert decision.accepted is False
    assert decision.status == "REJECTED"
    assert decision.dominance_result == DominanceResult.EQUAL
    assert "identical" in decision.reason.lower()


def test_accuracy_increase_does_not_automatically_win():
    """
    Explicit verification of requirement:
    'A candidate must NOT automatically win merely because accuracy increases.'
    """
    engine = AcceptanceEngine(
        tradeoff_policy=TradeoffPolicy.COMPOSITE_THRESHOLD,
        max_cost_regression_pct=40.0,
    )

    parent = {
        "accuracy": 0.80,
        "reliability": 0.80,
        "cost_per_task": 0.010,
        "latency_per_task": 1000.0,
    }
    # Accuracy increases (+4% points), but cost surges by +80%
    candidate = {
        "accuracy": 0.84,  # Increased accuracy (+4% points)
        "reliability": 0.80,
        "cost_per_task": 0.018,  # +80% cost surge
        "latency_per_task": 1000.0,
    }

    decision = engine.evaluate_candidate(parent, candidate)
    assert decision.accepted is False
    assert decision.dominance_result == DominanceResult.TRADEOFF
    assert "cost regressed substantially" in decision.reason


def test_tolerance_configuration():
    """
    Verifies that configurable tolerance properly treats near-zero variations as equal.
    """
    parent = {
        "accuracy": 0.5000,
        "reliability": 0.5000,
        "cost_per_task": 0.001000,
        "latency_per_task": 1000.0,
    }
    # Variation of 0.00002 on accuracy
    candidate_tiny_diff = {
        "accuracy": 0.50002,
        "reliability": 0.5000,
        "cost_per_task": 0.001000,
        "latency_per_task": 1000.0,
    }

    # Default tolerance (1e-4) treats difference <= 1e-4 as equal
    engine_default = AcceptanceEngine(tolerance=1e-4)
    decision = engine_default.evaluate_candidate(parent, candidate_tiny_diff)
    assert decision.dominance_result == DominanceResult.EQUAL
    assert decision.accepted is False

    # Zero tolerance recognizes the difference as candidate dominance
    engine_strict_zero = AcceptanceEngine(tolerance=0.0)
    decision_zero = engine_strict_zero.evaluate_candidate(parent, candidate_tiny_diff)
    assert decision_zero.dominance_result == DominanceResult.CANDIDATE_DOMINATES
    assert decision_zero.accepted is True


def test_return_fields_and_dict_compatibility():
    """
    Verifies that the return structure provides:
    - accepted: bool
    - reason: str
    - metrics_delta: dict
    - dominance_result: DominanceResult/str
    along with dictionary access support.
    """
    parent = {"accuracy": 0.5, "reliability": 0.5, "cost_per_task": 0.01, "latency_per_task": 1000}
    cand = {"accuracy": 0.8, "reliability": 0.8, "cost_per_task": 0.01, "latency_per_task": 1000}

    decision = evaluate_acceptance(parent, cand)

    assert isinstance(decision.accepted, bool)
    assert isinstance(decision.reason, str)
    assert isinstance(decision.metrics_delta, dict)
    assert isinstance(decision.dominance_result, str)

    # Dict access
    assert decision["accepted"] is True
    assert decision["status"] == "ACCEPTED"
    assert "accuracy" in decision["metrics_delta"]
