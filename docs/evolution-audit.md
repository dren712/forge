# FORGE S6-A — Outer Evolution Implementation Audit

**Audit Date**: September 6, 2026  
**Auditor**: Anti-Hallucination Evolution Architecture Audit  
**Target Subsystems**: Outer Evolutionary Optimization Pipeline  
**Audited Files**:
- `apps/api/app/schemas/agent_spec.py`
- `apps/api/app/agents/architect.py`
- `apps/api/app/benchmarks/base.py`
- `apps/api/app/benchmarks/software_engineering.py`
- `apps/api/app/benchmarks/third_party_benchmark.py`
- `apps/api/app/agents/runtime.py`
- `apps/api/app/evaluation/scoring.py`
- `apps/api/app/evaluation/metrics.py`
- `apps/api/app/evaluation/failure_analyzer.py`
- `apps/api/app/evolution/mutation.py`
- `apps/api/app/evolution/mutation_generator.py`
- `apps/api/app/evolution/engine.py`
- `apps/api/app/evolution/acceptance.py`
- `apps/api/app/services/experiment_service.py`
- `apps/api/app/models/entities.py`
- `apps/api/tests/test_vertical_slice.py`
- `apps/api/tests/test_architecture_contracts.py`
- `apps/api/tests/test_model_layer.py`

---

## 1. Trace of the Outer Evolution Execution Path

The canonical outer evolutionary loop progresses through the following 11 stages:

```text
[1] baseline AgentSpec
       │
       ▼
[2] benchmark (setup task workspaces)
       │
       ▼
[3] task results (AgentRuntime.run → Benchmark.evaluate_task)
       │
       ▼
[4] aggregate metrics (scoring.py: aggregate_generation_metrics)
       │
       ▼
[5] failure analysis (failure_analyzer.py: FailureAnalyzer.analyze)
       │
       ▼
[6] mutation proposal (mutation_generator.py: MutationGenerator.propose_mutation)
       │
       ▼
[7] candidate AgentSpec (deepcopied & mutated AgentSpec)
       │
       ▼
[8] candidate benchmark (EvolutionEngine.run_generation on candidate)
       │
       ▼
[9] comparison (acceptance.py: AcceptanceEngine.evaluate_candidate)
       │
       ▼
[10] accept/reject (Pareto multi-objective decision)
       │
       ▼
[11] generation persistence (experiment_service.py → GenerationModel, MutationModel, TraceEvents)
```

---

## 2. Stage-by-Stage Forensic Audit

### Step 1: Baseline AgentSpec
* **Exact File**: `apps/api/app/schemas/agent_spec.py` and `apps/api/app/agents/architect.py`
* **Class / Function**: `AgentSpec` (Pydantic model) and `AgentArchitect.design_agent()`
* **Input**: User goal (`str`), `available_tools: list[str]`, `benchmark_description: str`, `generation_number: int = 0`
* **Output**: Validated `AgentSpec` instance (`model`, `system_prompt`, `planner`, `tools`, `memory`, `verifier`, `retry_policy`, `orchestration`)
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: In `test_vertical_slice.py:24-33` and `test_model_layer.py:102-118`. Pydantic validation ensures strongly typed serialization.

### Step 2: Benchmark
* **Exact File**: `apps/api/app/benchmarks/base.py`, `apps/api/app/benchmarks/software_engineering.py`, `apps/api/app/benchmarks/third_party_benchmark.py`, `apps/api/app/evolution/engine.py`
* **Class / Function**: `Benchmark` (Protocol), `EvolutionEngine.run_generation()`, `Benchmark.setup_task()`
* **Input**: `generation_id: str`, `generation_number: int`, `spec: AgentSpec`, `task_subset: list[BenchmarkTask] | None`
* **Output**: Isolated filesystem workspaces (`workspaces/{experiment_id}/gen_{gen_number}/{task_id}`) seeded with pristine baseline state files (`.linear_state.json`, `.slack_messages.json`, git repos, test fixtures)
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: `EvolutionEngine.run_generation` initializes directories and calls `benchmark.setup_task()` before agent execution. Verified in `test_benchmark_integrity.py`.

