# FORGE S8-A — Frontend Audit Report

**Audit Date**: September 6, 2026  
**Auditor**: Automated Forensic Frontend Inspection Engine  
**Target Codebase**: `apps/web/` (Next.js 14.2.35, Tailwind CSS, TypeScript)  
**Backend Reference**: `apps/api/` (FastAPI, SQLite, SQLAlchemy)  
**Production Build Status**: `npm run build` exited with code 0 (5/5 static/dynamic routes verified)  

---

## 1. Executive Summary

This forensic audit evaluates the actual frontend implementation of the FORGE platform against the ground-truth architecture, backend API contracts, and evidence verification standards established in sections S0–S7.

Every screen, tab, component, and displayed value was audited by inspecting the TypeScript source code (`apps/web/app/**`, `apps/web/components/**`, `apps/web/lib/**`), tracking data flow from backend endpoints to rendered JSX, and verifying whether displayed metrics originate from **`REAL API DATA`**, **`MOCK DATA`**, **`HARDCODED DATA`**, or **`PARTIAL`** implementations.

### Summary of Audit Findings:
1. **Core Evolution & Benchmark UI is Fully Dynamic (`REAL API DATA`)**:
   - Experiment management, generation timelines, generation metrics (accuracy, reliability, cost, latency, composite score), declarative `AgentSpec` inspection, mutation before/after diffs, and live Server-Sent Events (SSE) tracing are all connected directly to real backend API endpoints.
2. **Production Build Succeeded**:
   - `npm run build` compiles cleanly with zero TypeScript errors and zero lint failures.
3. **Four Significant Hardcoded Fixtures Discovered**:
   - **Dashboard Provenance Card**: Renders static `<div ...>SHA-256 Valid</div>` without querying backend provenance.
   - **Causal Evidence Section in Learning Tab**: Lines 739–862 of `apps/web/app/experiments/[id]/page.tsx` hardcode 3 static cards (Linear UUID slug failure, Slack SLA tag violation, Linear integer priority failure) directly in JSX rather than fetching real causal data.
   - **Economic Savings Label**: Line 372 of `apps/web/app/experiments/[id]/page.tsx` hardcodes `Empirical Savings: -70.8% per task`.
   - **Navbar Provider Badge**: Hardcodes `"Inference: TensorMux (GLM-4.7-Flash)"` rather than querying `/api/providers/status`.
4. **S7-D Evidence API Is Completely Unwired**:
   - The read-only Causal Evidence API (`GET /api/experiments/{id}/evidence` and `GET /api/generations/{id}/evidence`) implemented in S7-D is **not present** in `apps/web/lib/api.ts` and is **never called** by the frontend.
5. **AO Status is Completely Missing from Frontend**:
   - Backend exposes `/api/ao/status`, `/api/ao/doctor`, and `/api/ao/diagnostics`, but there are zero components, routes, or API bindings in the web UI.

---

## 2. Inventory of Existing Screens & Routes

| Route | Page File | Purpose / Role |
| :--- | :--- | :--- |
| **`/`** | `apps/web/app/page.tsx` | **Dashboard**: System overview, active experiment metrics, global generation count, and experiments table. |
| **`/experiments/new`** | `apps/web/app/experiments/new/page.tsx` | **Create Experiment**: Form to define agent goal, benchmark target, available tools, and max generations. |
| **`/experiments/[id]`** | `apps/web/app/experiments/[id]/page.tsx` | **Experiment Detail & Workspace**: Main operational hub containing scorecards, action triggers, and 4 tab views. |
| **`/experiments/[id]/generations/[genId]`** | `apps/web/app/experiments/[id]/generations/[genId]/page.tsx` | **Generation Detail & Mutation Inspector**: Declarative `AgentSpec` breakdown and architectural before/after diffs. |
| **`/experiments/[id]/compare`** | `apps/web/app/experiments/[id]/compare/page.tsx` | **Generation Comparison**: Side-by-side performance table comparing any two generations with computed deltas. |

---

## 3. Inventory of Components & Tabs

