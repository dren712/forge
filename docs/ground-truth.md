# FORGE — Repository Ground Truth & Anti-Hallucination Audit (Section S0)

**Date**: September 6, 2026  
**Auditor**: Anti-Hallucination Audit Baseline  
**Commit Baseline**: `08171b3`  
**Test Suite**: 18 passing tests in 1.33s  
**Frontend Build**: Next.js 14.2.35 production build exit code 0 (5/5 static/dynamic routes verified)

---

## 1. Executive Summary & Audit Methodology

This document establishes the empirical ground truth of the FORGE codebase. Every capability claimed in prior summaries, architecture diagrams, and hackathon decks was audited directly against the source code, database schemas, test execution results, and runtime logs. 

No feature is marked `VERIFIED` based merely on documentation, class declarations, or mocked unit tests. Capabilities are classified into five strict categories:
* **`VERIFIED`**: Genuine functional implementation with automated or live execution verification.
* **`PARTIAL`**: Real code exists, but relies on partial external mocks, thin CLI checks, or incomplete end-to-end wiring.
* **`SIMULATED`**: The underlying system components exist, but the specific high-level endpoint returns pre-compiled, hardcoded data or metric fixtures.
* **`UNVERIFIED`**: Code exists in the repository, but has not been exercised against external production endpoints or lacks live integration validation.
* **`BROKEN`**: Code fails to compile, errors on execution, or has unresolved dependencies.

---

## 2. Definitive Feature Truth Table

| Subsystem / Capability | Source Path & Symbol | Status | Verification Evidence / Reproduction Command | Audit Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Test Suite Baseline** | `apps/api/tests/` | `VERIFIED` | `PYTHONPATH=apps/api .venv/bin/pytest -v apps/api/tests/` (18/18 passed in 1.33s) | Deterministic unit and mock integration tests pass cleanly. |
| **Frontend Production Build** | `apps/web/` | `VERIFIED` | `npm run build` in `apps/web/` (Exit code 0, 5/5 pages generated) | Zero TypeScript errors, zero Next.js lint errors. |
| **TensorMux Provider** | `apps/api/app/providers/tensormux.py:TensorMuxProvider` | `VERIFIED` | Unit tests pass; real client configured for `api.tensormux.com/v1` (`glm-4-7-flash`). | Full OpenAI SDK wrapper handling errors, token usage, tool calling. |
| **AI Grants OpenAI Provider** | `apps/api/app/providers/aigrants.py:AIGrantsIndiaProvider` | `VERIFIED` | Real client targeting `api.openai.com/v1` (`gpt-5-nano`, `text-embedding-3-small`). | Live API network tests executed successfully during prior baseline setup. |
| **Smallest.ai Voice TTS** | `apps/api/app/providers/voice.py:SmallestAIVoiceService` | `VERIFIED` | Real HTTP POST to `waves/v1/lightning-v3.1/get_speech`, returns audio/wav. | Live network test generated 11,564-byte valid audio/wav file. |
| **Experiential Provider** | `apps/api/app/providers/experiential.py:ExperientialProvider` | `UNVERIFIED` | Code implemented for `gpt-6-astra` via `api.experientiallabs.ai/v1`. | Requires `EXPLABS_API_KEY`; untested live due to unconfigured key. |
| **Maximor AO Orchestrator** | `apps/api/app/agents/ao_integration.py:AOOrchestratorBridge` | `PARTIAL` | Subprocess wrapper calling `ao doctor` and `ao status`. | Gracefully returns `available: false` when local binary is absent. Not a runtime hard dependency. |
| **DevOps Tools (GitHub, Sentry)** | `apps/api/app/tools/devops_tools.py` | `VERIFIED` | `apps/api/tests/test_devops_tools.py` passes. | Enforces branch protection, required approvals, and Sentry issue triage states. |
| **SaaS Tools (Linear, Slack, CRM)** | `apps/api/app/tools/third_party_apps.py` | `VERIFIED` | `apps/api/tests/test_third_party_apps.py` passes. | Enforces strict HTTP status codes: 422 for team slugs, 400 for string priority, 400 for missing Slack tags. |
| **Standard Tools (File, Shell, Search)** | `apps/api/app/tools/` | `VERIFIED` | `apps/api/tests/test_tools.py` passes. | Path traversal sandboxing, unified diff edits, ripgrep search all verified. |
| **AgentSpec & Schema** | `apps/api/app/schemas/agent_spec.py` | `VERIFIED` | Pydantic validation across models, verifiers, tools, temperature. | Strict serialization and deserialization. |
| **AgentArchitect** | `apps/api/app/agents/architect.py:AgentArchitect` | `VERIFIED` | `apps/api/tests/test_vertical_slice.py` lines 24–33. | Live/mock LLM structured prompt generation with automated JSON repair. |
| **AgentRuntime (ReAct Loop)** | `apps/api/app/agents/runtime.py:AgentRuntime` | `VERIFIED` | Multi-turn ReAct loop with max turn guards, tool dispatch, error feedback, verifier execution. | Fully functional core engine. Runs against real workspace directories. |
| **Tool Memory (SQLite DB)** | `apps/api/app/memory/tool_memory.py:ToolMemoryStore` | `VERIFIED` | `apps/api/tests/test_tool_memory.py` passes; SQLite schema in `models/entities.py`. | Real persistence, confidence boosting, and prompt formatting via `format_for_prompt()`. |
| **Autonomous Self-Reflection Engine** | `apps/api/app/agents/reflection.py:ToolReflectionEngine` | `VERIFIED` | `apps/api/tests/test_reflection.py` passes; called in `AgentRuntime.run` lines 321–350. | Parses error patterns from execution traces, extracts generalized playbooks. |
| **Benchmarks** | `apps/api/app/benchmarks/` | `VERIFIED` | `software_engineering` (10 tasks), `third_party_automation` (10 tasks). | Real workspace seeding and file/assertion evaluation. |
| **Evolution Engine** | `apps/api/app/evolution/engine.py:EvolutionEngine` | `VERIFIED` | `apps/api/tests/test_vertical_slice.py` passes. | Multi-task evaluation, failure classification, candidate mutation, and generation execution. |
| **Pareto Gate** | `apps/api/app/evolution/acceptance.py:ParetoAcceptanceEngine` | `VERIFIED` | Evaluates composite multi-objective score (accuracy, reliability, cost, latency). | Strictly rejects regressions. |
| **Cryptographic Provenance** | `apps/api/app/provenance/hasher.py:EventRecorder` | `VERIFIED` | `apps/api/tests/test_provenance.py` passes; tamper detection verified. | Canonical RFC 8785 JSON formatting + SHA-256 hash chaining. |
| **SSE Streaming Routes** | `apps/api/app/api/routes.py` | `VERIFIED` | `GET /api/experiments/{id}/stream` yields `TraceEvent` records. | Live FastAPI task 964 actively serving events. |
| **Next.js Web Frontend** | `apps/web/` | `VERIFIED` | Running on port 3000 (task 456), polling and rendering real experiment data. | Interactive Dashboard, Timeline, Memory Inspector, Provenance Viewer. |
| **Cold → Warm Learning Route** | `apps/api/app/services/experiment_service.py:run_learning_loop` | **`SIMULATED`** | Code inspection of lines 423–600. | **CRITICAL AUDIT GAP**: Seeds real DB records and invokes live LLM reflection, but returns fixed hardcoded dictionaries for cold vs warm metrics. |

