from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.evaluation.metrics import GenerationMetrics
from app.evaluation.scoring import compute_composite_score


class DominanceResult(str, Enum):
    CANDIDATE_DOMINATES = "CANDIDATE_DOMINATES"
    PARENT_DOMINATES = "PARENT_DOMINATES"
    TRADEOFF = "TRADEOFF"
    EQUAL = "EQUAL"


class TradeoffPolicy(str, Enum):
    STRICT_PARETO = "strict_pareto"
    COMPOSITE_THRESHOLD = "composite_threshold"


class AcceptanceDecision(BaseModel):
    accepted: bool
    status: str = "REJECTED"  # "ACCEPTED" or "REJECTED"
    reason: str
    dominance_result: DominanceResult = DominanceResult.EQUAL
    metrics_delta: dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility and auxiliary fields
    accuracy_delta: float = 0.0
    reliability_delta: float = 0.0
    cost_delta_percent: float = 0.0
    latency_delta_percent: float = 0.0
    composite_delta: float = 0.0

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


DEFAULT_TOLERANCES: dict[str, float] = {
    "accuracy": 1e-4,
    "reliability": 1e-4,
    "cost_per_task": 1e-6,
    "latency_per_task": 0.1,
}


class AcceptanceEngine:
    """
    FORGE S6-G: Pareto Acceptance Gate for candidate generations.
    Evaluates 4 core objectives:
    1. accuracy (higher is better)
    2. reliability (higher is better)
    3. cost_per_task (lower is better)
    4. latency_per_task (lower is better)

    Decision Logic:
    - Candidate strictly Pareto-dominates parent (no worse on any, better on >=1) -> ACCEPT
    - Parent strictly Pareto-dominates candidate -> REJECT
    - Identical metrics within tolerance -> REJECT
    - Tradeoff (better on some, worse on others) -> Resolved via configured tradeoff policy:
      * STRICT_PARETO: rejects any tradeoff
      * COMPOSITE_THRESHOLD: rejects substantial regressions (e.g. cost >50%, latency >30%),
        accepts favorable tradeoffs when composite improvement exceeds threshold.
    """

    def __init__(
        self,
        tradeoff_policy: TradeoffPolicy | str = TradeoffPolicy.COMPOSITE_THRESHOLD,
        tolerance: float | dict[str, float] | None = None,
        max_cost_regression_pct: float = 50.0,
        max_latency_regression_pct: float = 30.0,
        min_composite_gain: float = 0.01,
        min_accuracy_gain_for_tradeoff: float = 0.05,
    ):
        if isinstance(tradeoff_policy, str):
            try:
                tradeoff_policy = TradeoffPolicy(tradeoff_policy)
            except ValueError:
                pass
        self.tradeoff_policy = tradeoff_policy
        self.tolerance = tolerance
        self.max_cost_regression_pct = max_cost_regression_pct
        self.max_latency_regression_pct = max_latency_regression_pct
        self.min_composite_gain = min_composite_gain
        self.min_accuracy_gain_for_tradeoff = min_accuracy_gain_for_tradeoff

    def _resolve_tolerances(
        self, tolerance_override: float | dict[str, float] | None = None
    ) -> dict[str, float]:
        tol = tolerance_override if tolerance_override is not None else self.tolerance
        if tol is None:
            return dict(DEFAULT_TOLERANCES)
        if isinstance(tol, dict):
            return {
                "accuracy": float(tol.get("accuracy", DEFAULT_TOLERANCES["accuracy"])),
                "reliability": float(tol.get("reliability", DEFAULT_TOLERANCES["reliability"])),
                "cost_per_task": float(tol.get("cost_per_task", DEFAULT_TOLERANCES["cost_per_task"])),
                "latency_per_task": float(tol.get("latency_per_task", DEFAULT_TOLERANCES["latency_per_task"])),
            }
        val = float(tol)
        return {
            "accuracy": val,
            "reliability": val,
            "cost_per_task": val if val < 0.01 else DEFAULT_TOLERANCES["cost_per_task"],
            "latency_per_task": val if val >= 0.1 else DEFAULT_TOLERANCES["latency_per_task"],
        }

    @staticmethod
    def _extract_metrics(m: GenerationMetrics | dict[str, Any] | Any) -> tuple[float, float, float, float, float]:
        if isinstance(m, dict):
            acc = float(m.get("accuracy", 0.0))
            rel = float(m.get("reliability", 0.0))
            cost = float(m.get("cost_per_task", m.get("avg_cost_per_task", 0.0)))
            lat = float(m.get("latency_per_task", m.get("avg_latency_ms", 0.0)))
            comp = float(m.get("composite_score", 0.0))
            if comp == 0.0 and (acc > 0 or rel > 0):
                comp = compute_composite_score(acc, rel, cost, lat)
            return acc, rel, cost, lat, comp

        acc = float(getattr(m, "accuracy", 0.0))
        rel = float(getattr(m, "reliability", 0.0))
        cost = float(getattr(m, "avg_cost_per_task", getattr(m, "cost_per_task", 0.0)))
        lat = float(getattr(m, "avg_latency_ms", getattr(m, "latency_per_task", 0.0)))
        comp = float(getattr(m, "composite_score", 0.0))
        if comp == 0.0 and (acc > 0 or rel > 0):
            comp = compute_composite_score(acc, rel, cost, lat)
        return acc, rel, cost, lat, comp

    def evaluate_candidate(
        self,
        parent: GenerationMetrics | dict[str, Any] | Any,
        candidate: GenerationMetrics | dict[str, Any] | Any,
        tradeoff_policy: TradeoffPolicy | str | Callable | None = None,
        tolerance: float | dict[str, float] | None = None,
    ) -> AcceptanceDecision:
        p_acc, p_rel, p_cost, p_lat, p_comp = self._extract_metrics(parent)
        c_acc, c_rel, c_cost, c_lat, c_comp = self._extract_metrics(candidate)

        tols = self._resolve_tolerances(tolerance)
        active_policy = tradeoff_policy if tradeoff_policy is not None else self.tradeoff_policy

        # Deltas
        acc_delta = round(c_acc - p_acc, 6)
        rel_delta = round(c_rel - p_rel, 6)
        cost_delta = round(c_cost - p_cost, 6)
        lat_delta = round(c_lat - p_lat, 2)
        comp_delta = round(c_comp - p_comp, 6)

        # Percentage deltas (relative to parent baseline)
        acc_delta_pct = round(((c_acc - p_acc) / p_acc * 100.0), 2) if p_acc > 0 else 0.0
        rel_delta_pct = round(((c_rel - p_rel) / p_rel * 100.0), 2) if p_rel > 0 else 0.0
        cost_delta_pct = round(((c_cost - p_cost) / p_cost * 100.0), 2) if p_cost > 0 else 0.0
        lat_delta_pct = round(((c_lat - p_lat) / p_lat * 100.0), 2) if p_lat > 0 else 0.0

        better_objectives: list[str] = []
        worse_objectives: list[str] = []
        equal_objectives: list[str] = []

        # 1. Accuracy (higher is better)
        if c_acc - p_acc > tols["accuracy"]:
            better_objectives.append("accuracy")
        elif p_acc - c_acc > tols["accuracy"]:
            worse_objectives.append("accuracy")
        else:
            equal_objectives.append("accuracy")

        # 2. Reliability (higher is better)
        if c_rel - p_rel > tols["reliability"]:
            better_objectives.append("reliability")
        elif p_rel - c_rel > tols["reliability"]:
            worse_objectives.append("reliability")
        else:
            equal_objectives.append("reliability")

        # 3. Cost per task (lower is better)
        if p_cost - c_cost > tols["cost_per_task"]:
            better_objectives.append("cost_per_task")
        elif c_cost - p_cost > tols["cost_per_task"]:
            worse_objectives.append("cost_per_task")
        else:
            equal_objectives.append("cost_per_task")

        # 4. Latency per task (lower is better)
        if p_lat - c_lat > tols["latency_per_task"]:
            better_objectives.append("latency_per_task")
        elif c_lat - p_lat > tols["latency_per_task"]:
            worse_objectives.append("latency_per_task")
        else:
            equal_objectives.append("latency_per_task")

        metrics_delta = {
            "accuracy": acc_delta,
            "reliability": rel_delta,
            "cost_per_task": cost_delta,
            "latency_per_task": lat_delta,
            "accuracy_percent": acc_delta_pct,
            "reliability_percent": rel_delta_pct,
            "cost_percent": cost_delta_pct,
            "latency_percent": lat_delta_pct,
            "accuracy_delta": acc_delta,
            "reliability_delta": rel_delta,
            "cost_delta": cost_delta,
            "latency_delta": lat_delta,
            "cost_delta_percent": cost_delta_pct,
            "latency_delta_percent": lat_delta_pct,
            "composite": comp_delta,
            "composite_delta": comp_delta,
            "details": {
                "accuracy": {
                    "parent": p_acc,
                    "candidate": c_acc,
                    "delta": acc_delta,
                    "delta_percent": acc_delta_pct,
                    "direction": "better" if "accuracy" in better_objectives else ("worse" if "accuracy" in worse_objectives else "equal"),
                },
                "reliability": {
                    "parent": p_rel,
                    "candidate": c_rel,
                    "delta": rel_delta,
                    "delta_percent": rel_delta_pct,
                    "direction": "better" if "reliability" in better_objectives else ("worse" if "reliability" in worse_objectives else "equal"),
                },
                "cost_per_task": {
                    "parent": p_cost,
                    "candidate": c_cost,
                    "delta": cost_delta,
                    "delta_percent": cost_delta_pct,
                    "direction": "better" if "cost_per_task" in better_objectives else ("worse" if "cost_per_task" in worse_objectives else "equal"),
                },
                "latency_per_task": {
                    "parent": p_lat,
                    "candidate": c_lat,
                    "delta": lat_delta,
                    "delta_percent": lat_delta_pct,
                    "direction": "better" if "latency_per_task" in better_objectives else ("worse" if "latency_per_task" in worse_objectives else "equal"),
                },
            },
        }

        # Dominance evaluation
        if len(worse_objectives) == 0 and len(better_objectives) > 0:
            # Case 1: Candidate dominates parent -> ACCEPT
            dominance_result = DominanceResult.CANDIDATE_DOMINATES
            accepted = True
            reason = (
                f"Candidate Pareto-dominates parent: strictly better on "
                f"{better_objectives} with no regression on any metric."
            )
        elif len(better_objectives) == 0 and len(worse_objectives) > 0:
            # Case 2: Parent dominates candidate -> REJECT
            dominance_result = DominanceResult.PARENT_DOMINATES
            accepted = False
            reason = (
                f"Parent dominates candidate: candidate regressed on "
                f"{worse_objectives} with no improvements."
            )
        elif len(better_objectives) == 0 and len(worse_objectives) == 0:
            # Case 4: Identical metrics -> REJECT
            dominance_result = DominanceResult.EQUAL
            accepted = False
            reason = "Candidate metrics are identical to parent within tolerance; no measurable improvement."
        else:
            # Case 3: Tradeoff / no dominance -> Configured policy
            dominance_result = DominanceResult.TRADEOFF
            accepted, reason = self._resolve_tradeoff(
                policy=active_policy,
                better_objectives=better_objectives,
                worse_objectives=worse_objectives,
                acc_delta=acc_delta,
                rel_delta=rel_delta,
                cost_delta_pct=cost_delta_pct,
                lat_delta_pct=lat_delta_pct,
                comp_delta=comp_delta,
                metrics_delta=metrics_delta,
            )

        return AcceptanceDecision(
            accepted=accepted,
            status="ACCEPTED" if accepted else "REJECTED",
            reason=reason,
            dominance_result=dominance_result,
            metrics_delta=metrics_delta,
            accuracy_delta=acc_delta,
            reliability_delta=rel_delta,
            cost_delta_percent=cost_delta_pct,
            latency_delta_percent=lat_delta_pct,
            composite_delta=comp_delta,
        )

    def _resolve_tradeoff(
        self,
        policy: TradeoffPolicy | str | Callable,
        better_objectives: list[str],
        worse_objectives: list[str],
        acc_delta: float,
        rel_delta: float,
        cost_delta_pct: float,
        lat_delta_pct: float,
        comp_delta: float,
        metrics_delta: dict[str, Any],
    ) -> tuple[bool, str]:
        if callable(policy):
            return policy(metrics_delta, DominanceResult.TRADEOFF)

        if policy == TradeoffPolicy.STRICT_PARETO or policy == "strict_pareto":
            return (
                False,
                f"Tradeoff rejected under strict Pareto policy: candidate improved on "
                f"{better_objectives} but regressed on {worse_objectives}."
            )

        # Configured threshold policy (TradeoffPolicy.COMPOSITE_THRESHOLD)
        # 1. Regressed accuracy is always rejected
        if "accuracy" in worse_objectives and acc_delta < -0.001:
            return (
                False,
                f"Tradeoff rejected: accuracy regressed by {acc_delta * 100:.1f}%."
            )

        # 2. Check for substantial cost and/or latency regressions without sufficient compensating improvement
        cost_exploded = cost_delta_pct > self.max_cost_regression_pct
        latency_exploded = lat_delta_pct > self.max_latency_regression_pct
        insufficient_compensation = (
            acc_delta < self.min_accuracy_gain_for_tradeoff or comp_delta < self.min_composite_gain
        )

        if (cost_exploded or latency_exploded) and insufficient_compensation:
            if cost_exploded and latency_exploded:
                return (
                    False,
                    "Candidate is dominated by parent because cost and latency regress substantially without sufficient compensating improvement."
                )
            elif cost_exploded:
                return (
                    False,
                    f"Candidate is dominated by parent because cost regressed substantially (+{cost_delta_pct:.1f}%) without sufficient compensating improvement."
                )
            else:
                return (
                    False,
                    f"Candidate is dominated by parent because latency regressed substantially (+{lat_delta_pct:.1f}%) without sufficient compensating improvement."
                )

        # 3. If regressions are within acceptable thresholds (or compensated), evaluate composite score
        if comp_delta >= self.min_composite_gain:
            return (
                True,
                f"Tradeoff accepted by configured policy: accuracy (+{acc_delta * 100:.1f}%) and "
                f"reliability (+{rel_delta * 100:.1f}%) gains outweigh minor regressions "
                f"(Cost: +{cost_delta_pct:.1f}%, Latency: +{lat_delta_pct:.1f}%, Composite: +{comp_delta:.4f})."
            )

        return (
            False,
            f"Tradeoff rejected by configured policy: composite score change ({comp_delta:+.4f}) "
            f"does not meet minimum improvement threshold (+{self.min_composite_gain:.4f})."
        )


def evaluate_acceptance(
    parent: GenerationMetrics | dict[str, Any] | Any,
    candidate: GenerationMetrics | dict[str, Any] | Any,
    tradeoff_policy: TradeoffPolicy | str | None = None,
    tolerance: float | dict[str, float] | None = None,
    **kwargs: Any,
) -> AcceptanceDecision:
    engine = AcceptanceEngine(tradeoff_policy=tradeoff_policy or TradeoffPolicy.COMPOSITE_THRESHOLD, **kwargs)
    return engine.evaluate_candidate(parent, candidate, tolerance=tolerance)