| Component / Tab Name | Location | Primary Purpose |
| :--- | :--- | :--- |
| **Navbar** | `apps/web/components/Navbar.tsx` | Persistent navigation header, API health indicator, inference provider badge, "New Experiment" CTA. |
| **Root Layout** | `apps/web/app/layout.tsx` | HTML shell, dark mode styling, Navbar wrapper, and footer. |
| **Evolution Timeline Tab** | `apps/web/app/experiments/[id]/page.tsx` (`activeTab === 'timeline'`) | Chronological list of all evaluated generations ($G_0, G_1, \dots$), acceptance status, scorecards, and rejection reasons. |
| **Tool Memory & Learning Tab** | `apps/web/app/experiments/[id]/page.tsx` (`activeTab === 'learning'`) | Tool memory playbooks grid, Run 1 vs Run 2 learning loop execution, efficiency delta scoreboard, and causal cards. |
| **Live Execution Trace Tab** | `apps/web/app/experiments/[id]/page.tsx` (`activeTab === 'console'`) | Real-time console log streaming execution events via Server-Sent Events (`/api/experiments/{id}/stream`). |
| **Cryptographic Provenance Tab** | `apps/web/app/experiments/[id]/page.tsx` (`activeTab === 'provenance'`) | SHA-256 event chain verification card, genesis root hash, latest event hash, and re-verification trigger. |
| **Voice Debrief Players** | `[id]/page.tsx`, `[genId]/page.tsx` | HTMLAudioElement integration streaming synthesized debrief audio from Smallest.ai Waves (`/narrate`). |

---

## 4. Comprehensive Data Source Classification Table

For every major displayed value across the frontend, the data source is classified as:
* **`REAL API DATA`**: Dynamically fetched from a real backend REST/SSE endpoint.
* **`MOCK DATA`**: Simulated mock data returned by an endpoint or synthetic generator.
* **`HARDCODED DATA`**: Fixed literals or static JSX elements written directly in frontend code.
* **`PARTIAL`**: Mix of dynamic data with hardcoded fallbacks or unverified assumptions.

### 4.1 Global & Dashboard (`/`)

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Navbar API Health Status** | **`REAL API DATA`** | `Navbar.tsx:12-15` | Calls `api.getHealth()` (`GET /api/health`). Toggles green/red dot and "API Online/Offline". |
| **Navbar Inference Provider** | **`HARDCODED DATA`** | `Navbar.tsx:37` | Text `<span ...>Inference: TensorMux (GLM-4.7-Flash)</span>`. Does not query `/api/providers/status`. |
| **Active Experiments Count** | **`REAL API DATA`** | `page.tsx:65` | `experiments.length` derived from `api.getExperiments()` (`GET /api/experiments`). |
| **Top Generation Score** | **`REAL API DATA`** | `page.tsx:75` | Calculated from `e.best_accuracy` across all fetched experiments. |
| **Generations Evaluated** | **`REAL API DATA`** | `page.tsx:85` | Sum of `e.generations_count` across all fetched experiments. |
| **Dashboard Provenance Card** | **`HARDCODED DATA`** | `page.tsx:94` | Static text `<div ...>SHA-256 Valid</div>`. No API call to `/api/experiments/{id}/provenance` or global validator. |
| **Experiments Table** | **`REAL API DATA`** | `page.tsx:130-200` | Displays real `id`, `name`, `goal`, `benchmark_id`, `generations_count`, `best_accuracy`, `best_reliability`, and `status`. |

### 4.2 Create Experiment (`/experiments/new`)

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Form Inputs (Name, Goal, Max Gen)** | **`USER INPUT`** | `new/page.tsx:19-29` | React form state, editable by user. |
| **Benchmark Target Dropdown** | **`HARDCODED DATA`** | `new/page.tsx:124-125` | Only contains `<option value="software_engineering">`. Does not call `GET /api/benchmarks`. Excludes `third_party_automation`. |
| **Available Tools List** | **`HARDCODED DATA`** | `new/page.tsx:9-15` | Static local array `AVAILABLE_TOOLS` (5 tools). Does not call `GET /api/tools`. |
| **Form Submit (`createExperiment`)** | **`REAL API DATA`** | `new/page.tsx:49-56` | Sends POST request to `/api/experiments`. Navigates to `/experiments/${exp.id}` upon success. |