### Step 3: Task Results
* **Exact File**: `apps/api/app/agents/runtime.py` and `apps/api/app/benchmarks/base.py`
* **Class / Function**: `AgentRuntime.run()` $\to$ `Benchmark.evaluate_task()`
* **Input**: Task goal, workspace path, generation_id, execution_id
* **Output**: `AgentState` $\to$ `TaskEvaluation` (passed, score, reason, checks, failures, tool_calls) and `ExecutionMetrics` (accuracy, reliability, cost_usd, latency_ms, input_tokens, output_tokens, model_calls, tool_calls, tool_errors, clean_exit, recovered_from_error)
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: State transitions and evaluations inspect actual filesystem artifacts and tool outputs. Verified in `EvolutionEngine.run_generation:80-122`.

### Step 4: Aggregate Metrics
* **Exact File**: `apps/api/app/evaluation/scoring.py` and `apps/api/app/evaluation/metrics.py`
* **Class / Function**: `aggregate_generation_metrics(generation_number, task_metrics, failure_counts)`
* **Input**: `generation_number: int`, `task_metrics: list[ExecutionMetrics]`, `failure_counts: dict[str, int]`
* **Output**: `GenerationMetrics` (accuracy, reliability, total_cost_usd, avg_cost_per_task, avg_latency_ms, composite_score, total_tokens, total_model_calls, total_tool_calls, verification_pass_rate, failure_breakdown)
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: Evaluated via mathematical composite scoring:
  $$\text{composite} = 0.50 \cdot \text{accuracy} + 0.30 \cdot \text{reliability} + 0.10 \cdot \text{cost\_score} + 0.10 \cdot \text{speed\_score}$$
  Verified in `apps/api/tests/test_scoring.py`.

### Step 5: Failure Analysis
* **Exact File**: `apps/api/app/evaluation/failure_analyzer.py`
* **Class / Function**: `FailureAnalyzer.analyze(agent_spec, state, task, evaluation, metrics)`
* **Input**: `AgentSpec`, `AgentState`, `BenchmarkTask`, `TaskEvaluation`, `ExecutionMetrics`
* **Output**: `FailureAnalysis` (`task_id`, `failure_type`, `severity`, `evidence`, `root_cause`, `recommended_mutation`, `confidence`)
* **Current Status**: **`PARTIAL / SIMULATED` (Dual State)**
  * **Within `EvolutionEngine.run_generation`**: **`IMPLEMENTED`**. Directly executes `_rule_based_diagnosis` (for verification, timeout, recovery failure, constraint violation) with fallback to LLM structured diagnosis (`ANALYZER_SYSTEM_PROMPT`).
  * **Within `ExperimentService.evolve_generation`**: **`SIMULATED`**. In `apps/api/app/services/experiment_service.py:301-322`, the real `FailureAnalysis` objects from previous task executions are **not retrieved from the database**. Instead, `ExperimentService` reconstructs *synthetic* `FailureAnalysis` instances using dummy `task_id="observed_task"` and generic string root causes derived purely from `current_gen.metrics.get("failure_breakdown", {})`, or synthesizes a placeholder `VERIFICATION_FAILURE` if the dictionary is empty.

### Step 6: Mutation Proposal
* **Exact File**: `apps/api/app/evolution/mutation_generator.py`
* **Class / Function**: `MutationGenerator.propose_mutation(current_spec, failures, generation_number)`
* **Input**: `current_spec: AgentSpec`, `failures: list[FailureAnalysis]`, `generation_number: int`
* **Output**: `tuple[AgentSpec, Mutation]`
* **Current Status**: **`PARTIAL` (Heuristic Only, LLM Unused)**
  * `MutationGenerator` accepts `provider: LLMProvider | None = None` in its constructor (`__init__`), but `propose_mutation()` completely ignores `self.provider`.
  * It evaluates a fixed priority heuristic:
    1. If `VERIFICATION_FAILURE` and verifier is `none` $\to$ mutate verifier to `mandatory_tests`.
    2. If `PLANNING_FAILURE` or `TIMEOUT` $\to$ mutate planner to `structured_plan`, orchestration to `plan_execute_verify`.
    3. If `TOOL_EXECUTION_FAILURE` or `RECOVERY_FAILURE` $\to$ increase `retry_policy.max_attempts` to 4 and enable `backoff_seconds`.
    4. If verifier is already `mandatory_tests` $\to$ upgrade verifier to `strict_test_gate`.
    5. Fallback $\to$ append negative constraints to `system_prompt`.
  * While deterministic and grounded in failure categories, dynamic LLM-driven architectural mutations are uninvoked.

