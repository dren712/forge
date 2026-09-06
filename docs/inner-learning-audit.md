# FORGE — Inner Learning Implementation Audit (Section S5-A)

**Audit Date**: September 6, 2026  
**Scope**: Inner learning loop: Tool Failure → Reflection → Knowledge Extraction → Memory Persistence → Memory Retrieval → Prompt/Context Injection  
**Target Files Audited**:
- `apps/api/app/agents/runtime.py`
- `apps/api/app/agents/reflection.py`
- `apps/api/app/memory/tool_memory.py`
- `apps/api/app/models/entities.py`
- `apps/api/app/services/experiment_service.py`
- `scripts/run_benchmark.py`
- `apps/api/tests/test_reflection.py`
- `apps/api/tests/test_tool_memory.py`
- `apps/api/tests/test_learning_loop_end_to_end.py`

---

## 1. Trace of the Inner Learning Execution Path

```text
               ┌──────────────────────────────┐
               │         Tool Failure         │
               └──────────────┬───────────────┘
                              │ ToolResult(success=False, error=..., status_code=...)
                              │ Recorded in state.tool_results & state.observations
                              ▼
               ┌──────────────────────────────┐
               │      Reflection Trigger      │
               └──────────────┬───────────────┘
                              │ Triggered post-loop in AgentRuntime.run()
                              │ (Bypassed in ExperimentService.run_learning_loop)
                              ▼
               ┌──────────────────────────────┐
               │     Knowledge Extraction     │
               └──────────────┬───────────────┘
                              │ ToolReflectionEngine.reflect_on_execution()
                              │ Deterministic regex/substring matching on error traces
                              ▼
               ┌──────────────────────────────┐
               │      Memory Persistence      │
               └──────────────┬───────────────┘
                              │ ToolMemoryStore.add_or_update() (In-Memory)
                              │ ToolMemoryStore.sync_to_db() (SQLite: tool_memories)
                              ▼
               ┌──────────────────────────────┐
               │       Memory Retrieval       │
               └──────────────┬───────────────┘
                              │ ToolMemoryStore.get_entries(tool_names)
                              │ ToolMemoryStore.format_for_prompt()
                              ▼
               ┌──────────────────────────────┐
               │   Prompt/Context Injection   │
               └──────────────────────────────┘
                              │ AgentRuntime.run() lines 229-234
                              │ Appended to system_instruction & state.messages
```

---

## 2. Component-by-Component Audit

### Step 1: Tool Failure
- **Files / Classes / Functions**:
  - `apps/api/app/agents/runtime.py`: `AgentRuntime._execute_single_tool_call()` (lines 400–477) and `AgentRuntime.run()` (lines 330–350).
- **Implementation Reality**: `VERIFIED`.
  - When a tool fails (e.g. `LinearIssueTool` raises `invalid_team_uuid` or `SlackChannelTool` raises `policy_violation_enterprise_channel`), a structured `ToolResult` is returned with `success=False`, `error`, `error_type`, `status_code`, and `output`.
  - The runtime records this result in `state.tool_results` and `state.observations`, injects a `role: tool` message into `state.messages`, and transitions `state.status` to `AgentStatus.RECOVERING`.

### Step 2: Reflection Trigger
- **Files / Classes / Functions**:
  - `apps/api/app/agents/runtime.py`: lines 544–572.
  - `apps/api/app/services/experiment_service.py`: `ExperimentService.run_learning_loop()` (lines 434–505).
- **Implementation Reality**: `PARTIAL / SIMULATED`.
  - In `AgentRuntime.run()`: At post-loop conclusion, if `self.memory_store` is present, it emits `SELF_REFLECTION_STARTED`, calls `ToolReflectionEngine.reflect_on_execution()`, emits `TOOL_PLAYBOOK_LEARNED`, and emits `SELF_REFLECTION_COMPLETED`.
  - In `ExperimentService.run_learning_loop()`: **SIMULATED**. It does NOT call `AgentRuntime.run()` or `ToolReflectionEngine.reflect_on_execution()`. Instead, it manually inserts hardcoded rules into `ToolMemoryStore` and prompts the LLM to generate a decorative 2-sentence summary.

