"""
FORGE S7-C — Causal Evidence Links Tests

Proves explicit, unbroken causal traceability between:
1. Execution -> Failure -> Reflection -> Memory
2. Failure Cluster -> Mutation -> Candidate Generation -> Acceptance Decision

Each downstream artifact must be directly traceable to its upstream evidence
via deterministic IDs/references without fabrication.
"""
import uuid
import pytest
from sqlalchemy import select

from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import ExperimentModel, GenerationModel, MutationModel, ToolMemoryModel
from app.schemas.agent_spec import AgentSpec
from app.agents.state import AgentState
from app.agents.reflection import ToolReflectionEngine, ReflectedRule
from app.benchmarks.base import BenchmarkTask, TaskEvaluation
from app.evaluation.failure_analyzer import FailureAnalyzer, FailureAnalysis, FailureType
from app.evaluation.failure_clustering import FailureClusterer
from app.evaluation.metrics import ExecutionMetrics, GenerationMetrics
from app.evolution.mutation import Mutation
from app.evolution.mutation_generator import MutationGenerator
from app.evolution.acceptance import AcceptanceEngine, DominanceResult
from app.memory.tool_memory import ToolMemoryStore
from app.providers.mock import DeterministicMockProvider


# ─────────────────────────────────────────────────────────────
# 1. Execution -> Failure -> Reflection -> Memory
# ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_causal_link_execution_to_failure_to_reflection_to_memory():
    """
    Proves deterministic causal chain:
    failed execution -> failure record -> reflection record -> memory record.
    """
    await init_db()

    # 1. EXECUTION
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    state = AgentState(
        goal="Fetch task from Linear and update issue status",
        execution_id=execution_id,
        errors=["HTTP 422: team_id must be a valid 36-character team UUID (e.g. 550e8400-e29b-41d4-a716-446655440001)"],
        tool_results=[
            {
                "tool": "linear_api",
                "output": "Error: team_id must be a valid 36-character team UUID",
                "error": "HTTP 422: team_id must be a valid 36-character team UUID (e.g. 550e8400-e29b-41d4-a716-446655440001)",
                "success": False,
            }
        ],
    )
    state.transition_to("RUNNING")
    state.transition_to("FAILED")

    task = BenchmarkTask(
        id="task_linear_01",
        title="Linear Issue Sync",
        description="Sync tasks with Linear",
        category="third_party_automation",
        difficulty="MEDIUM",
        issue="Create an issue in Linear team CORE",
        expected_behavior="Issue created with valid team UUID",
    )
    evaluation = TaskEvaluation(
        task_id=task.id,
        passed=False,
        score=0.0,
        reason="Agent failed to pass valid team_id UUID to Linear API",
    )
    metrics = ExecutionMetrics(
        task_id=task.id,
        task_success=False,
        accuracy=0.0,
        reliability=0.0,
        cost_usd=0.001,
        latency_ms=250.0,
    )

    # 2. FAILURE RECORD
    provider = DeterministicMockProvider()
    analyzer = FailureAnalyzer(provider)
    failure = await analyzer.analyze(
        agent_spec=AgentSpec(name="test_agent", role="swe", system_prompt="Test", tools=["linear_api"]),
        state=state,
        task=task,
        evaluation=evaluation,
        metrics=metrics,
        execution_id=execution_id,
    )

    assert failure.id is not None
    assert failure.failure_id == failure.id
    assert failure.execution_id == execution_id, "Failure record must point to the execution that caused it"

    # 3. REFLECTION RECORD
    exp_id = f"exp_causal_{uuid.uuid4().hex[:8]}"
    store = ToolMemoryStore(experiment_id=exp_id)
    report = ToolReflectionEngine.reflect_on_execution(
        state=state,
        memory_store=store,
        execution_id=execution_id,
        failure_id=failure.id,
    )

    assert report.execution_id == execution_id
    assert report.failure_id == failure.id
    assert len(report.reflected_rules) >= 1
    reflected_rule = report.reflected_rules[0]

    assert reflected_rule.reflection_id == reflected_rule.id
    assert reflected_rule.execution_id == execution_id, "Reflected rule must link to execution_id"
    assert reflected_rule.failure_id == failure.id, "Reflected rule must link to failure_id"

    # 4. MEMORY RECORD
    assert len(report.entries) >= 1
    memory_entry = report.entries[0]

    assert memory_entry.memory_id == memory_entry.id
    assert memory_entry.reflection_id == reflected_rule.id, "Memory entry must link to reflection_id"
    assert memory_entry.failure_id == failure.id, "Memory entry must link to failure_id"
    assert memory_entry.execution_id == execution_id, "Memory entry must link to execution_id"

    # 5. PERSIST TO DATABASE AND VERIFY RELATIONAL INTEGRITY
    async with AsyncSessionLocal() as db:
        exp_model = ExperimentModel(
            id=exp_id,
            name="Causal Evidence Experiment",
            goal="Verify causal trace links",
            status="RUNNING",
        )
        db.add(exp_model)
        await db.commit()

        await store.sync_to_db(db)

        # Query database row
        db_mem = (
            await db.execute(
                select(ToolMemoryModel).where(ToolMemoryModel.id == memory_entry.id)
            )
        ).scalar_one()

        # Full backward trace verification:
        # DB Memory Record -> Reflection Record -> Failure Record -> Execution ID
        assert db_mem.id == memory_entry.id
        assert db_mem.reflection_id == reflected_rule.id
        assert db_mem.failure_id == failure.id
        assert db_mem.execution_id == execution_id

        # Traverse backward step-by-step
        upstream_reflection_id = db_mem.reflection_id
        assert upstream_reflection_id == reflected_rule.reflection_id

        upstream_failure_id = reflected_rule.failure_id
        assert upstream_failure_id == failure.failure_id

        origin_execution_id = failure.execution_id
        assert origin_execution_id == execution_id


