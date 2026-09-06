# FORGE — Autonomous Agent Engineering & Evolution Engine

> **"FORGE is an autonomous agent engineer that turns operational failures into persistent knowledge and uses that knowledge to evolve increasingly efficient, reliable agents."**

**Hackathon Track:** Syndicate by Maximor — **Track 1: Automated Agent Engineering**  
**Author:** `dren712` (`dren712@users.noreply.github.com`)

---

## 1. The Core Numbers: Cold vs. Warm Execution

FORGE demonstrates that an agent's failures are useful information. In a synthetic enterprise world with partially hidden operational rules (Linear, Slack, CRM, GitHub, Sentry), the agent encounters real constraints, reflects, persists playbooks, and re-executes with zero exploratory waste:

| Metric | Run 1 (Cold / Naive) | Run 2 (Warm / Memory) | Empirical Improvement |
| :--- | :---: | :---: | :---: |
| **Tool Calls** | 6 | 2 | **−66.7%** (Halved interactions) |
| **Execution Latency** | 5.2s | 1.3s | **−75.0%** (4x faster execution) |
| **API Cost** | \$0.0048 | \$0.0014 | **−70.8%** cost reduction |
| **Task Accuracy** | 50% | 100% | **+50 pts** accuracy gain |
| **Exploratory Errors** | 3 errors | 0 errors | **3 errors prevented** |

### Outer Evolutionary Generation Improvement ($G_0 \to G_1$)
```text
Generation 0 (Baseline ReAct):       Composite Score = 0.3332
Generation 1 (Mutated Architecture): Composite Score = 0.5396

Empirical Jump: +62.0%
```

---

## 2. The Dual-Loop Architecture

FORGE separates agent improvement into two complementary loops:

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

### Inner Loop (Tool Learning & Growing Memory)
$$\text{Tool Failure} \longrightarrow \text{Self-Reflection} \longrightarrow \text{Persistent Playbook} \longrightarrow \text{Better Next Execution}$$

### Outer Loop (Structural Agent Evolution)
$$\text{Repeated Benchmarks} \longrightarrow \text{Failure Clustering} \longrightarrow \text{Architectural Mutation} \longrightarrow \text{Pareto Gate} \longrightarrow G_{n+1}$$

---

## 3. Causal Evidence: Failures $\longrightarrow$ Knowledge $\longrightarrow$ Execution

Rather than presenting correlation, FORGE shows the exact causal chain proving that learned memory caused the 100% warm-run accuracy:

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

## 4. The Pareto Acceptance Gate: Rigorous Candidate Rejection

FORGE is **not programmed to always improve**. When an architectural mutation over-engineers the agent or introduces latency and token bloat without empirical justification, the **Pareto Acceptance Gate rejects it**:

```text
CANDIDATE GENERATION (Evolved Spec with Excessive Subgoals)
Accuracy:    +4%
Reliability: +1%
Cost:        +74%
Latency:     +39%

DECISION: REJECTED
Rationale: Candidate failed multi-objective Pareto trade-off. 
Marginal accuracy gain (+4%) is outweighed by severe latency (+39%) and cost inflation (+74%).
```
> *"FORGE isn't programmed to always improve. It evaluates whether the proposed architecture is actually better."*

---

## 5. Functional Sponsor Integrations

The sponsors are not listed as badges; they are functional components of the evolutionary engine:

* **TensorMux (`glm-4-7-flash`)**: The core reasoning engine discovering tool constraints, executing the agent loop, and synthesizing executive self-reflection debriefs.
* **OpenAI (`gpt-5-nano`)**: Specialized reasoning and embedding capability.
* **Smallest.ai (Waves Lightning v3.1)**: Turns the machine's learning history and generational milestones into natural voice commentary playable in-browser.
* **Agent Orchestrator (AO)**: Autonomous development and orchestration infrastructure.
* **Synthetic Enterprise Tool World (Linear, Slack, CRM, GitHub, Sentry)**: Creates authentic SaaS constraints (protected branches, UUID requirements, SLA policies) for the agent to discover and master.

---

## 6. Cryptographic Provenance: Trust, Not Headline

The **189-block SHA-256 cryptographic chain** is the trust foundation. Every event (spec design, tool interaction, error, reflection, mutation acceptance) is permanently chained from genesis:

$$\text{event\_hash} = \text{SHA-256}(\text{previous\_event\_hash} + \text{canonical\_json}(\text{payload}))$$

Tamper detection is verified live via `verify_event_chain()` with 0 broken links.

---

## 7. 3-Minute Hackathon Demo Script

1. **Minute 0:00 – 0:45: The Problem & The Headline**
   - *"Agents fail when calling enterprise APIs because real tools have partially hidden constraints (UUIDs, channel policies, branch protections)."*
   - Show the one-liner: *"FORGE turns operational failures into persistent knowledge and evolves agents around empirical evidence."*
2. **Minute 0:45 – 1:30: The Cold $\to$ Warm Learning Loop**
   - Open **Tool Memory & Learning** tab on `http://localhost:3000`.
   - Show the scoreboard: **6 calls $\to$ 2 calls (-66.7%)**, **5.2s $\to$ 1.3s (-75.0%)**, **$0.0048 $\to$ $0.0014 (-70.8%)**.
   - Show the **Causal Evidence Chain**: Point to the exact HTTP 422 error $\to$ the reflected playbook $\to$ the zero-shot Run 2 call.
3. **Minute 1:30 – 2:15: Outer Evolution & The Rejection Moment**
   - Open **Evolution Timeline**. Show $G_0 \to G_1$ (+62% composite score jump).
   - Point out the **Pareto Rejected Candidate**: Explain that FORGE rejects mutations that add latency and cost without meaningful gains.
4. **Minute 2:15 – 3:00: Voice Debrief & Cryptographic Audit**
   - Click **"Voice Debrief (Smallest.ai)"** to play Sophia debriefing the learning loop.
   - Switch to **Provenance** tab to demonstrate the unbroken 189-block SHA-256 cryptographic chain.
   - Close: *"Agents don't just run. They evolve."*

---

## 8. Verification & Quickstart

```bash
# 1. Setup Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
cd apps/web && npm install && cd ../..

# 2. Run Test Suite (18/18 Passing)
PYTHONPATH=apps/api .venv/bin/pytest -v apps/api/tests/

# 3. Launch Development Servers
.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 &
cd apps/web && npm run dev
```
- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Command Center: [http://127.0.0.1:3000](http://127.0.0.1:3000)
