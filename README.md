<![CDATA[<div align="center">

# 🔥 FORGE

### Autonomous Agent Engineering & Evolution Engine

> **Agents don't just run. They evolve.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hackathon:** Syndicate by Maximor — Track 1: Automated Agent Engineering  
**Live Demo:** [forge-darshan-712.vercel.app](https://forge-darshan-712.vercel.app) • **API:** [forge-api-amow.onrender.com](https://forge-api-amow.onrender.com/api/health)

</div>

---

## 🧠 What is FORGE?

FORGE is an **autonomous agent engineering platform** that empirically diagnoses why AI agents fail, synthesizes targeted architectural mutations, and drives multi-generation improvements — all backed by cryptographic provenance.

Instead of manually tuning prompts or agent configurations, FORGE automates the entire improvement cycle:

```
Agent Fails → FORGE Diagnoses Why → Mutates Architecture → Re-evaluates → Accepts or Rejects → Repeat
```

The result: agents that **learn from their own operational failures** and **evolve their own architecture** across generations.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FORGE PLATFORM                                 │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────────┐   │
│  │   Next.js    │    │   FastAPI     │    │   Agent Orchestrator    │   │
│  │  Command     │◄──►│   Engine      │◄──►│   (AO) Development     │   │
│  │  Center      │    │              │    │   Harness              │   │
│  │  (Frontend)  │    │  • Architect  │    │                         │   │
│  │              │    │  • Evaluator  │    │  • Daemon management    │   │
│  │  • Dashboard │    │  • Evolver    │    │  • Health diagnostics   │   │
│  │  • Timeline  │    │  • Prover    │    │  • Harness detection    │   │
│  │  • Evidence  │    │  • Recorder  │    │  • Session tracking     │   │
│  │  • Console   │    │  • Memory    │    │                         │   │
│  │  • Learning  │    │              │    │  Routes:                │   │
│  │  • AO Panel  │    │              │    │  GET /api/ao/status     │   │
│  └──────┬───────┘    └──────┬───────┘    │  GET /api/ao/doctor     │   │
│         │                   │            │  GET /api/ao/diagnostics│   │
│         │                   │            └─────────────────────────┘   │
│         │                   │                                          │
│         │            ┌──────┴───────┐                                  │
│         │            │  PostgreSQL  │    ┌──────────────────────┐      │
│         │            │  / SQLite    │    │  Benchmark Suite     │      │
│         │            │              │    │  10 Software Eng     │      │
│         │            │  6 Tables:   │    │  tasks with real     │      │
│         │            │  experiments │    │  repos & test        │      │
│         │            │  generations │    │  harnesses           │      │
│         │            │  executions  │    └──────────────────────┘      │
│         │            │  trace_events│                                  │
│         │            │  mutations   │    ┌──────────────────────┐      │
│         │            │  tool_memory │    │  LLM Providers       │      │
│         │            └──────────────┘    │  • TensorMux (GLM)   │      │
│         │                                │  • OpenAI (GPT)      │      │
│         └────────────────────────────────│  • Smallest.ai Voice │      │
│                                          └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Monorepo Structure

```
forge/
├── apps/
│   ├── api/                    # FastAPI backend (Python)
│   │   ├── app/
│   │   │   ├── agents/         # AO integration bridge
│   │   │   ├── api/            # REST + SSE routes
│   │   │   ├── benchmarks/     # Benchmark registry & evaluator
│   │   │   ├── core/           # Config, database, logging
│   │   │   ├── evaluation/     # Task evaluation engine
│   │   │   ├── evolution/      # Mutation & Pareto gate
│   │   │   ├── memory/         # Persistent tool memory store
│   │   │   ├── models/         # SQLAlchemy ORM entities
│   │   │   ├── provenance/     # SHA-256 cryptographic hasher
│   │   │   ├── providers/      # LLM provider abstraction
│   │   │   ├── schemas/        # Pydantic request/response models
│   │   │   ├── services/       # Core experiment service (1187 lines)
│   │   │   ├── tools/          # Sandboxed agent tools
│   │   │   └── tracing/        # Event recorder & broadcaster
│   │   ├── tests/              # 119 unit tests
│   │   └── requirements.txt
│   └── web/                    # Next.js 14 frontend (TypeScript)
│       ├── app/
│       │   ├── page.tsx                  # Dashboard
│       │   └── experiments/
│       │       ├── new/page.tsx          # Create experiment
│       │       └── [id]/page.tsx         # Detail view (3600+ lines)
│       ├── components/
│       │   └── Navbar.tsx                # Global nav + AO modal
│       └── lib/
│           └── api.ts                    # Typed API client
├── benchmarks/
│   └── software_engineering/   # 10 real repo tasks with tests
├── docs/
│   ├── FINAL_EVIDENCE.md       # Championship verification report
│   └── deployment-audit.md     # PostgreSQL migration audit
└── scripts/                    # CLI utilities
```

---

## 🤖 Agent Orchestrator (AO) Integration

FORGE integrates with **Agent Orchestrator (AO)** as its development orchestration infrastructure. AO manages the autonomous coding agents that build and maintain FORGE itself — creating a meta-layer where **the tool that evolves agents was itself built by an orchestrated agent**.

### What AO Does in FORGE

| Component | Role |
|-----------|------|
| **AO Daemon** | Background process managing agent sessions, project registration, and harness lifecycle |
| **AO Doctor** | Health diagnostics — checks daemon status, SQLite integrity, harness authentication, Git token availability |
| **AO Status** | Real-time daemon state — PID, port, active sessions, registered projects |
| **AO Diagnostics** | Comprehensive audit: installation path, version, daemon reachability, harness config, auth status |
| **Development Harness** | Wraps coding agents (e.g., Claude Code) for autonomous file editing, testing, and PR workflows |

### AO in the FORGE UI

The **AO Development Orchestration** panel is accessible from the navbar (🧠 button). It displays:

- **Daemon Status**: Whether AO is running, its PID and port
- **Doctor Report**: `ao doctor` output showing component health checks
- **Harness Detection**: Which coding agent harness is configured (e.g., `claude-code`)
- **Authentication State**: Whether the harness can autonomously invoke agents

### AO API Endpoints

```bash
# Check if AO daemon is running
GET /api/ao/status
# → {"running": true, "pid": 12345, "port": 3001}

# Run health diagnostics
GET /api/ao/doctor
# → {"available": true, "installed": true, "daemon_ok": true, "sqlite_ok": true, ...}

# Full diagnostic audit
GET /api/ao/diagnostics
# → {"ao_installed": true, "version": "0.3.2", "daemon_reachable": true, ...}
```

### AO Code Integration

The integration lives in [`apps/api/app/agents/ao_integration.py`](apps/api/app/agents/ao_integration.py):

```python
class AOOrchestratorBridge:
    """
    Integration layer with Agent Orchestrator (AO) daemon and CLI.
    Orchestrates development workflows and coding agents for FORGE development.
    Separated strictly from runtime benchmark evaluations.
    """
    
    async def get_status(self) -> dict:
        """Executes 'ao status' to query daemon status."""
        
    async def run_doctor(self) -> dict:
        """Executes 'ao doctor' to check local health and agent harnesses."""
        
    async def get_diagnostics(self) -> dict:
        """Comprehensive audit: installation, reachability, authentication, invocation."""
```

> **Important Design Decision:** AO is strictly a *development harness* — it orchestrates the agents that build FORGE, but is **not** part of the benchmark evaluation pipeline. This separation ensures that FORGE's evolutionary results are independently reproducible without AO installed.

---

## 🔄 The Dual-Loop Evolution Engine

FORGE operates two complementary improvement loops:

### Inner Loop: Tool Learning & Persistent Memory

The agent encounters real enterprise API constraints, fails, reflects, and persists operational heuristics ("playbooks") into tool memory:

```
Tool Failure → Self-Reflection → Persistent Playbook → Better Next Execution
```

**Empirical Results:**

| Metric | Run 1 (Cold / Naive) | Run 2 (Warm / Memory) | Improvement |
|--------|:---:|:---:|:---:|
| **Tool Calls** | 6 | 2 | **−66.7%** |
| **Execution Latency** | 5.2s | 1.3s | **−75.0%** |
| **API Cost** | $0.0048 | $0.0014 | **−70.8%** |
| **Task Accuracy** | 50% | 100% | **+50 pts** |
| **Errors** | 3 | 0 | **3 prevented** |

### Outer Loop: Structural Agent Evolution

Repeated benchmark evaluations drive architectural mutations through a Pareto acceptance gate:

```
Benchmarks → Failure Clustering → Architectural Mutation → Pareto Gate → G(n+1)
```

The Pareto gate **rejects** mutations that don't improve the multi-objective trade-off:

```
CANDIDATE: accuracy +4%, reliability +1%, cost +74%, latency +39%
DECISION:  REJECTED — marginal gains don't justify cost/latency regression
```

---

## 🔐 Cryptographic Provenance

Every event in FORGE (spec design, tool interaction, error, reflection, mutation, acceptance decision) is permanently chained using SHA-256:

```
event_hash = SHA-256(previous_event_hash + canonical_json(payload))
```

The provenance chain is verifiable via:
- **API**: `GET /api/experiments/{id}/provenance`
- **UI**: Provenance tab with per-event hash inspection and tamper detection

---

## 🚀 Quick Start — Run Locally (Judges)

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (with npm)
- **Git**
- **(Optional)** [Agent Orchestrator (AO)](https://docs.agentorchestrator.com) — for the AO development panel

### 1. Clone & Setup

```bash
git clone https://github.com/dren712/forge.git
cd forge

# Backend setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt

# Frontend setup
cd apps/web && npm install && cd ../..
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Required — LLM provider for agent reasoning
TENSORMUX_API_KEY=your_tensormux_key
TENSORMUX_BASE_URL=https://api.tensormux.com/v1
TENSORMUX_MODEL=glm-4-7-flash

# Optional — Voice narration (Smallest.ai)
SMALLEST_API_KEY=your_smallest_key

# Optional — Database (defaults to local SQLite if not set)
# DATABASE_URL=postgresql://user:pass@host:port/db

# Environment
FORGE_ENV=development
```

> **Note:** Without `TENSORMUX_API_KEY`, the agent architect and benchmark runner cannot generate LLM responses. You can still browse existing experiment data in the UI.

### 3. Run Tests (119 Passing)

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/ -v
```

### 4. Launch Development Servers

**Terminal 1 — Backend:**
```bash
source .venv/bin/activate
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd apps/web
npm run dev
```

### 5. Open FORGE

- **Command Center:** [http://localhost:3000](http://localhost:3000)
- **API Health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (FastAPI auto-generated Swagger)

### 6. (Optional) AO Integration

If you have **Agent Orchestrator** installed locally:

```bash
# Verify AO is running
ao status
ao doctor

# FORGE will auto-detect the AO binary and display its status
# in the navbar 🧠 button → "AO Development Orchestration" panel
```

If AO is not installed, the panel will show "ao binary not found" — this is expected. AO is a development harness, not required for the core evolution engine.

---

## 📋 Full API Reference

### Core Experiment Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/experiments` | Create a new evolution experiment |
| `GET` | `/api/experiments` | List all experiments with metrics |
| `GET` | `/api/experiments/{id}` | Get experiment details |
| `POST` | `/api/experiments/{id}/generate` | Generate initial agent spec (G0) |
| `POST` | `/api/experiments/{id}/run` | Run benchmark on current generation |
| `POST` | `/api/experiments/{id}/evolve` | Mutate → benchmark → accept/reject |
| `POST` | `/api/experiments/{id}/evolve-loop` | Auto-evolve up to N generations |
| `POST` | `/api/experiments/{id}/learning-run` | Inner-loop: Cold vs Warm demonstration |

### Data & Evidence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/experiments/{id}/generations` | List all generations with metrics |
| `GET` | `/api/generations/{id}` | Generation detail + mutation info |
| `GET` | `/api/experiments/{id}/executions` | Task execution history |
| `GET` | `/api/experiments/{id}/events` | Trace events (chronological) |
| `GET` | `/api/experiments/{id}/provenance` | SHA-256 chain verification |
| `GET` | `/api/experiments/{id}/evidence` | Causal evidence inspection |
| `GET` | `/api/experiments/{id}/tool-memory` | Learned operational playbooks |

### Voice & Live Streaming

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/generations/{id}/narrate` | Voice debrief audio (Smallest.ai) |
| `GET` | `/api/experiments/{id}/learning-narrate` | Learning loop voice summary |
| `GET` | `/api/experiments/{id}/stream` | Server-Sent Events (SSE) live stream |

### Agent Orchestrator (AO)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/ao/status` | AO daemon running state |
| `GET` | `/api/ao/doctor` | AO health diagnostics |
| `GET` | `/api/ao/diagnostics` | Full audit (version, auth, harness) |

### Infrastructure

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/providers/status` | LLM provider configuration |
| `GET` | `/api/benchmarks` | Available benchmark suites |
| `GET` | `/api/tools` | Registered agent tools |

---

## 🖥️ Command Center UI

The Next.js Command Center provides 5 specialized views for each experiment:

### 1. Evolution Timeline
Visual generation history showing G0 → G1 → G2... with accuracy, reliability, cost, and latency metrics. Click any generation to inspect its agent spec, mutation diff, and execution count.

### 2. Generation Comparison
Side-by-side metric diff between any two generations. Shows delta calculations with improved/regressed indicators for accuracy, reliability, cost per task, latency, and composite score.

### 3. Live Execution Console
Real-time telemetry via Server-Sent Events (SSE). Every model call, tool invocation, verification result, and error is displayed as it happens. Filterable by category (tools, model, errors, verification).

### 4. Provenance Inspector
Per-event hash chain visualization. Click any event to see its payload, SHA-256 hash, predecessor hash, and chain position. Verify button runs full chain validation.

### 5. Tool Memory & Learning
Cold vs Warm comparison scoreboard, learned playbook cards with confidence scores, and the causal evidence chain showing exactly how failures became knowledge.

### AO Development Panel
Navbar 🧠 button opens the AO modal showing daemon status, doctor diagnostics, and harness configuration.

---

## 🏢 Sponsor Integrations

Every sponsor is a **functional component** of the engine, not a badge:

| Sponsor | Role in FORGE | Where It's Used |
|---------|--------------|-----------------|
| **TensorMux** (`glm-4-7-flash`) | Core reasoning engine — agent architect, benchmark executor, self-reflector, mutation synthesizer | `apps/api/app/providers/tensormux.py` |
| **OpenAI** (`gpt-5-nano`) | Specialized reasoning via role routing (reflector role) | `apps/api/app/providers/factory.py` |
| **Smallest.ai** (Waves Lightning v3.1) | Voice narration — turns evolution milestones into spoken debriefs | `apps/api/app/providers/voice.py` |
| **Agent Orchestrator (AO)** | Development orchestration — daemon, health diagnostics, harness management | `apps/api/app/agents/ao_integration.py` |

---

## 🧪 Causal Evidence: Failures → Knowledge → Execution

FORGE doesn't just correlate — it shows the **exact causal chain** proving that learned memory caused improvements:

```
1. LINEAR TEAM UUID POLICY
   Run 1: HTTP 422 — Invalid team slug 'CORE'. Expected 36-char UUID.
        ↓ Self-Reflection
   Playbook: "Linear requires UUID '550e8400-...'. Never pass slugs."
        ↓ Applied
   Run 2: team_id: "550e8400-..." passed directly (0 errors, 1 call)

2. SLACK CHANNEL ESCALATION POLICY
   Run 1: HTTP 400 — Channel policy violation. #enterprise-escalations requires [SLA-ALERT].
        ↓ Self-Reflection
   Playbook: "Enterprise escalations must include '[SLA-ALERT]' and customer_id."
        ↓ Applied
   Run 2: Formatted with '[SLA-ALERT] customer_id: cust_acme_corp' instantly (0 errors)

3. LINEAR PRIORITY SCHEMA
   Run 1: HTTP 400 — Invalid priority 'urgent'. Expected integer 1-4.
        ↓ Self-Reflection
   Playbook: "Priority must be integer: 1 (Urgent), 2 (High), 3 (Normal), 4 (Low)."
        ↓ Applied
   Run 2: priority: 1 sent cleanly on first attempt
```

---

## 📊 Database Schema

Six tables storing the complete evolution history:

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `experiments` | Top-level experiment tracking | id, name, goal, benchmark_id, status, best_generation_id |
| `generations` | Agent specs + metrics per generation | id, generation_number, agent_spec (JSON), metrics (JSON), status |
| `executions` | Per-task execution records | id, task_id, generation_id, status, result (JSON), metrics (JSON) |
| `trace_events` | Immutable event log with hash chain | id, type, payload (JSON), previous_event_hash, event_hash |
| `mutations` | Architectural diffs between generations | id, mutation_type, target, before_json, after_json, reason |
| `tool_memories` | Learned operational playbooks | id, tool_name, category, pattern_trigger, learned_rule, confidence |

**Dual database support:** SQLite (local development) and PostgreSQL (production via Supabase). Auto-detected from `DATABASE_URL`.

---

## 🔧 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons |
| **Database** | SQLite (dev) / PostgreSQL 17 (prod via Supabase) |
| **LLM** | TensorMux (`glm-4-7-flash`), OpenAI (`gpt-5-nano`) |
| **Voice** | Smallest.ai Waves Lightning v3.1 |
| **Orchestration** | Agent Orchestrator (AO) |
| **Hosting** | Vercel (frontend), Render (backend), Supabase (database) |
| **Provenance** | SHA-256 hash chain (custom implementation) |

---

## 📝 License

MIT

---

<div align="center">

**FORGE** — *Agents don't just run. They evolve.* 🔥

</div>
]]>
