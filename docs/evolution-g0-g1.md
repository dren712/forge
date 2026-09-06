# FORGE S6-I — Evolution Cycle G0 $\to$ G1 Empirical Report

## 1. Executive Summary

This report documents an **actual measured evolution cycle** connecting the full outer evolution loop components:

$$\text{G0} \longrightarrow \text{Benchmark} \longrightarrow \text{Metrics} \longrightarrow \text{Failure Clustering} \longrightarrow \text{Mutation Proposal} \longrightarrow \text{Candidate AgentSpec} \longrightarrow \text{Candidate Benchmark} \longrightarrow \text{Candidate Metrics} \longrightarrow \text{Pareto Acceptance Gate} \longrightarrow \text{Decision}$$

All steps were executed using production LLM inference (`TensorMuxProvider` running `glm-4-7-flash` via `https://api.tensormux.com/v1`) against the enterprise benchmark suite (`SoftwareEngineeringBenchmark` v2.0.0).

In adherence to Section S6 guidelines:
* **No results were fabricated or manually modified.**
* **The candidate performed worse on efficiency (composite delta $-0.0050$) and was deterministically REJECTED by the Pareto gate.**
* **The rejected candidate generation remains fully persisted and inspectable.**
* **Parent G0 remains the champion (`best_generation_id`).**

---

## 2. Experimental Setup & Starting Conditions

* **Experiment ID**: `0b874877-5064-466f-a548-55270f57f78a`
* **Benchmark Suite**: `SoftwareEngineeringBenchmark`
* **Benchmark Version**: `2.0.0`
* **Evaluated Task**: `task_01` (*Fix pagination boundary in user list API*)
* **Allowed Tools**: `["repository", "file_editor", "test_runner", "shell", "search"]`
* **Live LLM Provider**: `TensorMuxProvider` (`glm-4-7-flash`)
* **Task Workspace Isolation**:
  * G0 Workspace: `workspaces/0b874877-5064-466f-a548-55270f57f78a/gen_0/task_01`
  * G1 Workspace: `workspaces/0b874877-5064-466f-a548-55270f57f78a/gen_1/task_01`
  * Environment reset explicitly invoked prior to each run via `benchmark.reset_task()`.

---

## 3. Generation 0 (Baseline)

### 3.1 G0 AgentSpec
* **Generation ID**: `feba7e98-b0dc-43d6-bc01-2c3f6a98f0bc`
* **Parent Generation ID**: `null` (Root ancestor)
* **Model**: `glm-4-7-flash`
* **Planner**: `re_act` (`max_subgoals: 5`, `require_replan_on_error: false`)
* **Memory**: `working_context` (`max_history_items: 30`, `summarize_threshold: 20`)
* **Verifier**: `mandatory_tests` (`require_zero_failed_tests: true`, `enforce_before_complete: true`, `min_test_count: 1`)
* **Retry Policy**: `max_attempts: 3`, `retry_on_tool_failure: true`, `backoff_seconds: 1.0`
* **Orchestration**: `plan_execute_verify` (`max_loops: 10`)

### 3.2 G0 Benchmark Execution & Metrics
* **Task Success**: `True` (Passed boundary test assertion)
* **Accuracy**: `1.0` (100.0%)
* **Reliability**: `0.9455`
* **Latency**: `44,249.2 ms` (44.25s)
* **Token Consumption**: `28,512` tokens
* **Model Calls**: `12`
* **Tool Calls**: `11`
* **Cost**: `$0.018257`
* **Composite Score**: `0.8654`
* **Status**: `COMPLETED`

---

## 4. Failure Clustering & Mutation Proposal

### 4.1 Failure Clustering
Because G0 achieved 1.0 accuracy on the baseline task, the failure clustering module detected no hard crashes, but flagged boundary condition rigor and edge-case coverage as the primary optimization vector (`REASONING_FAILURE` sensitivity).

### 4.2 Proposed Mutation
* **Mutation ID**: `1d4c2012-0f06-4b49-b0f5-8ed0c561b49f`
* **Target**: `system_prompt`
* **Mutation Type**: `PROMPT_UPDATE`
* **Reason**: *"Exploring constraint tightening and edge-case optimization for high-accuracy agent."*
* **Observed Failure**: `REASONING_FAILURE`
* **Expected Effect**: *"Sharpen boundary compliance and edge-case coverage."*

#### Exact Diff Applied to AgentSpec:
```diff
--- G0 System Prompt
+++ G1 System Prompt
@@ -1,4 +1,5 @@
 You are an autonomous software engineering agent. Your goal is to resolve issues in repositories through autonomous mutation and evaluation. Utilize the available tools: repository, file_editor, test_runner, shell, and search. Analyze the codebase to identify issues, apply targeted mutations to fix them, and rigorously evaluate the results using the test runner. Ensure all tests pass before marking the task as complete.
+[OPTIMIZATION]: Enforce strict boundary checks and edge-case verification for full coverage.
```