# ─────────────────────────────────────────────────────────────
# 2. Failure Cluster -> Mutation -> Candidate Generation -> Acceptance Decision
# ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_causal_link_cluster_to_mutation_to_candidate_to_acceptance():
    """
    Proves deterministic causal chain:
    failure cluster -> mutation -> candidate generation -> acceptance/rejection decision.
    """
    await init_db()

    # 1. RAW FAILURES & FAILURE CLUSTER
    exec_1 = f"exec_fail_1_{uuid.uuid4().hex[:6]}"
    exec_2 = f"exec_fail_2_{uuid.uuid4().hex[:6]}"

    f1 = FailureAnalysis(
        task_id="task_swe_01",
        execution_id=exec_1,
        failure_type=FailureType.VERIFICATION_FAILURE,
        severity="HIGH",
        evidence=["Agent completed task without invoking 'test_runner'"],
        root_cause="Agent lacks mandatory verification gate before declaring task completion.",
    )
    f2 = FailureAnalysis(
        task_id="task_swe_02",
        execution_id=exec_2,
        failure_type=FailureType.VERIFICATION_FAILURE,
        severity="HIGH",
        evidence=["No test runner invocations found in trace"],
        root_cause="Agent declared completion without running automated verification suite.",
    )

    clusterer = FailureClusterer()
    cluster_report = clusterer.cluster([f1, f2])
    cluster = cluster_report.get_cluster(FailureType.VERIFICATION_FAILURE)

    assert cluster is not None
    assert cluster.id is not None
    assert cluster.cluster_id == cluster.id
    assert f1.id in cluster.failure_ids
    assert f2.id in cluster.failure_ids
    assert len(cluster.failure_ids) == 2

    # 2. MUTATION PROPOSAL
    parent_spec = AgentSpec(
        name="baseline_agent",
        role="software_engineer",
        system_prompt="Resolve issues accurately.",
        tools=["file_editor", "repository", "test_runner"],
    )
    mutator = MutationGenerator()
    candidate_spec, mutation = mutator.generate_mutation(
        current_spec=parent_spec,
        failure_report=cluster_report,
        failures=[f1, f2],
    )

    assert mutation.id is not None
    assert mutation.mutation_id == mutation.id
    assert mutation.failure_cluster_id == cluster.id, "Mutation must link to the failure cluster that motivated it"
    assert f1.id in mutation.failure_ids, "Mutation must link to the constituent failure IDs"
    assert f2.id in mutation.failure_ids

    # 3. CANDIDATE GENERATION
    exp_id = f"exp_lineage_{uuid.uuid4().hex[:8]}"
    parent_gen_id = f"gen_parent_{uuid.uuid4().hex[:8]}"
    cand_gen_id = f"gen_cand_{uuid.uuid4().hex[:8]}"

    candidate_gen = GenerationModel(
        id=cand_gen_id,
        experiment_id=exp_id,
        parent_generation_id=parent_gen_id,
        generation_number=1,
        agent_spec=candidate_spec.model_dump(),
        mutation_id=mutation.id,
        status="RUNNING",
    )
    assert candidate_gen.mutation_id == mutation.id, "Candidate generation must link to mutation_id"
    assert candidate_gen.parent_generation_id == parent_gen_id

    # 4. ACCEPTANCE / REJECTION DECISION
    acceptance = AcceptanceEngine()
    parent_metrics = GenerationMetrics(
        generation_number=0,
        total_tasks=2,
        successful_tasks=0,
        accuracy=0.0,
        reliability=0.4,
        total_cost_usd=0.01,
        avg_cost_per_task=0.005,
        avg_latency_ms=1500.0,
        composite_score=0.15,
    )
    candidate_metrics = GenerationMetrics(
        generation_number=1,
        total_tasks=2,
        successful_tasks=2,
        accuracy=1.0,
        reliability=0.95,
        total_cost_usd=0.011,
        avg_cost_per_task=0.0055,
        avg_latency_ms=1600.0,
        composite_score=0.92,
    )

    decision = acceptance.evaluate_candidate(
        parent=parent_metrics,
        candidate=candidate_metrics,
        candidate_generation_id=candidate_gen.id,
        parent_generation_id=parent_gen_id,
        mutation_id=mutation.id,
    )

    assert decision.id is not None
    assert decision.decision_id == decision.id
    assert decision.candidate_generation_id == candidate_gen.id, "Decision must record candidate_generation_id"
    assert decision.parent_generation_id == parent_gen_id, "Decision must record parent_generation_id"
    assert decision.mutation_id == mutation.id, "Decision must record mutation_id"
    assert decision.accepted is True
    assert decision.status == "ACCEPTED"

    # Persist decision to candidate generation model
    candidate_gen.decision_id = decision.id
    candidate_gen.status = decision.status
    candidate_gen.metrics = {
        **candidate_metrics.model_dump(),
        "acceptance_decision": {
            "decision_id": decision.id,
            "candidate_generation_id": candidate_gen.id,
            "parent_generation_id": parent_gen_id,
            "mutation_id": mutation.id,
            "accepted": decision.accepted,
            "status": decision.status,
            "reason": decision.reason,
            "dominance_result": decision.dominance_result.value,
            "metrics_delta": decision.metrics_delta,
        },
    }

    # 5. PERSIST TO DATABASE AND VERIFY RELATIONAL INTEGRITY
    async with AsyncSessionLocal() as db:
        exp_model = ExperimentModel(
            id=exp_id,
            name="Causal Lineage Experiment",
            goal="Verify multi-step lineage causal links",
            status="COMPLETED",
        )
        db.add(exp_model)
        await db.commit()

        # Persist parent generation, mutation, and candidate generation
        parent_gen = GenerationModel(
            id=parent_gen_id,
            experiment_id=exp_id,
            generation_number=0,
            agent_spec=parent_spec.model_dump(),
            status="COMPLETED",
            metrics=parent_metrics.model_dump(),
        )
        db.add(parent_gen)

        db_mutation = MutationModel(
            id=mutation.id,
            experiment_id=exp_id,
            generation_id=parent_gen_id,
            mutation_type=mutation.mutation_type.value,
            target=mutation.target,
            before_json=mutation.before if isinstance(mutation.before, dict) else {"val": mutation.before},
            after_json=mutation.after if isinstance(mutation.after, dict) else {"val": mutation.after},
            reason=mutation.reason,
            observed_failure=mutation.observed_failure,
            expected_effect=mutation.expected_effect,
            failure_cluster_id=mutation.failure_cluster_id,
            failure_ids=mutation.failure_ids,
        )
        db.add(db_mutation)
        db.add(candidate_gen)
        await db.commit()

        # Query back candidate and mutation from DB
        db_cand = (await db.execute(select(GenerationModel).where(GenerationModel.id == cand_gen_id))).scalar_one()
        db_mut = (await db.execute(select(MutationModel).where(MutationModel.id == mutation.id))).scalar_one()

        # 6. FULL BACKWARD TRACE VERIFICATION:
        # Decision -> Candidate Generation -> Mutation -> Failure Cluster -> Failures -> Executions
        # Step A: From decision to candidate generation
        assert decision.candidate_generation_id == db_cand.id
        assert db_cand.decision_id == decision.id
        assert db_cand.metrics["acceptance_decision"]["decision_id"] == decision.id

        # Step B: From candidate generation to mutation
        assert db_cand.mutation_id == db_mut.id

        # Step C: From mutation to failure cluster
        assert db_mut.failure_cluster_id == cluster.id

        # Step D: From failure cluster to constituent raw failures
        assert f1.id in cluster.failure_ids
        assert f2.id in cluster.failure_ids
        assert f1.id in db_mut.failure_ids
        assert f2.id in db_mut.failure_ids

        # Step E: From raw failures to underlying execution traces
        assert f1.execution_id == exec_1
        assert f2.execution_id == exec_2
