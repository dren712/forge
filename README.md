# FORGE

### Tagline
> **Agents don't just run. They evolve.**

**Syndicate by Maximor — Track 1: Automated Agent Engineering**  
**Inference Partner:** TensorMux (`glm-4-7-flash`)

---

## 1. What is FORGE?

FORGE is an autonomous **agent engineering and evolution platform**. Instead of treating AI agents as fixed prompts or rigid scripts, FORGE treats agent design as an **empirical optimization problem**.

Given:
1. A goal
2. A set of available tools
3. A benchmark / evaluator

FORGE autonomously runs the full evolutionary loop:
```text
      GOAL
        ↓
  DESIGN AGENT (G0)
        ↓
    RUN AGENT
        ↓
CAPTURE EXECUTION
        ↓
    EVALUATE
        ↓
 ANALYZE FAILURES (Fixed Taxonomy)
        ↓
 PROPOSE IMPROVEMENT (Evidence-Driven Mutation)
        ↓
  MUTATE AGENT (Candidate G1)
        ↓
  RUN CANDIDATE
        ↓
     COMPARE
        ↓
 ACCEPT / REJECT (Pareto-Aware Objective)
        ↓
 NEW GENERATION
        ↓
     REPEAT
```

Every displayed metric and architectural mutation comes directly from actual stored executions.

---

## 2. Core Hackathon Thesis

> **FORGE automatically builds and evolves specialized agents using evidence from their previous failures.**

- **Not a generic chatbot.**
- **Not a simple prompt optimizer.**
- **Not a fake demo.**
- It is a real, reproducible **Agent Evolution Engine** with multi-dimensional tracking:
  - **Accuracy** (task completion pass rate)
  - **Reliability** (verification pass rate, tool error minimization, clean exits, recovery)
  - **Cost** (token tracking & price modeling)
  - **Latency** (task execution time & tool latency)
  - **Cryptographic Provenance** (SHA-256 unbroken hash chain)

---

## 3. High-Level Architecture

```text
forge/
├── apps/
│   ├── api/                           # FastAPI backend
│   │   ├── app/
│   │   │   ├── core/                  # Database, logging, exceptions, settings
│   │   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── schemas/               # Declarative AgentSpec & API models
│   │   │   ├── providers/             # LLMProvider protocol + TensorMuxProvider
│   │   │   ├── agents/                # Architect, Runtime, State, Verifier
│   │   │   ├── tools/                 # Sandboxed repository, file editor, shell, test runner, search
│   │   │   ├── benchmarks/            # 10 Software Engineering benchmark tasks
│   │   │   ├── evaluation/            # Evaluator, scoring formulas, FailureAnalyzer
│   │   │   ├── evolution/             # MutationEngine, AcceptanceEngine, EvolutionEngine
│   │   │   ├── tracing/               # TraceEvent schemas & EventRecorder
│   │   │   ├── provenance/            # Cryptographic SHA-256 chain verifier
│   │   │   ├── services/              # Experiment orchestration & SSE streaming
│   │   │   └── main.py                # FastAPI entrypoint
│   │   └── tests/                     # 10 unit and integration tests (100% pass)
│   │
│   └── web/                           # Next.js 14 Developer Dashboard (TypeScript + Tailwind)
│       ├── app/                       # Dashboard, New Experiment, Command Center, Comparison
│       ├── components/                # Navbar, Timeline, TraceStream, Scorecards
│       └── lib/                       # Typed API client & SSE connector
│
├── benchmarks/
│   └── software_engineering/          # 10 isolated local repository fixtures with pytest suites
│
├── scripts/
│   ├── test_tensormux.py              # Connectivity verification for TensorMux endpoint
│   ├── seed_benchmark.py              # Benchmark inspection & integrity check
│   └── run_demo.py                    # Fully automated end-to-end evolution demo
│
└── docs/
    ├── architecture.md                # Detailed system design
    ├── evolution.md                   # Mutation operators & acceptance logic
    ├── benchmark.md                   # Benchmark tasks specification
    └── api.md                         # OpenAPI documentation
```

---

## 4. Primary Benchmark: Controlled Software Engineering Agent

The benchmark consists of **10 reproducible local micro-codebases** with isolated filesystems and automated pytest test suites:

1. **`task_01_simple_bug`**: Fix off-by-one boundary in pagination utility.
2. **`task_02_find_correct_file`**: Locate formatter module among utils and add ISO 8601 timestamp.
3. **`task_03_multi_file_change`**: Sync UserModel schema and UserSerializer output dictionary.
4. **`task_04_understand_existing_tests`**: Implement Tier 3 discount edge case matching test specs.
5. **`task_05_fix_failing_test`**: Fix ZeroDivisionError in statistics variance calculations.
6. **`task_06_ambiguous_requirement`**: Load database timeout with sane 30.0s fallback default.
7. **`task_07_avoid_unrelated_modifications`**: Fix auth token validation without touching billing code.
8. **`task_08_feature_implementation`**: Implement custom LRU cache decorator.
9. **`task_09_recovery_from_error`**: Support datetime serialization in custom JSON encoder and recover from errors.
10. **`task_10_verify_before_success`**: Strict semantic version parser requiring test suite verification.

---

## 5. TensorMux Inference Integration

FORGE is powered by **TensorMux**:
- **Base URL:** `https://api.tensormux.com/v1`
- **Model:** `glm-4-7-flash` (30B Mixture-of-Experts, 32K context window, agentic tool calling)
- **OpenAI Compatible Interface:** Implemented cleanly via `TensorMuxProvider(LLMProvider)` with token usage telemetry and automatic retries.

### Configure TensorMux:
Get your key at [https://app.tensormux.com](https://app.tensormux.com) (starts with `tmx_`), then edit `.env`:
```env
TENSORMUX_API_KEY=tmx_your_key_here
TENSORMUX_BASE_URL=https://api.tensormux.com/v1
TENSORMUX_MODEL=glm-4-7-flash
```

Test connectivity:
```bash
python scripts/test_tensormux.py
```

---

## 6. Cryptographic Provenance Chain

Every experiment in FORGE generates an audit-grade, tamper-evident event log.
Each event is cryptographically linked:
$$\text{event\_hash} = \text{SHA-256}(\text{previous\_event\_hash} + \text{canonical\_json}(\text{payload}))$$

- **Root Genesis Hash:** `0000000000000000000000000000000000000000000000000000000000000000`
- **Tamper Detection:** Any alteration of an event payload or sequence breaks the chain and is flagged instantly in the UI.

---

## 7. Quickstart Guide

### 1. Setup Environment
```bash
cd forge
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
cp .env.example .env
```

### 2. Run Autonomous Evolution Demo
Experience the full empirical evolution loop right in your terminal:
```bash
python scripts/run_demo.py
```

### 3. Run Backend Test Suite
```bash
cd apps/api
pytest -v tests/
```

### 4. Start the Full Application

**Terminal 1 (Backend API):**
```bash
cd apps/api
../../.venv/bin/uvicorn app.main:app --port 8000 --reload
```

**Terminal 2 (Web Developer UI):**
```bash
cd apps/web
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser!