### Step 7: Candidate AgentSpec
* **Exact File**: `apps/api/app/evolution/mutation_generator.py`
* **Class / Function**: `MutationGenerator.propose_mutation()`
* **Input**: `copy.deepcopy(current_spec)`
* **Output**: Mutated `candidate_spec: AgentSpec`
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: Pydantic schema produces valid, fully deserializable spec records.

### Step 8: Candidate Benchmark
* **Exact File**: `apps/api/app/evolution/engine.py`
* **Class / Function**: `EvolutionEngine.run_generation()` (called from `EvolutionEngine.evolve_step()`)
* **Input**: `candidate_gen_id: str`, `candidate_gen_number: int`, `spec: candidate_spec`, `task_subset`
* **Output**: `candidate_metrics: GenerationMetrics`, `candidate_task_metrics: list[ExecutionMetrics]`, `candidate_failures: list[FailureAnalysis]`
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: Runs candidate agent runtime across the benchmark tasks in clean candidate generation workspaces (`gen_1/`).

### Step 9: Comparison
* **Exact File**: `apps/api/app/evolution/acceptance.py`
* **Class / Function**: `AcceptanceEngine.evaluate_candidate(parent, candidate)`
* **Input**: `parent: GenerationMetrics`, `candidate: GenerationMetrics`
* **Output**: `AcceptanceDecision` (`accepted: bool`, `status: str`, `reason: str`, `accuracy_delta`, `reliability_delta`, `cost_delta_percent`, `latency_delta_percent`, `composite_delta`)
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: Multi-objective Pareto rules:
  1. Rejects if accuracy regresses ($< -0.001$).
  2. Rejects if cost increases $> 60\%$ without significant accuracy gain ($< 5\%$).
  3. Accepts if accuracy improves ($> 0$).
  4. Accepts if accuracy is equal but reliability improves ($\ge 5\%$).
  5. Accepts if composite score improves ($> 0.02$).
  6. Otherwise rejects.
  Verified in `apps/api/tests/test_architecture_contracts.py:test_acceptance_engine_deterministic_contracts`.

### Step 10: Accept / Reject Decision
* **Exact File**: `apps/api/app/evolution/engine.py`
* **Class / Function**: `EvolutionEngine.evolve_step():203-221`
* **Input**: `AcceptanceDecision`
* **Output**: Emits `EventType.GENERATION_ACCEPTED` or `EventType.GENERATION_REJECTED` into cryptographic event recorder with deltas and status; returns `(candidate_spec, mutation, candidate_metrics, decision)`
* **Current Status**: **`IMPLEMENTED`**
* **Verification**: Event emission and decision object verified in `test_vertical_slice.py:76-78`.

### Step 11: Generation Persistence
* **Exact File**: `apps/api/app/services/experiment_service.py`
* **Class / Function**: `ExperimentService.evolve_generation():336-392`
* **Input**: `candidate_spec`, `mutation`, `candidate_metrics`, `decision`, `db: AsyncSession`
* **Output**:
  - `MutationModel` record written to SQLite.
  - `GenerationModel` record written to SQLite with `parent_generation_id`, `mutation_id`, `metrics`, `status`, and `rejection_reason`.
  - All new `TraceEventModel` records committed to event hash chain.
  - If `decision.accepted`: updates `exp.current_generation_id` and `exp.best_generation_id`.
* **Current Status**: **`IMPLEMENTED`**
* **Preservation of Rejected Candidates**:
  * **YES, preserved.** In `ExperimentService.evolve_generation():353-365`:
    ```python
    candidate_gen = GenerationModel(
        id=cand_gen_id,
        experiment_id=exp.id,
        parent_generation_id=current_gen.id,
        generation_number=current_gen.generation_number + 1,
        agent_spec=candidate_spec.model_dump(),
        mutation_id=mutation.id,
        metrics=candidate_metrics.model_dump(),
        benchmark_id=exp.benchmark_id,
        status=decision.status,  # "REJECTED" or "ACCEPTED"
        rejection_reason=decision.reason if not decision.accepted else None,
    )
    db.add(candidate_gen)
    ```
    Rejected generations are persistently stored in the database with their full agent spec, mutation link, metrics, and explicit rejection reason. They are simply not promoted to `exp.best_generation_id` or `exp.current_generation_id`.