### 4.3 Experiment Detail (`/experiments/[id]`)

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Experiment Header Metadata** | **`REAL API DATA`** | `[id]/page.tsx:213-237` | Real `name`, `status`, `goal`, `benchmark_id`, `tool_ids` from `api.getExperiment(id)`. |
| **Task Scope Selector** | **`USER INPUT`** | `[id]/page.tsx:244-254` | Sets `taskLimit` state (1, 3, 5, 10 tasks), passed as query param to `/run` and `/evolve`. |
| **Action: Generate G0 Agent** | **`REAL API DATA`** | `[id]/page.tsx:159-169` | Calls `api.generateAgent(id)` (`POST /api/experiments/{id}/generate`). |
| **Action: Run Benchmark** | **`REAL API DATA`** | `[id]/page.tsx:171-181` | Calls `api.runBenchmark(id, taskLimit)` (`POST /api/experiments/{id}/run`). |
| **Action: Evolve Agent** | **`REAL API DATA`** | `[id]/page.tsx:183-193` | Calls `api.evolveAgent(id, taskLimit)` (`POST /api/experiments/{id}/evolve`). |
| **Scorecard: Accuracy** | **`REAL API DATA`** | `[id]/page.tsx:302-306` | Real `metrics.accuracy`, `successful_tasks`, `total_tasks` from `currentGen.metrics`. |
| **Scorecard: Reliability** | **`REAL API DATA`** | `[id]/page.tsx:310-314` | Real `metrics.reliability` from `currentGen.metrics`. |
| **Scorecard: Cost / Task** | **`REAL API DATA`** | `[id]/page.tsx:319-322` | Real `metrics.avg_cost_per_task` and `total_tokens` from `currentGen.metrics`. |
| **Scorecard: Avg Latency** | **`REAL API DATA`** | `[id]/page.tsx:327-330` | Real `metrics.avg_latency_ms` and `total_tool_calls` from `currentGen.metrics`. |
| **Scorecard: Composite Score** | **`REAL API DATA`** | `[id]/page.tsx:334-337` | Real `metrics.composite_score` from `currentGen.metrics`. |
| **Sponsor Credit Pool Badges** | **`HARDCODED DATA`** | `[id]/page.tsx:353-361` | Static badges ("TensorMux MoE", "OpenAI", "Smallest.ai"). Not fetched from API. |
| **Total Tokens Processed** | **`REAL API DATA`** | `[id]/page.tsx:368` | Dynamically summed: `generations.reduce((acc, g) => acc + (g.metrics?.total_tokens || 0), 0)`. |
| **Empirical Savings Metric** | **`HARDCODED DATA`** | `[id]/page.tsx:372` | Hardcoded string `"-70.8%"` in JSX: `<span ...>-70.8%</span> per task`. |

### 4.4 Generation Timeline Tab

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Generation Number & ID** | **`REAL API DATA`** | `[id]/page.tsx:451, 471` | `gen.generation_number`, `gen.id` from `api.getGenerations(id)`. |
| **Generation Status** | **`REAL API DATA`** | `[id]/page.tsx:461-469` | `gen.status` (`ACCEPTED`, `REJECTED`, `COMPLETED`). |
| **Best Model Badge** | **`REAL API DATA`** | `[id]/page.tsx:457` | Condition `gen.id === experiment.best_generation_id`. |
| **Timeline Metrics & Deltas** | **`REAL API DATA`** | `[id]/page.tsx:476-500` | Real accuracy, reliability, cost, composite score, and calculated delta against previous generation. |
| **Voice Debrief Audio** | **`REAL API DATA`** | `[id]/page.tsx:78-107` | Streams live audio from `api.getNarrationAudioUrl(gen.id)` (`GET /api/generations/{id}/narrate`). |
| **Rejection Rationale** | **`PARTIAL`** | `[id]/page.tsx:532` | Uses `gen.rejection_reason` if non-null, but falls back to static string `"Candidate failed multi-objective Pareto trade-off..."`. |

### 4.5 Live Execution Trace Tab

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Trace Events Stream** | **`REAL API DATA`** | `[id]/page.tsx:136-151` | Connects to real SSE endpoint: `new EventSource("${API_BASE}/experiments/${id}/stream")`. |
| **Trace Events History** | **`REAL API DATA`** | `[id]/page.tsx:116` | Initial fetch via `api.getEvents(id, 80)` (`GET /api/experiments/{id}/events`). |
| **Event Attributes** | **`REAL API DATA`** | `[id]/page.tsx:564-581` | Real `ev.timestamp`, `ev.type`, and stringified `ev.payload`. |

