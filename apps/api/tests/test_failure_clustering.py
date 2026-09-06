import pytest
from app.evaluation.failure_analyzer import FailureType, FailureAnalysis
from app.evaluation.failure_clustering import (
    FailureClusterer,
    FailureClusterReport,
    cluster_failures,
)
from app.evaluation.metrics import ExecutionMetrics


def test_failure_clustering_verification_and_planning_counts():
    """
    Validates FORGE S6-C deterministic requirement:
    4 verification failures
    3 planning failures
    actually produce those exact counts, percentages, affected tasks, and severity.
    """
    # Deterministic fixtures
    verification_failures = [
        FailureAnalysis(
            task_id="task_se_001",
            failure_type=FailureType.VERIFICATION_FAILURE,
            severity="HIGH",
            evidence=["Premature exit without running test_runner", "Unit tests unverified"],
            root_cause="Agent declared completion before verifying fixes with tests.",
        ),
        FailureAnalysis(
            task_id="task_se_002",
            failure_type=FailureType.VERIFICATION_FAILURE,
            severity="CRITICAL",
            evidence=["No test assertions executed before completion declaration"],
            root_cause="Missing test assertion gate in verifier.",
        ),
        FailureAnalysis(
            task_id="task_se_003",
            failure_type=FailureType.VERIFICATION_FAILURE,
            severity="HIGH",
            evidence=["Verifier mandatory_tests check failed: exit code 1"],
            root_cause="Tests failed during automated verification gate.",
        ),
        FailureAnalysis(
            task_id="task_se_004",
            failure_type=FailureType.VERIFICATION_FAILURE,
            severity="MEDIUM",
            evidence=["Agent claimed bug fixed without executing test suite"],
            root_cause="Absence of test execution before task exit.",
        ),
    ]

    planning_failures = [
        FailureAnalysis(
            task_id="task_se_005",
            failure_type=FailureType.PLANNING_FAILURE,
            severity="HIGH",
            evidence=["Agent looped across same directory 15 times without goal progress"],
            root_cause="Unstructured goal decomposition caused cyclic exploration.",
        ),
        FailureAnalysis(
            task_id="task_se_006",
            failure_type=FailureType.PLANNING_FAILURE,
            severity="MEDIUM",
            evidence=["Stuck in infinite plan-execute cycle on invalid file path"],
            root_cause="Planner failed to adjust file search trajectory.",
        ),
        FailureAnalysis(
            task_id="task_se_007",
            failure_type=FailureType.PLANNING_FAILURE,
            severity="HIGH",
            evidence=["Failure to decompose task into steps; repeated invalid tool call"],
            root_cause="Plan lacked prerequisite step ordering.",
        ),
    ]

    all_failures = verification_failures + planning_failures
    task_metrics = [
        ExecutionMetrics(
            task_id=f"task_se_00{i+1}",
            task_success=False,
            accuracy=0.0,
            reliability=0.2,
            cost_usd=0.01,
            latency_ms=1200.0,
        )
        for i in range(7)
    ]

    clusterer = FailureClusterer()
    report: FailureClusterReport = clusterer.cluster(all_failures, task_metrics)

    # Core count assertions required by S6-C
    assert report.total_failures == 7
    assert report.total_tasks_evaluated == 7
    assert len(report.clusters) == 2

    # Verification failures cluster verification
    verif_cluster = report["VERIFICATION_FAILURE"]
    assert verif_cluster.category == "VERIFICATION_FAILURE"
    assert verif_cluster.count == 4, "Must produce exactly 4 verification failures"
    assert verif_cluster.affected_tasks == ["task_se_001", "task_se_002", "task_se_003", "task_se_004"]
    assert verif_cluster.percentage == 57.14  # 4 / 7 * 100 = 57.1428...
    assert verif_cluster.severity == "CRITICAL", "Maximum severity (CRITICAL from task_se_002) must propagate"
    assert "Premature exit without running test_runner" in verif_cluster.representative_evidence
    assert "No test assertions executed before completion declaration" in verif_cluster.representative_evidence

    # Planning failures cluster verification
    plan_cluster = report["PLANNING_FAILURE"]
    assert plan_cluster.category == "PLANNING_FAILURE"
    assert plan_cluster.count == 3, "Must produce exactly 3 planning failures"
    assert plan_cluster.affected_tasks == ["task_se_005", "task_se_006", "task_se_007"]
    assert plan_cluster.percentage == 42.86  # 3 / 7 * 100 = 42.8571...
    assert plan_cluster.severity == "HIGH", "Maximum severity (HIGH) must propagate"
    assert "Agent looped across same directory 15 times without goal progress" in plan_cluster.representative_evidence