---

## 3. Red / Yellow / Green Status Classification

### 🟢 Green: Verified & Fully Operational (Do Not Touch / Solid Foundation)
1. **AgentRuntime ReAct Execution**: Multi-step tool execution loop with error handling, sandbox workspace isolation, and verifier integration.
2. **Deterministic & Live LLM Providers**: Clean abstraction (`LLMProvider`) with working clients for TensorMux (`glm-4-7-flash`) and OpenAI AI Grants (`gpt-5-nano`).
3. **Smallest.ai Voice Synthesis**: Functional HTTP service generating real WAV audio from synthesized agent debriefs.
4. **Third-Party & DevOps Tool Sandbox**: Realistic simulation of API quirks (Linear UUIDs, priority integers, Slack SLA policy tags, CRM tier logic, GitHub branch protection, Sentry triage).
5. **Tool Memory Architecture**: SQLite-backed `ToolMemoryStore` with schema persistence and prompt formatting (`format_for_prompt`).
6. **ToolReflectionEngine**: Analyzes error outputs and extracts actionable playbooks into memory.
7. **Evolution Engine & Pareto Gate**: Autonomous G0 → G1 loop with real mutation proposals (`PromptMutation`, `ToolSelectionMutation`, `TemperatureMutation`, `VerifierMutation`).
8. **Cryptographic Provenance**: SHA-256 event chaining with tamper-evident verification.
9. **Next.js Frontend**: Fully compiling, zero-error dashboard with real-time UI components.

### 🟡 Yellow: Partial Implementations & Thin Integrations (Operational with Caveats)
1. **`AOOrchestratorBridge`**: Thin subprocess wrapper calling local `ao` CLI commands. It does not crash if `ao` is absent, but does not autonomously orchestrate remote worker pools without the external binary.
2. **`ExperientialProvider`**: Fully written code for `gpt-6-astra`, but untestable without active `EXPLABS_API_KEY`.
3. **Frontend Causal Transition Cards**: The UI displays the documented 6 → 2 tool call reduction and 50% → 100% accuracy jump, which currently relies on the pre-compiled payload from `POST /api/experiments/{id}/learning-run`.