### 4.6 Cryptographic Provenance Tab

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Provenance Validity** | **`REAL API DATA`** | `[id]/page.tsx:596, 602` | Real `provenance.is_valid` from `api.getProvenance(id)` (`GET /api/experiments/{id}/provenance`). |
| **Provenance Message & Count** | **`REAL API DATA`** | `[id]/page.tsx:605` | Real `provenance.message`, `provenance.total_events`. |
| **Genesis & Latest Hashes** | **`REAL API DATA`** | `[id]/page.tsx:622, 626` | Real `provenance.genesis_hash`, `provenance.latest_hash` (SHA-256 strings). |
| **Re-verify Trigger** | **`REAL API DATA`** | `[id]/page.tsx:611-615` | Calls `loadData()` to re-query `/api/experiments/{id}/provenance`. |

### 4.7 Tool Memory & Learning Tab

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Tool Playbooks List** | **`REAL API DATA`** | `[id]/page.tsx:882-923` | Real entries from `api.getToolMemory(id)` (`GET /api/experiments/{id}/tool-memory`). Displays tool, category, confidence, observation count, trigger, rule, evidence. |
| **Execute Learning Loop** | **`REAL API DATA`** | `[id]/page.tsx:64-76` | Calls `api.runLearningLoop(id)` (`POST /api/experiments/{id}/learning-run`). |
| **Efficiency Delta Scoreboard** | **`PARTIAL`** | `[id]/page.tsx:678-725` | Displays `tool_calls`, `latency_ms`, `cost_usd`, `tokens`, `errors_prevented` from `learningReport`. Frontend renders API response dynamically, but backend `run_learning_loop` currently returns a pre-compiled simulation dictionary (identified in S0 audit). |
| **Learning Voice Debrief** | **`REAL API DATA`** | `[id]/page.tsx:654` | Plays audio from `GET /api/experiments/{id}/learning-narrate`. |
| **Causal Evidence Section** | **`HARDCODED DATA`** | `[id]/page.tsx:739-862` | **3 completely hardcoded cards in JSX**: (1) Linear UUID slug, (2) Slack SLA alert tag, (3) Linear integer priority. Does NOT read from API or DB. |

### 4.8 Generation Detail (`/experiments/[id]/generations/[genId]`)

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Generation Header & Metrics** | **`REAL API DATA`** | `[genId]/page.tsx:94-141` | Real number, ID, status, accuracy, reliability, cost, latency from `api.getGenerationDetail(genId)`. |
| **Mutation Cards** | **`REAL API DATA`** | `[genId]/page.tsx:145-173` | Real `mutation.type`, `target`, `observed_failure`, `expected_effect`, `reason`. |
| **Before / After Spec Diffs** | **`REAL API DATA`** | `[genId]/page.tsx:175-184` | Real JSON strings of `mutation.before` and `mutation.after`. |
| **Declarative AgentSpec** | **`REAL API DATA`** | `[genId]/page.tsx:194-247` | Real model, planner, verifier, orchestration, retry_policy, memory, system prompt, tools. |
| **Model Subtitle** | **`HARDCODED DATA`** | `[genId]/page.tsx:198` | Hardcoded text: `<p ...>GLM-4.7-Flash 30B MoE via TensorMux</p>`. |

### 4.9 Generation Comparison (`/experiments/[id]/compare`)

| Displayed Value / Element | Classification | Source Code Reference | Exact Data Source & Inspection Details |
| :--- | :--- | :--- | :--- |
| **Generation Dropdowns (A & B)**| **`REAL API DATA`** | `compare/page.tsx:68-91` | Populated dynamically from `api.getGenerations(expId)`. |
| **Side-by-Side Metrics Table** | **`REAL API DATA`** | `compare/page.tsx:106-170` | Compares `accuracy`, `reliability`, `cost`, `latency`, `composite_score` and calculates deltas dynamically. |

---

## 5. Audit of Specific Requested Subsystems

### 5.1 Failure Analysis
- **Status**: **`PARTIAL / FRAGMENTED`**
- **Existing**:
  - `rejection_reason` in Generation Timeline (`gen.status === 'REJECTED'`).
  - `mutation.observed_failure` and `mutation.reason` in Generation Detail.
  - Failures in Live Trace console.
- **Missing / Omitted**:
  - `Generation.metrics.failure_breakdown` (e.g. `{"TOOL_EXECUTION_FAILURE": 2, "VERIFICATION_FAILURE": 1}`) is returned by the API but is **never rendered anywhere in the UI**.
  - There is no failure distribution chart or failure cluster view.

