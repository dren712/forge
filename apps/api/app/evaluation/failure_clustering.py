from enum import Enum
from typing import Any, Literal
import uuid
from pydantic import BaseModel, Field

from app.evaluation.failure_analyzer import FailureType, FailureAnalysis
from app.evaluation.metrics import ExecutionMetrics


SEVERITY_ORDER = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

VALID_TAXONOMY_CATEGORIES = {t.value for t in FailureType}


class FailureCluster(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    count: int
    affected_tasks: list[str] = Field(default_factory=list)
    percentage: float = 0.0
    representative_evidence: list[str] = Field(default_factory=list)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    root_causes: list[str] = Field(default_factory=list)
    failure_ids: list[str] = Field(default_factory=list)

    @property
    def cluster_id(self) -> str:
        return self.id


class FailureClusterReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_failures: int = 0
    total_tasks_evaluated: int = 0
    clusters: list[FailureCluster] = Field(default_factory=list)
    failure_ids: list[str] = Field(default_factory=list)

    @property
    def report_id(self) -> str:
        return self.id

    def get_cluster(self, category: str | FailureType) -> FailureCluster | None:
        cat_str = category.value if isinstance(category, Enum) else str(category)
        for cluster in self.clusters:
            if cluster.category == cat_str:
                return cluster
        return None

    def __getitem__(self, category: str | FailureType) -> FailureCluster:
        cluster = self.get_cluster(category)
        if cluster is None:
            raise KeyError(f"No failure cluster found for category: {category}")
        return cluster

    def to_formatted_report(self) -> str:
        lines = [
            "# FORGE Failure Aggregation & Clustering Report",
            f"Total Failures: {self.total_failures} | Tasks Evaluated: {self.total_tasks_evaluated}",
            "",
            "| Category | Count | Percentage | Severity | Affected Tasks |",
            "|---|---|---|---|---|",
        ]
        for c in self.clusters:
            tasks_preview = ", ".join(c.affected_tasks[:4])
            if len(c.affected_tasks) > 4:
                tasks_preview += f" (+{len(c.affected_tasks) - 4} more)"
            lines.append(f"| {c.category} | {c.count} | {c.percentage:.1f}% | {c.severity} | {tasks_preview} |")

        lines.append("")
        lines.append("## Representative Evidence")
        for c in self.clusters:
            lines.append(f"### {c.category} ({c.count} failures, Severity: {c.severity})")
            if c.representative_evidence:
                for ev in c.representative_evidence:
                    lines.append(f"- {ev}")
            else:
                lines.append("- (No evidence recorded)")
        return "\n".join(lines)


class FailureClusterer:
    """
    Aggregates and clusters task-level execution results and failure analyses.
    Groups failures into the established FORGE failure taxonomy without fabricating evidence.
    """

    def cluster(
        self,
        failures: list[FailureAnalysis | dict[str, Any]],
        task_results: list[ExecutionMetrics | dict[str, Any]] | None = None,
    ) -> FailureClusterReport:
        if not failures:
            total_tasks = len(task_results) if task_results else 0
            return FailureClusterReport(
                total_failures=0,
                total_tasks_evaluated=total_tasks,
                clusters=[],
            )

        # 1. Normalize failures
        normalized_failures: list[dict[str, Any]] = []
        for f in failures:
            if isinstance(f, FailureAnalysis):
                f_type_str = f.failure_type.value if isinstance(f.failure_type, Enum) else str(f.failure_type)
                f_id = getattr(f, "id", None) or getattr(f, "failure_id", None) or str(uuid.uuid4())
                normalized_failures.append({
                    "id": str(f_id),
                    "task_id": f.task_id,
                    "failure_type": f_type_str,
                    "severity": f.severity,
                    "evidence": list(f.evidence),
                    "root_cause": f.root_cause,
                })
            elif isinstance(f, dict):
                f_type = f.get("failure_type", f.get("category", "REASONING_FAILURE"))
                if isinstance(f_type, Enum):
                    f_type = f_type.value
                evidence_list = f.get("evidence", [])
                if isinstance(evidence_list, str):
                    evidence_list = [evidence_list]
                f_id = f.get("id", f.get("failure_id", str(uuid.uuid4())))
                normalized_failures.append({
                    "id": str(f_id),
                    "task_id": str(f.get("task_id", "")),
                    "failure_type": str(f_type),
                    "severity": str(f.get("severity", "HIGH")).upper(),
                    "evidence": list(evidence_list),
                    "root_cause": str(f.get("root_cause", "")),
                })

        # 2. Correlate with task_results if present
        total_tasks = len(task_results) if task_results else len({f["task_id"] for f in normalized_failures if f["task_id"]})
        total_failures = len(normalized_failures)

        # 3. Group by failure category
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in normalized_failures:
            cat = item["failure_type"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(item)

        clusters: list[FailureCluster] = []
        for cat, items in grouped.items():
            count = len(items)

            # Unique affected tasks in order of appearance
            affected_tasks: list[str] = []
            seen_tasks = set()
            for item in items:
                tid = item["task_id"]
                if tid and tid not in seen_tasks:
                    seen_tasks.add(tid)
                    affected_tasks.append(tid)

            # Extract grounded evidence (strictly unhallucinated)
            representative_evidence: list[str] = []
            seen_evidence = set()
            for item in items:
                for ev in item["evidence"]:
                    ev_str = str(ev).strip()
                    if ev_str and ev_str not in seen_evidence:
                        seen_evidence.add(ev_str)
                        representative_evidence.append(ev_str)

            # Extract grounded root causes
            root_causes: list[str] = []
            seen_causes = set()
            for item in items:
                rc_str = item.get("root_cause", "").strip()
                if rc_str and rc_str not in seen_causes:
                    seen_causes.add(rc_str)
                    root_causes.append(rc_str)

            # Determine aggregate severity (highest among constituent failures)
            severities = [item.get("severity", "HIGH") for item in items]
            max_sev = max(severities, key=lambda s: SEVERITY_ORDER.get(s, 0)) if severities else "HIGH"
            if max_sev not in SEVERITY_ORDER:
                max_sev = "HIGH"

            percentage = round((count / total_failures) * 100.0, 2) if total_failures > 0 else 0.0
            cluster_f_ids = [item["id"] for item in items if item.get("id")]

            clusters.append(FailureCluster(
                category=cat,
                count=count,
                affected_tasks=affected_tasks,
                percentage=percentage,
                representative_evidence=representative_evidence,
                severity=max_sev,
                root_causes=root_causes,
                failure_ids=cluster_f_ids,
            ))

        # Sort clusters: primary by count descending, secondary by severity descending
        clusters.sort(key=lambda c: (c.count, SEVERITY_ORDER.get(c.severity, 0)), reverse=True)

        all_failure_ids = [item["id"] for item in normalized_failures if item.get("id")]
        return FailureClusterReport(
            total_failures=total_failures,
            total_tasks_evaluated=total_tasks,
            clusters=clusters,
            failure_ids=all_failure_ids,
        )


def cluster_failures(
    failures: list[FailureAnalysis | dict[str, Any]],
    task_results: list[ExecutionMetrics | dict[str, Any]] | None = None,
) -> FailureClusterReport:
    """Convenience functional interface for failure clustering."""
    return FailureClusterer().cluster(failures, task_results)