### 🔴 Red: Major Vulnerabilities & Gaps (Must Fix Before Submission)
1. **Simulated Metrics in `run_learning_loop`**:
   - **File**: `apps/api/app/services/experiment_service.py` (lines 423–600)
   - **Issue**: When a user or judge clicks "Execute Learning Loop", the backend creates DB memory entries and calls the LLM for a reflection summary, but returns a static, hardcoded dictionary:
     - `tool_calls`: 6 → 2
     - `latency_ms`: 5200.0 → 1300.0
     - `cost_usd`: 0.0048 → 0.0014
     - `accuracy`: 0.5 → 1.0
   - **Risk**: If a judge inspects network traces or backend execution logs, they will notice the metrics did not originate from two consecutive `AgentRuntime.run()` calls.
   - **Solution**: Refactor `run_learning_loop` to invoke `AgentRuntime.run()` live twice:
     - **Pass 1 (Cold)**: Run agent without memory store. Capture real tool calls, errors, latency, tokens, cost.
     - **Distillation**: Call `ToolReflectionEngine.reflect_on_execution()` to distill playbooks into `ToolMemoryStore`.
     - **Pass 2 (Warm)**: Run agent with memory store injected into system prompt. Capture real reduction in calls, zero errors, lower latency, and reduced tokens.
     - Return **dynamically computed deltas** from genuine trace events.

---

## 4. Deep-Dive Subsystem Analysis

### 4.1 Inference Providers & Voice
* **TensorMux (`apps/api/app/providers/tensormux.py`)**: Targets `https://api.tensormux.com/v1` with model `glm-4-7-flash`. Uses standard OpenAI client. Fully functional.
* **AI Grants OpenAI (`apps/api/app/providers/aigrants.py`)**: Targets `https://api.openai.com/v1` with `gpt-5-nano`. Fully functional.
* **Smallest.ai Voice (`apps/api/app/providers/voice.py`)**: Targets `https://waves-api.smallest.ai/api/v1/lightning-v3.1/get_speech`. Fully functional; generates real audio byte stream.
* **Deterministic Mock (`apps/api/app/providers/mock.py`)**: Deterministic provider for fast, reproducible offline testing. Used in CI test suite (`FORGE_TEST_MODE=1`).

### 4.2 DevOps & Third-Party App Tool Harnesses
* **Linear Tool (`apps/api/app/tools/third_party_apps.py:LinearAPITool`)**:
  - Requires 36-char team UUID (e.g. `'550e8400-e29b-41d4-a716-446655440001'`). Rejects `'CORE'` with 422.
  - Requires integer priority 1–4. Rejects `'urgent'` with 400.
  - Requires `'assignee_id'` when moving to `'In Progress'`.
* **Slack Tool (`apps/api/app/tools/third_party_apps.py:SlackAPITool`)**:
  - Rejects postings to `#enterprise-escalations` without `[SLA-ALERT]` and `customer_id` with 400.
* **CRM Tool (`apps/api/app/tools/third_party_apps.py:CRMAPITool`)**:
  - Provides enterprise tier details and contractual SLA thresholds.
* **GitHub & Sentry Tools (`apps/api/app/tools/devops_tools.py`)**:
  - Simulates branch protections (requiring PR and reviews before pushing to `main`).
  - Simulates Sentry issue triage and resolution workflows.

### 4.3 Agent Runtime, Reflection, and Memory Store
* **`AgentRuntime` (`apps/api/app/agents/runtime.py`)**:
  - Implements the complete ReAct paradigm: Prompt formulation → Model invocation → Tool execution → Error capture → Multi-turn continuation → Verifier validation.
  - Injects `ToolMemoryStore.format_for_prompt()` into the agent's system prompt if present.
  - Calls `ToolReflectionEngine.reflect_on_execution()` at runtime completion to distill newly encountered tool errors into persistent playbooks.
* **`ToolMemoryStore` (`apps/api/app/memory/tool_memory.py`)**:
  - Stores rules indexed by `tool_name`, `category`, `pattern_trigger`, `learned_rule`, `evidence`, and `confidence`.
  - Backed by SQLite table `tool_memories`.
* **`ToolReflectionEngine` (`apps/api/app/agents/reflection.py`)**:
  - Contains deterministic heuristics for pattern matching against tool responses and error messages.
  - Synthesizes `ToolPlaybookEntry` objects with confidence scores.