### 5.2 Causal Evidence
- **Status**: **`HARDCODED DATA / UNWIRED API`**
- **Existing**:
  - The "Tool Memory & Learning" tab has a section titled *"Causal Evidence: How Failures Directly Caused Zero-Shot Execution"*, but all 3 cards are **static hardcoded JSX elements**.
- **Critical Disconnect**:
  - In section S7-D, read-only causal evidence APIs were added: `GET /api/experiments/{id}/evidence` and `GET /api/generations/{id}/evidence`.
  - The frontend has **zero calls** to these endpoints, and `apps/web/lib/api.ts` does not even declare the method.

### 5.3 Provenance
- **Status**: **`REAL API DATA`** on Detail tab; **`HARDCODED DATA`** on Dashboard.
- **Detail Page**: The "Cryptographic Provenance" tab invokes `api.getProvenance(id)` and displays true cryptographic status (`is_valid`), genesis hash, and latest event hash.
- **Dashboard**: The provenance card on the main dashboard renders a static text string `"SHA-256 Valid"` regardless of actual database state.

### 5.4 Voice Debrief
- **Status**: **`REAL API DATA`**
- **Existing**:
  - Real HTMLAudioElement player with play/pause state handling.
  - Targets `/api/generations/{id}/narrate` and `/api/experiments/{id}/learning-narrate`.
  - Streams genuine WAV audio synthesized via Smallest.ai Waves.

### 5.5 AO Status
- **Status**: **`COMPLETELY MISSING`**
- **Backend**: Exposes `/api/ao/status`, `/api/ao/doctor`, `/api/ao/diagnostics`.
- **Frontend**: Zero routes, zero components, zero API client methods.
- *Architectural Note*: In accordance with hackathon instructions, AO represents the development process while FORGE represents the agent execution runtime. However, an operational status badge or diagnostics drawer for the orchestrator is absent.

### 5.6 Metrics & Economics
- **Status**: **`REAL API DATA`** (Core) / **`HARDCODED DATA`** (Labels)
- **Scorecards**: Accuracy, reliability, cost/task, latency, composite score, and token counters are genuine metrics computed by the evaluation engine.
- **Economics Banner**: The text `"Empirical Savings: -70.8% per task"` is hardcoded, and the sponsor credit badges are static strings.

---

## 6. Broken Links, API Disconnects & Inconsistencies

1. **Unwired S7-D Evidence API**:
   - Backend endpoint `GET /api/experiments/{id}/evidence` returns structured causal relationships (`generation`, `parent_generation`, `metrics`, `failures`, `memory`, `mutations`, `decision`, `provenance`), but the frontend never calls it.
2. **Missing Benchmark Option in `/experiments/new`**:
   - The `<select>` element only has `<option value="software_engineering">`. The backend's second verified benchmark, `third_party_automation` (10 tasks), cannot be chosen from the UI.
3. **Static Available Tools in `/experiments/new`**:
   - Form uses a hardcoded array `AVAILABLE_TOOLS` instead of fetching available tools from `GET /api/tools`.
4. **Unwired Multi-Generation Loop (`/evolve-loop`)**:
   - Backend endpoint `POST /api/experiments/{id}/evolve-loop` (implemented in S6-J) can execute $G_0 \to G_1 \to G_2 \dots G_n$ autonomously. The UI only provides a single-step "Evolve Agent" button (`/evolve`).
5. **Ignored `failure_breakdown` Field**:
   - `metrics.failure_breakdown` is part of the `Generation.metrics` interface in `lib/api.ts`, but no component renders it.
6. **Unwired Provider Status**:
   - Backend endpoint `GET /api/providers/status` reports active provider and model status, but the Navbar and Experiment Detail views display hardcoded strings.

---

## 7. UX & Usability Problems

1. **No Causal Lineage Visualization**:
   - While generations are listed sequentially in a vertical list, there is no DAG or graph visualizer showing parent $\to$ mutation $\to$ candidate relationships or rejected branch history.
2. **No Failure Drilldown Modal**:
   - Users cannot click on a failed task to inspect the exact test output, stack trace, or diff that caused the failure.
3. **No Event Filtering in Trace Stream**:
   - The Live Execution Trace console displays all event types in an unfilterable stream, making it difficult to isolate `TOOL_CALL`, `ERROR`, or `VERIFICATION` events during high-turn runs.
