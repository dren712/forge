# 🔥 FORGE — Autonomous Agent Engineering & Evolution Engine

> **"Agents don't just run. They evolve."**
> 
> FORGE is an autonomous agent engineering platform that empirically diagnoses why AI agents fail in real-world environments, synthesizes targeted architectural mutations, and drives multi-generation improvements backed by cryptographic provenance.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hackathon Track:** Syndicate by Maximor — **Track 1: Automated Agent Engineering**  
**Author:** `dren712`  
**Repository:** [https://github.com/dren712/forge](https://github.com/dren712/forge)  
**Live Frontend (Vercel):** [https://forge-agentd.vercel.app/](https://forge-agentd.vercel.app/)  
**Live API Status (Render):** [https://forge-api-amow.onrender.com/](https://forge-api-amow.onrender.com/)  
**API Health Check:** [https://forge-api-amow.onrender.com/api/health](https://forge-api-amow.onrender.com/api/health)  
**Interactive API Docs (Swagger):** [https://forge-api-amow.onrender.com/docs](https://forge-api-amow.onrender.com/docs)  
**Live Experiments API:** [https://forge-api-amow.onrender.com/api/experiments](https://forge-api-amow.onrender.com/api/experiments)  

---

## 1. Executive Summary & Empirical Results

Modern AI agents fail when meeting the real world: hidden API schemas, unwritten team policies, and subtle edge cases cause repeated operational breakdowns.

FORGE treats **failures as high-value training signal**. Instead of prompting harder, FORGE operates a dual-loop evolutionary engine:

1. **Inner Loop (Experiential Tool Learning):** Discovers hidden tool constraints, reflects, and persists operational playbooks across execution runs.
2. **Outer Loop (Structural Agent Evolution):** Clusters benchmark failures, proposes architectural mutations (prompt, planner, memory, verifier), and validates them through a strict Pareto Acceptance Gate.

### Empirical Scoreboard: Cold vs. Warm Execution

In an enterprise tool benchmark with hidden operational policies (Linear, Slack, CRM, GitHub, Sentry), the agent's first run hits real-world constraints, reflects, persists playbooks, and re-executes with zero exploratory waste:

| Metric | Run 1 (Cold / Naive) | Run 2 (Warm / Memory) | Empirical Delta |
| :--- | :---: | :---: | :---: |
| **Tool Calls** | 6 calls | 2 calls | **−66.7%** (Halved interactions) |
| **Execution Latency** | 5.2s | 1.3s | **−75.0%** (4x faster execution) |
| **API Cost** | $0.0048 | $0.0014 | **−70.8%** cost reduction |
| **Task Accuracy** | 50% | 100% | **+50 pts** accuracy jump |
| **Exploratory Errors** | 3 errors | 0 errors | **3 errors prevented** |

### Outer Evolutionary Generation Jump ($G_0 \to G_1$)

```text
Generation 0 (Baseline ReAct Agent):   Composite Score = 0.3332 (100% task accuracy, low reliability)
Generation 1 (Mutated Architecture):   Composite Score = 0.5396 (100% task accuracy, strict verifier)

Empirical Evolution Jump: +62.0%
```

---

## 2. Agent Orchestrator (AO) — The Meta-Agent Development Harness

A centerpiece of FORGE is its integration with **Agent Orchestrator (AO)**. 

### What is AO in FORGE?

AO is not a decorative badge — it is the **autonomous development orchestration infrastructure** that was used to build and maintain FORGE itself. 

This establishes a powerful **meta-agent engineering loop**:
- **AO (The Meta-Layer):** Orchestrates autonomous coding agents, manages daemon lifecycles, and automates multi-file development workflows across the FORGE codebase.
- **FORGE (The Evolutionary Engine):** Evaluates, mutates, and evolves domain agents against software engineering and enterprise benchmarks.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      THE META-AGENT ARCHITECTURE                        │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Agent Orchestrator (AO)                        │  │
│  │  Autonomous Developer Harness • Daemon • Coding Agent Lifecycle   │  │
│  │  Orchestrated the creation, testing, and evolution of FORGE itself │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │ Builds & Harnesses                 │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     FORGE Platform Engine                         │  │
│  │                                                                   │  │
│  │   ┌────────────────────┐            ┌─────────────────────────┐   │  │
│  │   │  Inner Loop        │            │  Outer Loop             │   │  │
│  │   │  Tool Playbooks    │            │  Architectural Mutation │   │  │
│  │   │  Failure Reflection│            │  Pareto Acceptance Gate │   │  │
│  │   └────────┬───────────┘            └────────────┬────────────┘   │  │
│  │            │                                     │                │  │
│  │            ▼                                     ▼                │  │
│  │     100% Warm Accuracy                    Evolved Gen Spec        │  │
│  │    (-66.7% Tool Calls)                   (+62% Composite Score)   │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
│                                    ▼                                    │
│                     Cryptographic SHA-256 Provenance                     │
│                        (Unbroken 189-Block Ledger)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Clean Architectural Isolation

FORGE enforces a strict separation of concerns:
- **AO is a Development Harness:** It manages the development environment, local daemons, SQLite session stores, and coding agents (e.g., Claude Code, local harnesses).
- **Runtime Independence:** Runtime benchmark evaluations, Pareto acceptance gating, and cryptographic provenance verification execute independently of AO. This guarantees that FORGE benchmarks are **100% reproducible on any machine or server**.

### Live AO Telemetry in the UI

Judges can inspect AO directly in the Command Center:
1. Click the **🧠 brain icon** in the top navigation bar.
2. The **AO Development Orchestration** modal opens, displaying live backend diagnostics from:
   - `GET /api/ao/status`: Daemon PID, active port, and process health.
   - `GET /api/ao/doctor`: Real CLI health checks (`ao doctor`) reporting SQLite storage integrity and coding harness status.
   - `GET /api/ao/diagnostics`: Audit report detailing harness authentication, registered workspaces, and process isolation.

> **Truthful Reporting:** On the hosted production container (Render Linux), the AO modal truthfully reports that the macOS `ao` binary is on standby and expectedly absent from the production container — demonstrating real backend diagnostics with **zero fabricated sessions**.

---

## 3. The Dual-Loop Evolution Engine

```text
                                USER GOAL
                                    │
                                    ▼
                           ┌────────────────┐
                           │    FORGE       │
                           │ Agent Architect│
                           └───────┬────────┘
                                   │
                                Agent G0
                                   │
                                   ▼
                          Enterprise Tool World
                     ┌──────┬──────┬──────┬──────┐
                     │Linear│Slack │ CRM  │GitHub│...
                     └──────┴──────┴──────┴──────┘
                                   │
                                   ▼
                               Trace data
                                   │
                          ┌────────┴─────────┐
                          ▼                  ▼
                     Failure Analysis     Metrics
                          │
                          ▼
                     Self Reflection
                          │
                          ▼
                     Memory / Playbooks
                          │
                          └──────────────┐
                                         ▼
                                    Better Agent
                                         │
                                         ▼
                                   Benchmark Again
                                         │
                                         ▼
                                   G1 / G2 / G3...
                                         │
                                         ▼
                                 Pareto Acceptance
                                         │
                                         ▼
                              SHA-256 Provenance Ledger
                                         │
                                 ┌───────┴───────┐
                                 ▼               ▼
                              Command          Voice
                              Center          Debrief
```

### Inner Loop: Tool Learning & Growing Memory

> **Tool Failure** ➔ **Self-Reflection** ➔ **Persistent Playbook** ➔ **Zero-Waste Re-execution**

When an agent interacts with SaaS tools, real-world errors occur (e.g. invalid UUIDs, missing escalation tags, branch protection rules). FORGE captures the error stack, triggers self-reflection, and saves a generalized playbook into persistent `ToolMemory`. On subsequent runs, the agent loads these playbooks and executes cleanly on the first attempt.

### Outer Loop: Structural Agent Evolution

> **Benchmark Run** ➔ **Failure Clustering** ➔ **Architectural Mutation** ➔ **Pareto Gate** ➔ **$G_{n+1}$**

Across multiple tasks, failure traces are clustered. FORGE's evolutionary engine generates targeted mutations to:
- **System Prompts:** Add boundary condition and edge-case guidance.
- **Planning Logic:** Switch between direct execution, ReAct, and subgoal-driven planning.
- **Verification Strategy:** Enforce mandatory automated test execution before task completion.
- **Retry Policies:** Configure backoff rates and tool-specific retry limits.

---

## 4. Causal Evidence: Failures $\longrightarrow$ Knowledge $\longrightarrow$ Execution

FORGE provides an unambiguous causal audit trail proving that learned playbooks caused the performance improvements:

```text
1. LINEAR TEAM UUID POLICY
   Run 1 Failure: HTTP 422: Invalid team slug 'CORE'. Expected 36-char UUID.
         ↓
   Self-Reflection: "Linear requires UUID '550e8400-e29b-41d4-a716-446655440001'. Never pass slugs."
         ↓
   Run 2 Action: team_id: "550e8400-..." passed directly (0 errors, 1 call).

2. SLACK CHANNEL ESCALATION POLICY
   Run 1 Failure: HTTP 400: Channel policy violation. #enterprise-escalations requires [SLA-ALERT].
         ↓
   Self-Reflection: "Enterprise escalations must include '[SLA-ALERT]' and customer_id in text."
         ↓
   Run 2 Action: Formatted with '[SLA-ALERT] customer_id: cust_acme_corp' instantly (0 errors).

3. LINEAR PRIORITY SCHEMA
   Run 1 Failure: HTTP 400: Invalid priority 'urgent'. Expected integer 1-4.
         ↓
   Self-Reflection: "Priority must be integer: 1 (Urgent), 2 (High), 3 (Normal), 4 (Low)."
         ↓
   Run 2 Action: priority: 1 sent cleanly on first attempt.
```

---

## 5. The Pareto Acceptance Gate: Rigorous Candidate Rejection

FORGE is **not programmed to naively accept every mutation**. When an architectural candidate over-engineers the agent or introduces latency and token bloat without empirical justification, the **Pareto Acceptance Gate rejects it**:

```text
CANDIDATE GENERATION (Evolved Spec with Excessive Subgoals)
Accuracy:    +4%
Reliability: +1%
Cost:        +74% (Cost Regressed)
Latency:     +39% (Latency Regressed)

DECISION: REJECTED
Rationale: Parent dominates candidate. Candidate regressed on ['cost_per_task', 'latency_per_task'] 
with negligible accuracy gain (+4%). Evolved spec discarded; parent retained.
```

> *"FORGE isn't programmed to always say yes. It evaluates whether the proposed architecture is actually better across accuracy, reliability, cost, and latency."*

---

## 6. Functional Sponsor Integrations

Every sponsor technology is a functional component of the architecture:

| Sponsor | Role in FORGE | Production Implementation |
| :--- | :--- | :--- |
| **TensorMux** (`glm-4-7-flash`) | Core Agent Reasoning Engine | Powers agent task execution, tool selection, failure reflection, and mutation synthesis. |
| **Agent Orchestrator (AO)** | Autonomous Developer Harness | Development orchestration, health diagnostics, local daemon management, and session auditing. |
| **OpenAI** (`gpt-5-nano`) | Specialized Reasoning / Embeddings | Role-based routing for reflection analysis and semantic clustering. |
| **Smallest.ai** (Waves Lightning v3.1) | Voice Debriefing Engine | Synthesizes spoken commentary of evolutionary milestones and learning debriefs directly in the UI. |

---

## 7. Cryptographic Provenance Ledger

Every event in FORGE (agent creation, model calls, tool executions, error reflections, mutation proposals, and Pareto decisions) is chained into an immutable SHA-256 ledger:

```python
event_hash = SHA256(previous_event_hash + canonical_json(payload))
```

- **189+ Block Unbroken Ledger:** Backed by persistent database records.
- **Zero Broken Links:** Cryptographically validated via `GET /api/experiments/{id}/provenance`.
- **Tamper Detection:** If any historical event payload is modified, the hash chain breaks at that exact index and flags the anomaly.

---

## 8. 🚀 Quickstart for Judges: Run Locally

Judges can run FORGE locally in under 2 minutes with complete parity to the production system.

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Git

### 1. Clone & Set Up

```bash
# Clone the repository
git clone https://github.com/dren712/forge.git
cd forge

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt

# Set up Next.js frontend
cd apps/web && npm install && cd ../..
```

### 2. Configure Environment (`.env`)

A pre-configured `.env` works out of the box with the local SQLite database. Ensure your `.env` contains:

```env
TENSORMUX_API_KEY=tmx_c7e209ad781c0490dc1b9f9480a0e61d
TENSORMUX_BASE_URL=https://api.tensormux.com/v1
TENSORMUX_MODEL=glm-4-7-flash
DATABASE_URL=sqlite+aiosqlite:///forge.db
FORGE_ENV=development
```

### 3. Run the Automated Test Suite (119 Passing Tests)

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/ -v
```

### 4. Launch Local Development Servers

**Terminal 1 — Backend (FastAPI):**
```bash
source .venv/bin/activate
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend (Next.js):**
```bash
cd apps/web
npm run dev
```

### 5. Access the Local Application

- **Command Center UI:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Health:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Interactive OpenAPI / Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 9. 3-Minute Judge Evaluation Script

When evaluating the live application or your local build, follow this 3-minute walkthrough:

1. **0:00 — Overview Dashboard ([http://localhost:3000](http://localhost:3000)):**
   - Review the active evolution experiments. Notice the **100% peak accuracy** achieved across software engineering tasks.
   - Click into the **GitHub Issue Resolver** experiment.
2. **0:45 — The Evolution Timeline & Pareto Rejection:**
   - Inspect **Generation 0 (Baseline)** vs **Generation 1 (Candidate)**.
   - Observe the **Pareto Rejection**: FORGE empirically rejected Candidate 1 because cost/latency regressed without sufficient accuracy upside.
3. **1:30 — Causal Evidence & Tool Playbooks:**
   - Open the **Evidence** and **Learning** views.
   - Review the causal chain: see the exact Linear UUID error, the generated playbook rule, and how the subsequent execution achieved zero errors.
4. **2:15 — Cryptographic Provenance:**
   - Navigate to the **Provenance** tab.
   - Click **Verify Provenance** to trigger the live SHA-256 cryptographic chain audit across all recorded trace events.
5. **2:45 — Agent Orchestrator (AO) Panel:**
   - Click the **🧠 brain icon** in the top navigation bar to inspect the AO development orchestration diagnostics.

---

## 10. Technology Stack Summary

| Domain | Stack |
| :--- | :--- |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, Uvicorn |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons |
| **Database** | Dual Driver: SQLite (`aiosqlite` local) / PostgreSQL 17 (`asyncpg` production) |
| **Development Harness** | Agent Orchestrator (AO) CLI & Daemon Bridge |
| **LLM & Voice Providers** | TensorMux (`glm-4-7-flash`), OpenAI (`gpt-5-nano`), Smallest.ai (Waves v3.1) |
| **Integrity & Auditing** | Cryptographic SHA-256 Event Chain, Causal Evidence Inspector |
| **Cloud Hosting** | Vercel (Frontend), Render (Backend), Supabase (PostgreSQL Database) |

---

<div align=center>

**FORGE** — *Agents don't just run. They evolve.* 🔥

</div>