---

## 5. Candidate Generation 1 (Evaluation)

### 5.1 G1 Candidate Execution
* **Generation ID**: `1d5bb8d5-e371-4dbc-8266-12e641401898`
* **Parent Generation ID**: `feba7e98-b0dc-43d6-bc01-2c3f6a98f0bc`
* **Generation Number**: `1`
* **Benchmark Version**: `2.0.0` (Identical task set and version as G0)
* **Workspace Isolation**: Clean workspace seeded from pristine task files.

### 5.2 Measured Candidate Metrics
* **Task Success**: `True`
* **Accuracy**: `1.0` (100.0%)
* **Reliability**: `0.9571`
* **Latency**: `49,724.3 ms` (49.72s)
* **Token Consumption**: `44,834` tokens
* **Model Calls**: `15`
* **Tool Calls**: `14`
* **Cost**: `$0.026779`
* **Composite Score**: `0.8604`

---

## 6. Metric Comparison & Delta Analysis

| Metric | Parent (G0) | Candidate (G1) | Delta ($\Delta$) | Relative Change | Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | `1.0000` | `1.0000` | `0.0000` | `0.0%` | **EQUAL** |
| **Reliability** | `0.9455` | `0.9571` | `+0.0116` | `+1.23%` | **BETTER** |
| **Cost per Task** | `$0.018257` | `$0.026779` | `+$0.008522` | `+46.68%` | **WORSE** |
| **Latency per Task**| `44,249.2 ms`| `49,724.3 ms`| `+5,475.1 ms` | `+12.37%` | **WORSE** |
| **Composite Score** | `0.8654` | `0.8604` | `-0.0050` | `-0.58%` | **WORSE** |
| **Total Tokens** | `28,512` | `44,834` | `+16,322` | `+57.24%` | **WORSE** |
| **Tool Calls** | `11` | `14` | `+3` | `+27.27%` | **WORSE** |

---

## 7. Pareto Acceptance Gate Decision

### 7.1 Objective Evaluation
1. **Accuracy**: Equal ($1.0 \to 1.0$)
2. **Reliability**: Better ($0.9455 \to 0.9571$, $+1.23\%$)
3. **Cost**: Worse ($+\$0.0085$, $+46.68\%$ cost surge)
4. **Latency**: Worse ($+5.48\text{s}$, $+12.37\%$ slower)

### 7.2 Dominance Classification
* **Dominance Result**: `TRADEOFF`
  * Candidate is better on reliability, but worse on cost and latency.
  * Neither candidate nor parent strictly Pareto-dominates across all 4 objectives.

### 7.3 Configured Policy Evaluation
* **Policy**: `TradeoffPolicy.COMPOSITE_THRESHOLD`
* **Decision**: **`REJECTED`**
* **Reason**:
  > *"Tradeoff rejected by configured policy: composite score change (-0.0050) does not meet minimum improvement threshold (+0.0100)."*

#### Empirical Finding:
Tightening the system prompt prompt with `[OPTIMIZATION]: Enforce strict boundary checks and edge-case verification for full coverage` caused the LLM to make 3 additional tool calls and burn 16,322 more tokens performing redundant test checks. While this yielded a tiny $+1.23\%$ gain in measured reliability, it drove cost up by $+46.68\%$, resulting in a net negative composite utility score. The Pareto gate correctly protected the system from adopting a wasteful mutation.

---

## 8. Persistence & Lineage Invariants

1. **Candidate Status**: `GenerationModel.status = "REJECTED"`
2. **Rejection Reason**: Persisted in `GenerationModel.rejection_reason`.
3. **Lineage Preservation**:
   - `G1.parent_generation_id == "feba7e98-b0dc-43d6-bc01-2c3f6a98f0bc"` (G0)
   - Both G0 and G1 remain stored in SQLite; the rejected generation was **not deleted**.
4. **Experiment Champion**:
   - `exp.best_generation_id = "feba7e98-b0dc-43d6-bc01-2c3f6a98f0bc"` (Remains G0)
   - `exp.current_generation_id = "feba7e98-b0dc-43d6-bc01-2c3f6a98f0bc"` (Remains G0)
5. **Parent Immutability**:
   - G0 metrics, agent spec, and status remained completely unaltered.
6. **Provenance Event Chain**:
   - Cryptographic hash chain verified from `GENESIS_HASH` through all 14 trace events.

---

## 9. Test Suite Verification

Full test suite execution:
```bash
.venv/bin/pytest apps/api/tests/ -v
# 100 passed in 6.72s
```
All contracts, lineage constraints, Pareto gate rules, and end-to-end evolution cycles verified.