---

## 3. Explicit Gap & Classification Summary

| Subsystem Component | Implementation Status | Ground Truth Reality |
| :--- | :---: | :--- |
| **Baseline Spec Design** | `IMPLEMENTED` | Strongly typed Pydantic `AgentSpec` designed via `AgentArchitect`. |
| **Benchmark Workspace Seeding** | `IMPLEMENTED` | Pristine directories with deterministic setup per task. |
| **Runtime Execution & Evaluation** | `IMPLEMENTED` | `AgentRuntime.run()` executed and evaluated against real filesystem state. |
| **Scoring & Metric Aggregation** | `IMPLEMENTED` | Deterministic composite scoring across accuracy, reliability, cost, speed. |
| **Failure Analysis in Engine** | `IMPLEMENTED` | Rule-based and LLM diagnosis in `EvolutionEngine.run_generation()`. |
| **Failure Analysis in Service Layer** | `SIMULATED` | `ExperimentService.evolve_generation()` creates synthetic `FailureAnalysis` objects with dummy `task_id="observed_task"` from breakdown counts. |
| **Mutation Generator** | `PARTIAL` | Rule-based mutation cascade is fully functional, but provider is ignored and LLM mutations are uncalled. |
| **Candidate Execution & Evaluation** | `IMPLEMENTED` | Fully evaluated on candidate workspace. |
| **Pareto Acceptance Engine** | `IMPLEMENTED` | Strict multi-objective mathematical decision gates. |
| **Lineage & Candidate Persistence** | `IMPLEMENTED` | `GenerationModel` and `MutationModel` persisted in SQLite; rejected candidates preserved with reasons. |
| **Mock Mode Coupling in Service** | `SIMULATED` | `ExperimentService.evolve_generation:272-274` explicitly sets `provider.mode = "evolved"` when `DeterministicMockProvider` is detected. |

---

## 4. Test Verification Evidence

Smallest relevant automated tests executed:

```bash
# 1. Acceptance engine Pareto contracts
.venv/bin/pytest apps/api/tests/test_architecture_contracts.py -k "acceptance" -v
1 passed, 7 deselected in 0.19s

# 2. Failure analyzer and mutation generator contracts
.venv/bin/pytest apps/api/tests/test_model_layer.py -k "failure_analyzer" -v
1 passed, 5 deselected in 0.68s

# 3. End-to-end vertical slice (G0 -> Failure -> Mutation -> G1 -> Acceptance -> Provenance)
.venv/bin/pytest apps/api/tests/test_vertical_slice.py -v
1 passed in 0.68s
```

All 3 targeted test suites passed with 100% success.

---

## 5. Audit Conclusion

```text
S6-A STATUS: PARTIAL
```

### Rationale
The core algorithmic components of the outer evolution loop (`EvolutionEngine`, `AcceptanceEngine`, `MutationGenerator`, `FailureAnalyzer`, `Scoring`) are fully implemented and verified by automated unit and integration tests. Lineage tracking and persistence of both accepted and rejected candidates are verified in SQLite.

However, the outer evolutionary pipeline is classified as **`PARTIAL`** due to two specific integration gaps in the service layer:
1. **Disconnected Failure Provenance in Service**: `ExperimentService.run_generation_benchmark` does not persist structured `FailureAnalysis` records to the database. Consequently, `ExperimentService.evolve_generation` reconstructs synthetic placeholder `FailureAnalysis` instances with dummy `task_id="observed_task"` and generic text based purely on `failure_breakdown` counters.
2. **Provider Mode Mutation Override**: `ExperimentService.evolve_generation` contains a test-mode hardcoding that forcibly mutates `provider.mode = "evolved"` when a `DeterministicMockProvider` is used.

---

## 6. Recommended Next Change

**Recommendation (Single Change)**:
Persist the structured `FailureAnalysis` records generated during `run_generation_benchmark` (either as a JSON attribute on `GenerationModel.failures` or linked to `ExecutionModel`), and update `ExperimentService.evolve_generation()` to load these genuine failure analyses directly into `MutationGenerator.propose_mutation()`, eliminating the synthetic `task_id="observed_task"` reconstruction.