### Step 3: Knowledge Extraction
- **Files / Classes / Functions**:
  - `apps/api/app/agents/reflection.py`: `ToolReflectionEngine.reflect_on_execution(state, memory_store, model_name)`.
- **Implementation Reality**: `VERIFIED (Deterministic Heuristic Parser)`.
  - Analyzes `state.tool_results` by inspecting tool names and matching substrings in `output` and `error`.
  - Covers 6 fixed categories:
    1. `linear_api`: team UUID format (`422`), integer priority (`400`), assignee for In Progress (`409`).
    2. `slack_api`: `[SLA-ALERT]` and `customer_id` requirement for `#enterprise-escalations` (`400`).
    3. `crm_api`: Enterprise tier routing logic and SLA thresholds.
    4. `github_api`: Branch prefix requirements (`fix/`, `hotfix/`) and bracketed ticket PR titles.
    5. `sentry_api`: Minimum 15-character resolution note (`422`).
    6. `test_runner`: Assertion failure trace inspection.
  - **Limitation**: Does not use an LLM for open-ended or arbitrary failure synthesis; extraction is rule-based pattern matching.

### Step 4: Memory Persistence
- **Files / Classes / Functions**:
  - `apps/api/app/memory/tool_memory.py`: `ToolMemoryStore.add_or_update()`, `sync_to_db()`, `sync_from_db()`.
  - `apps/api/app/models/entities.py`: `ToolMemoryModel` (table `tool_memories`).
- **Implementation Reality**: `VERIFIED`.
  - In-memory entries are deduplicated by `tool_name` and `pattern_trigger`. Repeat observations increment `observation_count` and boost `confidence` (+0.05 up to 1.0).
  - Persistence to SQLite table `tool_memories` via `sync_to_db(db)` and `sync_from_db(db)` is verified.

### Step 5: Memory Retrieval
- **Files / Classes / Functions**:
  - `apps/api/app/memory/tool_memory.py`: `ToolMemoryStore.get_entries()`, `ToolMemoryStore.format_for_prompt()`.
- **Implementation Reality**: `VERIFIED`.
  - Filters playbooks by `tool_names` in `AgentSpec.tools`.
  - Formats entries into a structured markdown block (`### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]`) with Actionable Rule, trigger pattern, confidence, and observation count.

### Step 6: Prompt / Context Injection
- **Files / Classes / Functions**:
  - `apps/api/app/agents/runtime.py`: `AgentRuntime.run()` lines 229–234, 242.
- **Implementation Reality**: `VERIFIED IN RUNTIME, BYPASSED IN BENCHMARK CLI`.
  - In `AgentRuntime`: If `self.memory_store` is provided, `playbook_text` is formatted and appended to `system_instruction`. It is placed in `state.messages` (`role: system`), reaching `self.provider.generate()` on every multi-turn step.
  - In `scripts/run_benchmark.py`: `AgentRuntime` is instantiated **without** `memory_store` (`AgentRuntime(spec=spec, provider=provider)`). In `--mode evolved`, rules are baked directly into a static string in `spec.system_prompt` via `build_spec()`.

---

## 3. Specific Audit Questions Addressed

### Q1: Exact files, classes, and functions for each step?
- See Section 2 above for complete file paths, class names, method signatures, and line numbers.

### Q2: What is actually implemented?
- `ToolMemoryStore` with deduplication, confidence boosting, prompt formatting, and SQLite persistence.
- `ToolReflectionEngine` extracting playbooks from execution error traces across 6 tool categories.
- `AgentRuntime` prompt injection (pre-loop) and reflection trigger (post-loop) when `memory_store` is supplied.
- SQLAlchemy `ToolMemoryModel` in table `tool_memories`.
- `EvolutionEngine` wiring of `ToolMemoryStore` into `AgentRuntime`.

### Q3: What is mocked or simulated?
- **`ExperimentService.run_learning_loop()`**: Returns hardcoded static numbers for `run_1_cold` (6 calls, 3 errors, 5200ms) and `run_2_warm` (2 calls, 0 errors, 1300ms) instead of executing `AgentRuntime.run()`.
- **`scripts/run_benchmark.py`**: `--mode evolved` uses a hardcoded prompt string and a mode-checking mock provider (`BenchmarkMockProvider`), bypassing dynamic `ToolMemoryStore` retrieval.