### 4.4 The Cold → Warm Learning Loop: Gap Analysis
* **The Route**: `POST /api/experiments/{id}/learning-run` handled by `ExperimentService.run_learning_loop()`.
* **What is Real**:
  - SQLite database record creation for `ToolPlaybookEntry`.
  - Real LLM call for executive reflection summary using configured provider.
  - SHA-256 hashed trace event emissions (`AGENT_STARTED`, `SELF_REFLECTION_COMPLETED`, `AGENT_COMPLETED`).
* **What is Simulated**:
  - The returned metric block (`run_1_cold` and `run_2_warm`) uses hardcoded integers and floats (e.g. 6 tool calls vs 2 tool calls, 5.2s vs 1.3s).
  - The actual `AgentRuntime.run()` method is not invoked inside this function.

---

## 5. What We Can Truthfully Claim Today

1. **Autonomous Architecture & ReAct Engine**: FORGE possesses a fully implemented, sandboxed ReAct runtime capable of calling local and simulated SaaS tools, parsing structured arguments, catching runtime exceptions, and verifying results.
2. **Persistent Tool Memory & Prompt Augmentation**: FORGE successfully stores learned operational heuristics in SQLite and automatically formats active playbooks into agent system prompts on subsequent executions.
3. **Autonomous Self-Reflection**: FORGE analyzes failed tool executions to extract generalized rules with confidence scores.
4. **Autonomous Agent Architecture Evolution**: FORGE implements a complete genetic/iterative evolution engine that benchmarks agents, detects failure modes, proposes targeted mutations (prompt, tools, verifier, temperature), and evaluates candidates across a Pareto front.
5. **Cryptographic Provenance**: Every state transition, tool call, mutation, and evaluation is recorded in a SHA-256 tamper-evident hash chain.
6. **Live Multi-Modal Presentation**: Real-time event streaming via SSE to a Next.js dashboard, with live voice debriefs synthesized via Smallest.ai.

---

## 6. Prioritized Remediation Plan (What Must Be Fixed)

### Priority 1: Dynamic Learning Loop Engine (Section S1)
* **Goal**: Replace the hardcoded metrics in `ExperimentService.run_learning_loop` with genuine sequential execution of `AgentRuntime.run()`.
* **Design**:
  1. Define a benchmark task (e.g. `tpa_001`: "Triage Enterprise Customer Incident").
  2. **Run 1 (Cold Execution)**:
     - Instantiate `AgentRuntime` with clean `ToolMemoryStore` (zero playbooks).
     - Run against task in isolated sandbox.
     - Agent naturally attempts naive tool calls, hits Linear 422 UUID error and Slack 400 tag error.
     - Agent retries, resolves, and completes.
     - Compute real metrics: count of tool calls, errors encountered, elapsed wall-clock latency, token usage, cost.
  3. **Reflection & Distillation**:
     - `ToolReflectionEngine` extracts playbooks from Run 1 trace into `ToolMemoryStore`.
     - Sync memory store to SQLite.
  4. **Run 2 (Warm Execution)**:
     - Instantiate new `AgentRuntime` with populated `ToolMemoryStore`.
     - System prompt now contains the learned UUID and Slack tag playbooks.
     - Run identical task.
     - Agent executes directly without exploratory errors.
     - Compute real metrics: tool calls, errors (0), elapsed latency, tokens, cost.
  5. **Dynamic Metric Delta**:
     - Compute actual empirical deltas: Δcalls, Δlatency, Δcost, Δaccuracy.
     - Return the genuine empirical report to the frontend.

### Priority 2: Update End-to-End Test Suite
* Update `apps/api/tests/test_learning_loop_end_to_end.py` to assert against genuine runtime executions rather than static payload assertions.
* Ensure deterministic mock provider supports both cold and warm execution paths with reproducible deltas.

---

## 7. What We Should NOT Touch (Stability Invariants)

To prevent regressions, the following verified systems are frozen:
1. **Core Database Models**: `apps/api/app/models/entities.py` (Do not alter table schemas or relationships).
2. **Provenance Hasher**: `apps/api/app/provenance/hasher.py` (The canonical JSON serialization and SHA-256 chaining is complete and 100% verified).
3. **Pareto Acceptance Engine**: `apps/api/app/evolution/acceptance.py` (Multi-objective scoring mathematics are sound).
4. **Third-Party App Logic**: `apps/api/app/tools/third_party_apps.py` (The error codes and payloads are already calibrated).
5. **Existing 18 Unit Tests**: Must remain 100% green at all times.

---

## 8. Recommended Next Section: S1 — Dynamic Learning Loop Engine

With repository ground truth established, the immediate next milestone is **Section S1**:
1. Implement dynamic dual-pass execution inside `ExperimentService.run_learning_loop`.
2. Ensure live SSE events stream for both cold and warm passes.
3. Compute dynamic cost, latency, and tool-call deltas from genuine `AgentState` records.
4. Verify with offline deterministic tests and live LLM integration.