def test_evidence_grounding_no_invented_causes():
    """
    Verifies that representative evidence and root causes are grounded strictly in execution trace data
    and no causes or evidence strings are hallucinated or fabricated.
    """
    known_evidence_1 = "Tool 'file_editor' failed: FileNotFoundError: /src/app.py"
    known_evidence_2 = "Tool 'shell' returned non-zero exit code 127"
    known_root_cause = "Agent assumed target file was located in /src instead of /lib."

    analysis = FailureAnalysis(
        task_id="task_tool_01",
        failure_type=FailureType.TOOL_EXECUTION_FAILURE,
        severity="HIGH",
        evidence=[known_evidence_1, known_evidence_2],
        root_cause=known_root_cause,
    )

    report = cluster_failures([analysis])
    cluster = report["TOOL_EXECUTION_FAILURE"]

    assert cluster.count == 1
    assert cluster.representative_evidence == [known_evidence_1, known_evidence_2]
    assert cluster.root_causes == [known_root_cause]

    # Verify no fabricated elements
    for ev in cluster.representative_evidence:
        assert ev in [known_evidence_1, known_evidence_2]


def test_full_taxonomy_coverage():
    """
    Validates that every category in the FORGE failure taxonomy is clustered properly.
    """
    taxonomy_types = [
        FailureType.REASONING_FAILURE,
        FailureType.PLANNING_FAILURE,
        FailureType.TOOL_SELECTION_FAILURE,
        FailureType.TOOL_EXECUTION_FAILURE,
        FailureType.CONTEXT_FAILURE,
        FailureType.MEMORY_FAILURE,
        FailureType.VERIFICATION_FAILURE,
        FailureType.RECOVERY_FAILURE,
        FailureType.TASK_MISINTERPRETATION,
        FailureType.TIMEOUT,
        FailureType.COST_LIMIT,
    ]

    analyses = [
        FailureAnalysis(
            task_id=f"task_{t.value.lower()}",
            failure_type=t,
            severity="MEDIUM",
            evidence=[f"Evidence for {t.value}"],
            root_cause=f"Root cause for {t.value}",
        )
        for t in taxonomy_types
    ]

    report = cluster_failures(analyses)
    assert report.total_failures == len(taxonomy_types)
    assert len(report.clusters) == len(taxonomy_types)

    for t in taxonomy_types:
        cluster = report.get_cluster(t)
        assert cluster is not None
        assert cluster.count == 1
        assert cluster.category == t.value


def test_empty_and_edge_cases():
    """
    Validates clustering with empty failure sets, dictionary inputs, and multiple failures on same task.
    """
    # Empty
    empty_report = cluster_failures([])
    assert empty_report.total_failures == 0
    assert len(empty_report.clusters) == 0

    # Multiple failures on the same task
    repeated_failures = [
        FailureAnalysis(
            task_id="shared_task",
            failure_type=FailureType.TIMEOUT,
            severity="HIGH",
            evidence=["Timed out after 300s"],
            root_cause="Execution exceeded time limit",
        ),
        FailureAnalysis(
            task_id="shared_task",
            failure_type=FailureType.TIMEOUT,
            severity="CRITICAL",
            evidence=["Hard timeout threshold hit"],
            root_cause="Infinite loop in runtime step",
        ),
    ]
    report = cluster_failures(repeated_failures)
    timeout_cluster = report["TIMEOUT"]
    assert timeout_cluster.count == 2
    assert timeout_cluster.affected_tasks == ["shared_task"], "Unique affected tasks list"
    assert timeout_cluster.severity == "CRITICAL"
    assert len(timeout_cluster.representative_evidence) == 2

    # Formatted markdown report rendering
    md = report.to_formatted_report()
    assert "# FORGE Failure Aggregation & Clustering Report" in md
    assert "TIMEOUT" in md
