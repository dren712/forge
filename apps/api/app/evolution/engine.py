import uuid
import time
import asyncio
from pathlib import Path
from typing import Callable, Any
from app.core.config import settings
from app.schemas.agent_spec import AgentSpec
from app.benchmarks.base import Benchmark, BenchmarkTask
from app.agents.runtime import AgentRuntime
from app.tools.registry import default_registry
from app.providers.base import LLMProvider
from app.evaluation.metrics import ExecutionMetrics, GenerationMetrics
from app.evaluation.scoring import compute_cost, compute_reliability, aggregate_generation_metrics
from app.evaluation.failure_analyzer import FailureAnalyzer, FailureAnalysis
from app.evaluation.failure_clustering import FailureClusterer, FailureClusterReport
from app.evolution.mutation import Mutation
from app.evolution.mutation_generator import MutationGenerator
from app.evolution.acceptance import AcceptanceEngine, AcceptanceDecision
from app.memory.tool_memory import ToolMemoryStore
from app.tracing.recorder import EventRecorder
from app.tracing.events import EventType


class EvolutionEngine:
    def __init__(
        self,
        experiment_id: str,
        benchmark: Benchmark,
        provider: LLMProvider,
        workspaces_root: Path | None = None,
        recorder: EventRecorder | None = None,
        memory_store: ToolMemoryStore | None = None,
    ):
        self.experiment_id = experiment_id
        self.benchmark = benchmark
        self.provider = provider
        self.workspaces_root = workspaces_root or (settings.root_dir / "workspaces" / experiment_id)
        self.workspaces_root.mkdir(parents=True, exist_ok=True)
        self.recorder = recorder or EventRecorder(experiment_id)
        self.memory_store = memory_store or ToolMemoryStore(experiment_id)
        self.analyzer = FailureAnalyzer(provider)
        self.clusterer = FailureClusterer()
        self.last_failure_report: FailureClusterReport | None = None
        self.mutator = MutationGenerator(provider)
        self.acceptance = AcceptanceEngine()

    async def run_generation(
        self,
        generation_id: str,
        generation_number: int,
        spec: AgentSpec,
        task_subset: list[BenchmarkTask] | None = None,
        on_event: Callable[[str], Any] | None = None,
    ) -> tuple[GenerationMetrics, list[ExecutionMetrics], list[FailureAnalysis]]:
        """Executes a generation across benchmark tasks, captures metrics, and analyzes failures."""
        tasks = task_subset or self.benchmark.list_tasks()
        task_metrics: list[ExecutionMetrics] = []
        failures: list[FailureAnalysis] = []
        runtime = AgentRuntime(
            spec=spec,
            provider=self.provider,
            tool_registry=default_registry,
            recorder=self.recorder,
            memory_store=self.memory_store,
        )

        await self.recorder.emit(
            EventType.GENERATION_CREATED,
            {
                "generation_id": generation_id,
                "generation_number": generation_number,
                "spec": spec.model_dump(),
                "task_count": len(tasks),
            },
            generation_id=generation_id,
        )

        for task in tasks:
            execution_id = str(uuid.uuid4())
            task_workspace = self.workspaces_root / f"gen_{generation_number}" / task.id
            if hasattr(self.benchmark, "reset_task"):
                await self.benchmark.reset_task(task, task_workspace)
            await self.benchmark.setup_task(task, task_workspace)

            start_t = time.perf_counter()
            # Run agent on task
            agent_state = await runtime.run(
                goal=f"Issue: {task.issue}\nExpected: {task.expected_behavior}\nConstraints: {', '.join(task.constraints)}",
                workspace=task_workspace,
                generation_id=generation_id,
                execution_id=execution_id,
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            # Evaluate task
            await self.recorder.emit(
                EventType.EVALUATION_STARTED,
                {"task_id": task.id, "execution_id": execution_id},
                generation_id=generation_id,
                execution_id=execution_id,
            )

            evaluation = await self.benchmark.evaluate_task(agent_state, task, task_workspace)

            # Metrics
            cost = compute_cost(agent_state.input_tokens, agent_state.output_tokens)
            rel = compute_reliability(agent_state, evaluation)
            tool_errors = len([tr for tr in agent_state.tool_results if not tr.get("success", False)])

            metric = ExecutionMetrics(
                task_id=task.id,
                execution_id=execution_id,
                task_success=evaluation.passed,
                accuracy=1.0 if evaluation.passed else 0.0,
                reliability=rel,
                cost_usd=cost,
                latency_ms=elapsed_ms,
                input_tokens=agent_state.input_tokens,
                output_tokens=agent_state.output_tokens,
                total_tokens=agent_state.total_tokens,
                model_calls=agent_state.model_call_count,
                tool_calls=agent_state.tool_call_count,
                tool_errors=tool_errors,
                verification_passed=agent_state.verification_passed,
                clean_exit=(agent_state.status == "COMPLETED"),
                recovered_from_error=(tool_errors > 0 and evaluation.passed),
            )
            task_metrics.append(metric)

            await self.recorder.emit(
                EventType.EVALUATION_COMPLETED,
                {
                    "task_id": task.id,
                    "passed": evaluation.passed,
                    "accuracy": metric.accuracy,
                    "reliability": metric.reliability,
                    "cost_usd": metric.cost_usd,
                    "reason": evaluation.reason,
                },
                generation_id=generation_id,
                execution_id=execution_id,
            )

            # Failure diagnosis if not passed
            if not evaluation.passed:
                analysis = await self.analyzer.analyze(spec, agent_state, task, evaluation, metric, execution_id=execution_id)
                failures.append(analysis)
                await self.recorder.emit(
                    EventType.FAILURE_DETECTED,
                    {
                        "failure_id": analysis.id,
                        "task_id": task.id,
                        "execution_id": execution_id,
                        "failure_type": analysis.failure_type.value,
                        "root_cause": analysis.root_cause,
                        "evidence": analysis.evidence,
                    },
                    generation_id=generation_id,
                    execution_id=execution_id,
                )

        # Aggregate generation level metrics and cluster failures
        self.last_failure_report = self.clusterer.cluster(failures, task_metrics)
        failure_counts = {c.category: c.count for c in self.last_failure_report.clusters}
        gen_metrics = aggregate_generation_metrics(generation_number, task_metrics, failure_counts)

        return gen_metrics, task_metrics, failures

    async def evaluate_candidate(
        self,
        current_generation_id: str,
        current_generation_number: int,
        current_spec: AgentSpec,
        current_metrics: GenerationMetrics,
        failures: list[FailureAnalysis] | None = None,
        task_subset: list[BenchmarkTask] | None = None,
    ) -> tuple[AgentSpec, Mutation, GenerationMetrics, list[ExecutionMetrics], list[FailureAnalysis]]:
        """
        FORGE S6-F Candidate Evaluation:
        current generation -> mutation -> candidate AgentSpec -> benchmark -> candidate metrics.
        Runs candidate against the SAME benchmark version and task set as parent.
        Resets benchmark state before execution.
        Preserves parent generation and metrics untouched.
        Does NOT perform acceptance/rejection.
        """
        # 1. Propose & validate mutation
        candidate_spec, mutation = self.mutator.propose_mutation(
            current_spec=current_spec,
            failures=failures,
            generation_number=current_generation_number + 1,
            benchmark_metrics=current_metrics,
        )

        await self.recorder.emit(
            EventType.MUTATION_PROPOSED,
            {
                "mutation_id": mutation.id,
                "mutation_type": mutation.mutation_type.value,
                "target": mutation.target,
                "reason": mutation.reason,
                "expected_effect": mutation.expected_effect,
            },
            generation_id=current_generation_id,
        )

        candidate_gen_id = str(uuid.uuid4())
        candidate_gen_number = current_generation_number + 1

        # 2. Run candidate generation against the same tasks
        candidate_metrics, candidate_task_metrics, candidate_failures = await self.run_generation(
            generation_id=candidate_gen_id,
            generation_number=candidate_gen_number,
            spec=candidate_spec,
            task_subset=task_subset,
        )

        return candidate_spec, mutation, candidate_metrics, candidate_task_metrics, candidate_failures

    async def evolve_step(
        self,
        current_generation_id: str,
        current_generation_number: int,
        current_spec: AgentSpec,
        current_metrics: GenerationMetrics,
        failures: list[FailureAnalysis],
        task_subset: list[BenchmarkTask] | None = None,
    ) -> tuple[AgentSpec, Mutation, GenerationMetrics, AcceptanceDecision]:
        """
        Takes an evaluated generation and executes the full cycle:
        mutation -> candidate -> benchmark -> evaluate -> accept/reject
        """
        candidate_spec, mutation, candidate_metrics, candidate_task_metrics, candidate_failures = await self.evaluate_candidate(
            current_generation_id=current_generation_id,
            current_generation_number=current_generation_number,
            current_spec=current_spec,
            current_metrics=current_metrics,
            failures=failures,
            task_subset=task_subset,
        )

        candidate_gen_id = str(uuid.uuid4())
        candidate_gen_number = current_generation_number + 1

        # 3. Acceptance decision
        decision = self.acceptance.evaluate_candidate(current_metrics, candidate_metrics)
        if not decision.candidate_generation_id:
            decision.candidate_generation_id = candidate_gen_id
        if not decision.parent_generation_id:
            decision.parent_generation_id = current_generation_id
        if not decision.mutation_id:
            decision.mutation_id = mutation.id

        decision_event = EventType.GENERATION_ACCEPTED if decision.accepted else EventType.GENERATION_REJECTED
        await self.recorder.emit(
            decision_event,
            {
                "decision_id": decision.id,
                "candidate_generation_id": candidate_gen_id,
                "candidate_generation_number": candidate_gen_number,
                "parent_generation_id": current_generation_id,
                "mutation_id": mutation.id,
                "status": decision.status,
                "reason": decision.reason,
                "accuracy_delta": decision.accuracy_delta,
                "reliability_delta": decision.reliability_delta,
                "cost_delta_percent": decision.cost_delta_percent,
            },
            generation_id=candidate_gen_id,
        )

        return candidate_spec, mutation, candidate_metrics, decision

    async def run_evolution_loop(
        self,
        initial_spec: AgentSpec,
        max_generations: int = 5,
        max_consecutive_rejections: int = 3,
        task_subset: list[BenchmarkTask] | None = None,
        target_accuracy: float | None = None,
        stop_condition: Callable[[GenerationMetrics], bool] | None = None,
    ) -> list[tuple[AgentSpec, GenerationMetrics, AcceptanceDecision | None]]:
        """
        FORGE S6-J Multi-Generation Evolution in Engine:
        Runs G0 -> G1 -> G2 -> ...
        Yields history of evaluated generations with acceptance decisions.
        """
        history: list[tuple[AgentSpec, GenerationMetrics, AcceptanceDecision | None]] = []

        # 1. Run G0
        g0_id = str(uuid.uuid4())
        g0_metrics, g0_task_metrics, g0_failures = await self.run_generation(
            generation_id=g0_id,
            generation_number=0,
            spec=initial_spec,
            task_subset=task_subset,
        )
        history.append((initial_spec, g0_metrics, None))

        current_spec = initial_spec
        current_metrics = g0_metrics
        current_gen_id = g0_id
        current_gen_number = 0
        current_failures = g0_failures

        consecutive_rejections = 0

        # Check initial stop condition
        if target_accuracy is not None and current_metrics.accuracy >= target_accuracy:
            return history
        if stop_condition and stop_condition(current_metrics):
            return history

        while len(history) < max_generations:
            try:
                candidate_spec, mutation, candidate_metrics, decision = await self.evolve_step(
                    current_generation_id=current_gen_id,
                    current_generation_number=current_gen_number,
                    current_spec=current_spec,
                    current_metrics=current_metrics,
                    failures=current_failures,
                    task_subset=task_subset,
                )
            except Exception:
                # No valid mutation generated or evaluation halted
                break

            history.append((candidate_spec, candidate_metrics, decision))

            if decision.accepted:
                current_spec = candidate_spec
                current_metrics = candidate_metrics
                current_gen_id = str(uuid.uuid4())
                current_gen_number += 1
                consecutive_rejections = 0

                if target_accuracy is not None and candidate_metrics.accuracy >= target_accuracy:
                    break
                if stop_condition and stop_condition(candidate_metrics):
                    break
            else:
                # Rejected: current remains parent!
                consecutive_rejections += 1
                if consecutive_rejections >= max_consecutive_rejections:
                    break

        return history
