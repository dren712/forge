import pytest
from app.evaluation.scoring import compute_cost, compute_composite_score, compute_reliability
from app.agents.state import AgentState
from app.benchmarks.base import TaskEvaluation


def test_cost_computation():
    cost = compute_cost(1000, 1000)
    # 1000 prompt @ 0.0005 + 1000 completion @ 0.0015 = 0.002
    assert cost == 0.002


def test_composite_score():
    # 100% accuracy, 100% reliability, zero cost, low latency
    score = compute_composite_score(1.0, 1.0, 0.0, 5000.0)
    assert score >= 0.90

    # 0% accuracy, 0% reliability
    score_zero = compute_composite_score(0.0, 0.0, 0.10, 30000.0)
    assert score_zero == 0.0


def test_reliability_scoring():
    state = AgentState(goal="Test")
    state.verification_passed = True
    state.status = "COMPLETED"
    state.tool_call_count = 2
    state.tool_results = [{"success": True}, {"success": True}]

    evaluation = TaskEvaluation(
        task_id="t1",
        passed=True,
        score=1.0,
        reason="Tests passed",
        verification_passed=True,
    )

    rel = compute_reliability(state, evaluation)
    # 0.40 (verif) + 0.30 (tool success) + 0.20 (clean exit) + 0.05 (clean baseline) = ~0.95
    assert rel >= 0.90