### Q4: What is missing?
- Live two-pass execution inside `run_learning_loop` (Pass 1 Cold without memory $\to$ Distill $\to$ Pass 2 Warm with memory).
- Dynamic memory passing in `scripts/run_benchmark.py` (`AgentRuntime(..., memory_store=store)`).
- LLM-based fallback reflection for novel, unmodeled error messages.

### Q5: Does memory survive across executions?
- **Within SQLite database (per `experiment_id`)**: **YES**. `sync_to_db` and `sync_from_db` persist playbooks across separate processes and server restarts.
- **Across benchmark tasks in `scripts/run_benchmark.py`**: **NO**. `memory_store` is not initialized or passed to the runtime.
- **Within an `EvolutionEngine` instance**: **YES in-memory** across tasks in that engine instance.

### Q6: Does retrieved memory actually reach the model?
- **When `AgentRuntime` has `memory_store`**: **YES**. Injected into `system_instruction`, stored in `state.messages[0]["content"]`, and sent to `LLMProvider.generate()`.
- **In `run_learning_loop`**: **NO**, because `AgentRuntime` is not executed.
- **In `scripts/run_benchmark.py`**: **NO**, because `memory_store` is `None`.

### Q7: Can benchmark execution be run with and without memory?
- **In `scripts/run_benchmark.py`**: **PARTIALLY / NOMINALLY**. It accepts `--mode baseline` (stateless) and `--mode evolved` (working_context), but this controls a static prompt string and a mock provider switch, not genuine `ToolMemoryStore` retrieval.
- **In `EvolutionEngine`**: **YES**, by passing or omitting `memory_store`.

---

## 4. Verification Tests Executed

Executed the minimal relevant test subset:
```bash
.venv/bin/pytest apps/api/tests/test_reflection.py apps/api/tests/test_tool_memory.py apps/api/tests/test_learning_loop_end_to_end.py -v
```
**Results**:
- `test_reflection.py::test_reflection_engine_distills_playbooks_from_errors`: **PASSED** (6 rules distilled from 6 mock tool error traces).
- `test_tool_memory.py::test_tool_memory_store_add_and_format`: **PASSED** (Store correctly deduplicates, boosts confidence, formats prompt markdown).
- `test_learning_loop_end_to_end.py::test_learning_loop_end_to_end`: **PASSED** (Passes only because it asserts against the hardcoded dictionary return values in `run_learning_loop`).

---

## 5. Audit Conclusion

S5-A STATUS: PARTIAL

The low-level mechanics of inner learning (`ToolMemoryStore`, `ToolReflectionEngine`, `AgentRuntime` system prompt injection, and SQLite database persistence) are genuinely implemented and functional. However, the high-level demo endpoint (`run_learning_loop` in `experiment_service.py`) and the benchmark CLI (`scripts/run_benchmark.py`) currently simulate or bypass dynamic memory execution.

---

## 6. Recommended Next Change

**Recommend exactly ONE next change**:

Refactor `apps/api/app/services/experiment_service.py:run_learning_loop` to replace the hardcoded metric dictionary with **two genuine sequential executions of `AgentRuntime.run()`**:
1. **Pass 1 (Cold)**: Instantiate `AgentRuntime` with `memory_store=None` on a benchmark task (e.g., `task_01_enterprise_escalation`); execute live and capture genuine tool calls, errors, latency, and tokens.
2. **Distillation**: Pass `cold_state` to `ToolReflectionEngine.reflect_on_execution(cold_state, mem_store)` to distill genuine error playbooks into `mem_store`, and sync to SQLite.
3. **Pass 2 (Warm)**: Instantiate `AgentRuntime` with `memory_store=mem_store` on the same task (or reset environment); execute live with playbooks injected into the model prompt; record genuine reductions in tool calls, errors, and tokens, and return real computed deltas.
---

# Section S5-B — Persistent Tool Memory Implementation & Verification

**Execution Date**: September 6, 2026  
**Scope**: Fulfill persistent tool memory contract: storage, retrieval, confidence, category, evidence, timestamp, deterministic serialization, and empty store invariants.

## 1. Implemented Memory Contract Specifications

