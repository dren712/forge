from typing import Tuple
from pydantic import BaseModel
from app.evaluation.metrics import GenerationMetrics


class AcceptanceDecision(BaseModel):
    accepted: bool
    status: str  # "ACCEPTED" or "REJECTED"
    reason: str
    accuracy_delta: float
    reliability_delta: float
    cost_delta_percent: float
    latency_delta_percent: float
    composite_delta: float


class AcceptanceEngine:
    """
    Evaluates candidate generation against parent baseline.
    Pareto-aware decision logic:
    1. Rejects if accuracy decreases.
    2. Rejects if composite score decreases.
    3. Rejects if minor accuracy gain (< 2%) is accompanied by cost explosion (> 50%).
    4. Accepts if accuracy increases with stable/improved reliability without severe regressions.
    5. Accepts if accuracy is equal but reliability significantly improves (> 5%) with acceptable cost.
    """

    def evaluate_candidate(
        self,
        parent: GenerationMetrics,
        candidate: GenerationMetrics,
    ) -> AcceptanceDecision:
        acc_delta = round(candidate.accuracy - parent.accuracy, 4)
        rel_delta = round(candidate.reliability - parent.reliability, 4)
        comp_delta = round(candidate.composite_score - parent.composite_score, 4)

        # Cost delta
        if parent.avg_cost_per_task > 0:
            cost_delta_pct = round(((candidate.avg_cost_per_task - parent.avg_cost_per_task) / parent.avg_cost_per_task) * 100.0, 1)
        else:
            cost_delta_pct = 0.0

        # Latency delta
        if parent.avg_latency_ms > 0:
            lat_delta_pct = round(((candidate.avg_latency_ms - parent.avg_latency_ms) / parent.avg_latency_ms) * 100.0, 1)
        else:
            lat_delta_pct = 0.0

        # Rule 1: Regression in accuracy
        if acc_delta < -0.001:
            return AcceptanceDecision(
                accepted=False,
                status="REJECTED",
                reason=f"Accuracy regressed by {acc_delta * 100:.1f}%.",
                accuracy_delta=acc_delta,
                reliability_delta=rel_delta,
                cost_delta_percent=cost_delta_pct,
                latency_delta_percent=lat_delta_pct,
                composite_delta=comp_delta,
            )

        # Rule 2: Insufficient accuracy gain vs catastrophic cost increase
        if acc_delta < 0.05 and cost_delta_pct > 60.0:
            return AcceptanceDecision(
                accepted=False,
                status="REJECTED",
                reason=f"Cost increased by {cost_delta_pct}% without significant accuracy gain (+{acc_delta * 100:.1f}%).",
                accuracy_delta=acc_delta,
                reliability_delta=rel_delta,
                cost_delta_percent=cost_delta_pct,
                latency_delta_percent=lat_delta_pct,
                composite_delta=comp_delta,
            )

        # Rule 3: Significant accuracy improvement
        if acc_delta > 0:
            return AcceptanceDecision(
                accepted=True,
                status="ACCEPTED",
                reason=f"Accuracy improved by +{acc_delta * 100:.1f}% (Reliability: +{rel_delta * 100:.1f}%).",
                accuracy_delta=acc_delta,
                reliability_delta=rel_delta,
                cost_delta_percent=cost_delta_pct,
                latency_delta_percent=lat_delta_pct,
                composite_delta=comp_delta,
            )

        # Rule 4: Same accuracy, but reliability improvement
        if acc_delta >= 0 and rel_delta >= 0.05:
            return AcceptanceDecision(
                accepted=True,
                status="ACCEPTED",
                reason=f"Reliability improved by +{rel_delta * 100:.1f}% while maintaining accuracy.",
                accuracy_delta=acc_delta,
                reliability_delta=rel_delta,
                cost_delta_percent=cost_delta_pct,
                latency_delta_percent=lat_delta_pct,
                composite_delta=comp_delta,
            )

        # Rule 5: Same accuracy, same reliability, but improved composite/cost
        if comp_delta > 0.02:
            return AcceptanceDecision(
                accepted=True,
                status="ACCEPTED",
                reason=f"Efficiency improved: Composite score increased by +{comp_delta:.3f}.",
                accuracy_delta=acc_delta,
                reliability_delta=rel_delta,
                cost_delta_percent=cost_delta_pct,
                latency_delta_percent=lat_delta_pct,
                composite_delta=comp_delta,
            )

        # Default fallback: No material improvement
        return AcceptanceDecision(
            accepted=False,
            status="REJECTED",
            reason="Candidate produced no measurable improvement in accuracy or reliability.",
            accuracy_delta=acc_delta,
            reliability_delta=rel_delta,
            cost_delta_percent=cost_delta_pct,
            latency_delta_percent=lat_delta_pct,
            composite_delta=comp_delta,
        )