4. **Compare Page Lacks Spec Diff**:
   - The `/compare` page compares numeric metrics in a table, but does not display a side-by-side visual diff of the two `AgentSpec` configurations.
5. **No Confirmation / Warning on Multi-Turn Execution**:
   - Triggering "Evolve Agent" or "Run Benchmark" starts execution immediately without showing the estimated task count or token cost.

---

## 8. Production Build Verification Result

The production build was executed inside `apps/web/`:

```bash
cd apps/web && npm run build
```

### Exact Output:
```text
> forge-web@1.0.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
<w> [webpack.cache.PackFileCacheStrategy] Caching failed for pack: Error: Unable to snapshot resolve dependencies
<w> [webpack.cache.PackFileCacheStrategy] Caching failed for pack: Error: Unable to snapshot resolve dependencies
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/5) ...
   Generating static pages (1/5) 
   Generating static pages (2/5) 
   Generating static pages (3/5) 
 ✓ Generating static pages (5/5)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                Size     First Load JS
┌ ○ /                                      3.41 kB         101 kB
├ ○ /_not-found                            873 B          88.2 kB
├ ƒ /experiments/[id]                      8.97 kB         106 kB
├ ƒ /experiments/[id]/compare              2.43 kB        99.6 kB
├ ƒ /experiments/[id]/generations/[genId]  3.54 kB         101 kB
└ ○ /experiments/new                       3.15 kB         100 kB
+ First Load JS shared by all              87.3 kB
  ├ chunks/117-f48404e42cb32be4.js         31.7 kB
  ├ chunks/fd9d1056-0807e69ea9c303ac.js    53.6 kB
  └ other shared chunks (total)            1.95 kB

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

- **Exit Code**: `0`
- **Errors**: `0`
- **Lint Failures**: `0`
- **Generated Routes**: 5/5 routes successfully compiled and optimized.

---

## 9. Highest-Priority Fixes (Roadmap for S8-B / S8-C)

1. **Wire S7-D Evidence API into Frontend (`Priority: P0`)**:
   - Add `getEvidence: (id: string) => fetchJson<EvidenceReport>(`/experiments/${id}/evidence`)` to `apps/web/lib/api.ts`.
   - Replace the 3 static hardcoded cards in `apps/web/app/experiments/[id]/page.tsx` with dynamic cards rendered from `evidence.failures`, `evidence.memory`, and `evidence.mutations`.
2. **Connect Dashboard Provenance Card (`Priority: P1`)**:
   - Make the Dashboard provenance card dynamic by checking provenance validity of experiments rather than displaying static `"SHA-256 Valid"`.
3. **Enable `third_party_automation` in Create Experiment (`Priority: P1`)**:
   - Fetch benchmarks dynamically via `GET /api/benchmarks` so users can run experiments against SaaS tools (Linear, Slack, CRM) as well as software engineering tasks.
4. **Display `failure_breakdown` in Metrics Scorecards (`Priority: P1`)**:
   - Render failure distribution badges (e.g. `VERIFICATION_FAILURE: 1`, `TOOL_SELECTION_FAILURE: 2`) in the Generation Timeline and Generation Detail views.
5. **Expose Multi-Generation Evolution Loop (`Priority: P2`)**:
   - Add a "Run Multi-Gen Evolution" button to trigger `POST /api/experiments/{id}/evolve-loop` with a generation count cap.
6. **Dynamic Economics Savings Calculation (`Priority: P2`)**:
   - Replace hardcoded `"-70.8%"` with empirical savings calculated from $(cost_{G0} - cost_{G_{best}}) / cost_{G0}$.
7. **Add Lightweight AO Status Badge (`Priority: P3`)**:
   - Display a non-intrusive indicator in the Navbar showing orchestrator status via `GET /api/ao/status`, keeping the development workflow visible without conflating it with the FORGE runtime.

---

## 10. Audit Conclusion

The FORGE frontend possesses a robust, fully compiling Next.js foundation with dynamic metric scorecards, SSE streaming, real mutation before/after diffs, and cryptographic provenance checks. However, several high-value evidence displays (specifically the Causal Evidence chain, Dashboard provenance status, and benchmark selection) currently rely on hardcoded JSX or remain unwired from the S7-D API.

**S8-A STATUS: VERIFIED**