- **File**: `apps/api/app/memory/tool_memory.py`
- **Class**: `ToolPlaybookEntry`
  - `id: str`: Unique identifier (UUIDv4).
  - `experiment_id: str`: Associated experiment ID foreign key.
  - `tool_name: str`: Identifier of the enterprise tool (e.g. `linear_api`, `slack_api`).
  - `category: str`: Categorized policy or quirk domain (`SCHEMA_QUIRK`, `CONTEXTUAL_LOGIC`, `WORKFLOW_DEPENDENCY`, `ERROR_RECOVERY`).
  - `pattern_trigger: str`: Trigger context or tool call parameter condition.
  - `learned_rule: str`: High-leverage operational instruction.
  - `evidence: Optional[str]`: Raw error code or response trace explaining the rule origin.
  - `confidence: float`: Bounded float `[0.0, 1.0]` reflecting empirical reliability.
  - `observation_count: int`: Frequency counter of how many times the rule was reinforced.
  - `created_at: str`: ISO 8601 UTC creation timestamp.
  - `updated_at: str`: ISO 8601 UTC update timestamp.
  - `canonical_dict()`: Deterministic key-sorted dictionary representation.
  - `to_canonical_json()`: RFC 8785-compliant deterministic JSON serialization.
- **Class**: `ToolMemoryStore`
  - `save_playbook()`: Explicit saving interface recording learned playbooks.
  - `retrieve_playbooks(tool_names, category, min_confidence)`: Granular retrieval with multi-criteria filtering and deterministic sorting by `(-confidence, tool_name, pattern_trigger)`.
  - `format_for_prompt(tool_names)`: Renders system prompt markdown block `### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]`.
  - **Empty Store Invariant**: If no playbooks exist (or none match the requested tools), `format_for_prompt()` strictly returns `""` (empty string), guaranteeing zero prompt injection for naive agents.
  - `to_canonical_json()`: Deterministically serializes the entire store sorted by canonical keys.
  - `save_to_file(path)` / `load_from_file(path)`: File-based persistence round-trip.
  - `sync_to_db(db)` / `sync_from_db(db)`: SQLite persistence mapping to `tool_memories` table with deterministic `order_by(created_at, id)`.

## 2. Test Verification & Proof of Cycle

The test suite in `apps/api/tests/test_tool_memory.py` was updated with 4 comprehensive tests:
1. `test_tool_memory_store_add_and_format`:
   - Proves entry creation, deduplication on repeat triggers, observation counting, and confidence boosting (+0.05 per observation).
2. `test_empty_memory_store_returns_no_learned_context`:
   - Proves that an empty or uninitialized memory store returns `[]` from `get_entries()`, `[]` from `retrieve_playbooks()`, and strictly `""` (empty string) from `format_for_prompt()`.
3. `test_save_persist_new_execution_retrieve_cycle`:
   - Proves the full lifecycle:
     $$\\text{save (Execution 1)} \\to \\text{sync\\_to\\_db (SQLite)} \\to \\text{new ToolMemoryStore instance (Execution 2)} \\to \\text{sync\\_from\\_db} \\to \\text{retrieve\\_playbooks}$$
   - Confirms exact preservation of all fields (`category`, `evidence`, `confidence`, `timestamps`, `learned_rule`).
   - Confirms that the newly instantiated execution receives the formatted prompt markdown containing verified rules and evidence.
4. `test_deterministic_serialization_and_file_persistence`:
   - Proves that two stores with identical entries inserted in different sequences produce identical canonical JSON strings.
   - Proves round-trip file persistence via `save_to_file` and `load_from_file`.

## 3. Test Execution Results

```bash
.venv/bin/pytest apps/api/tests/test_tool_memory.py -v
```
**Output**: `4 passed in 0.62s` (100% green)

```bash
.venv/bin/pytest apps/api/tests/ -v
```
**Output**: `52 passed in 1.33s` (100% green across all 15 test suites)

## 4. Section S5-B Conclusion

S5-B STATUS: VERIFIED
The persistent tool memory contract is fully implemented, deterministically serialized, and verified against SQLite and local storage without altering runtime architecture, benchmarks, evolution engine, frontend, or model provider layers.
