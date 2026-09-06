# FORGE S5-F — Inner Learning Loop Empirical Verification Report

## Executive Summary

This report documents an **actual controlled experiment** verifying the FORGE inner learning loop (reflection, persistent tool memory, and dynamic prompt injection) executed against the enterprise multi-app benchmark using the production LLM provider (`TensorMuxProvider` running `glm-4-7-flash`).

In adherence to the benchmark integrity guidelines of Section S4 and S5:
* **No results were fabricated or manually modified.**
* **The system was not altered to force artificial improvement.**
* **All metrics reflect real execution traces, API latencies, and token counters.**

---

## 1. Experimental Setup & Starting Conditions

### 1.1 Selected Task
* **Benchmark Suite**: `ThirdPartyAppBenchmark` (`third_party_automation` v2.0.0)
* **Task ID**: `task_02_contextual_sla_routing`
* **Task Title**: Cross-App Contextual Routing: Enterprise SLA Escalation
* **Goal**: `"Incoming support alert for 'cust_acme_corp'. Look up their SLA tier in CRM and execute the required channel alert and issue creation."`
* **Allowed Tools**: `["crm_api", "slack_api", "linear_api"]`
* **Evaluation Standard**: Deterministic state file inspection (`.linear_state.json` and `.slack_messages.json` must verify that `#enterprise-escalations` received an alert with `[SLA-ALERT]` citing `cust_acme_corp`, and a Linear issue was created with `priority=1`).

### 1.2 Model & Runtime Configuration
* **LLM Provider**: `TensorMuxProvider`
* **Model**: `glm-4-7-flash` (via `https://api.tensormux.com/v1`)
* **Agent Architecture**:
  * **Planner**: `re_act` (Reason step-by-step using Thought -> Action -> Observation)
  * **Memory**: `working_context`
  * **Verifier**: `none` (Evaluation performed independently by benchmark suite)
  * **Max Steps**: 20
  * **Max Tool Calls**: 30

### 1.3 Starting Workspace Baseline
Prior to each execution, the workspace was initialized with pristine, unmutated state files:
* `.linear_state.json`: `{"issues": [], "counter": 101}`
* `.slack_messages.json`: `[]`
* `crm_api`: Customer database seeded with `cust_acme_corp` (`tier: "Enterprise"`, `sla_response_hours: 1`, `support_routing_rule: "Urgent enterprise incidents must be broadcast to #enterprise-escalations with [SLA-ALERT] and assigned Linear priority 1."`).

---

## 2. RUN A — COLD (Empty Memory)

### 2.1 Starting Memory State
* **Store Status**: Empty (`ToolMemoryStore(experiment_id="exp_inner_learning_verify")`)
* **Active Entries**: 0
* **Injected Context**: None (`memory_context_count = 0`)

### 2.2 Execution Trace & Sequence
1. `crm_api` (`action="get_customer"`, `customer_id="cust_acme_corp"`)
   * **Result**: `200 OK`
   * **Payload**: Discovered Enterprise customer tier with <1hr SLA requiring `#enterprise-escalations` broadcast with `[SLA-ALERT]`.
2. `slack_api` (`action="post_message"`, `channel="#enterprise-escalations"`, `text="Incoming support alert for cust_acme_corp: Enterprise tier customer requires urgent attention."`)
   * **Result**: `400 Bad Request`
   * **Failure**: `Error 400 Bad Request: Enterprise channel policy violation. Messages posted to #enterprise-escalations must contain the tag '[SLA-ALERT]' and cite the customer identifier (e.g. 'customer_id: cust_...').`
3. `slack_api` (`action="post_message"`, `channel="#enterprise-escalations"`, `text="[SLA-ALERT] Incoming support alert for cust_acme_corp (Acme Global Enterprise) - SLA: 1 hour. Immediate escalation required."`)
   * **Result**: `200 OK` (Recovered following error observation)
4. `linear_api` (`action="create_issue"`, `title="[cust_acme_corp] Enterprise Support Alert - SLA < 1hr", priority=1`)
   * **Result**: `400 Bad Request`
   * **Failure**: `Error 400 Bad Request: 'team_id' is required to create an issue.`
5. `linear_api` (`action="list_teams"`)
   * **Result**: `200 OK` (Discovered team `550e8400-e29b-41d4-a716-446655440001`)
6. `linear_api` (`action="create_issue"`, `team_id="550e8400-e29b-41d4-a716-446655440001"`, `title="[cust_acme_corp] Enterprise Support Alert", priority=1`)
   * **Result**: `201 Created` (Issue `CORE-101` created)

### 2.3 Run A Metrics
| Metric | Recorded Value |
| :--- | :--- |
| **Status** | `COMPLETED` |
| **Benchmark Passed** | `True` |
| **Benchmark Score** | `1.0 / 1.0` |
| **Total Tool Calls** | 6 |
| **Tool Errors Encountered** | 2 |
| **Tool Error Rate** | 33.3% (2 / 6) |
| **Elapsed Latency** | 14,196.7 ms (14.20 s) |
| **Input Tokens** | 8,782 |
| **Output Tokens** | 1,158 |
| **Total Tokens** | 9,940 |
| **Execution Cost** | \$0.006128 USD |
| **Reliability Score** | 0.900 |

---

## 3. REFLECTION & KNOWLEDGE EXTRACTION

The trace from Run A was processed by `ToolReflectionEngine.reflect_and_persist()`. The engine verified evidence grounding against the raw execution corpus and persisted two structured rules:

### 3.1 Persisted Playbook Rules
```json
[
  {
    "tool_name": "crm_api",
    "category": "CONTEXTUAL_LOGIC",
    "pattern_trigger": "Customer Tier Triage (Enterprise)",
    "learned_rule": "Enterprise tier customers (SLA < 1hr) require urgent incident escalation: post to #enterprise-escalations with '[SLA-ALERT]' and create Linear issue with priority=1.",
    "evidence": "{\n  \"customer\": {\n    \"customer_id\": \"cust_acme_corp\",\n    \"name\": \"Acme Global Enterprise\",\n    \"tier\": \"Enterprise\",\n    \"sla_response_hours\": 1,\n...",
    "confidence": 1.0,
    "observation_count": 2
  },
  {
    "tool_name": "slack_api",
    "category": "WORKFLOW_DEPENDENCY",
    "pattern_trigger": "post_message to #enterprise-escalations",
    "learned_rule": "Messages posted to #enterprise-escalations must include the tag '[SLA-ALERT]' and cite the customer_id in the text.",
    "evidence": "Error 400 Bad Request: Enterprise channel policy violation. Messages posted to #enterprise-escalations must contain the tag '[SLA-ALERT]' and cite the",
    "confidence": 1.0,
    "observation_count": 2
  }
]
```

---

## 4. RUN B — WARM (Memory Guided)

### 4.1 Starting Memory State
* **Store Status**: Populated with 2 active playbooks
* **Prompt Injection**: Injected under `### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]` into `state.messages[0]`
* **Injected Payload**:
  ```text
  ### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]
  The following operational rules, API quirks, and domain conventions were learned from prior runs.
  Apply them directly to avoid redundant exploratory calls and API errors:

  1. [CRM_API | CONTEXTUAL_LOGIC]
     • When: Customer Tier Triage (Enterprise)
     • Actionable Rule: Enterprise tier customers (SLA < 1hr) require urgent incident escalation: post to #enterprise-escalations with '[SLA-ALERT]' and create Linear issue with priority=1.
     • Learned from: { "customer": { "customer_id": "cust_acme_corp", ... }
     • Confidence: 100% (observed 2x)

  2. [SLACK_API | WORKFLOW_DEPENDENCY]
     • When: post_message to #enterprise-escalations
     • Actionable Rule: Messages posted to #enterprise-escalations must include the tag '[SLA-ALERT]' and cite the customer_id in the text.
     • Learned from: Error 400 Bad Request: Enterprise channel policy violation...
     • Confidence: 100% (observed 2x)
  ```

### 4.2 Execution Trace & Sequence
1. `crm_api` (`action="get_customer"`, `customer_id="cust_acme_corp"`) -> `200 OK`
2. `slack_api` (`action="post_message"`, `channel="#enterprise-escalations"`, omitted `[SLA-ALERT]`) -> `400 Bad Request`
3. `slack_api` (`action="post_message"`, with `[SLA-ALERT]`) -> `200 OK`
4. `linear_api` (`action="create_issue"`, missing `team_id`) -> `400 Bad Request`
5. `linear_api` (`action="list_teams"`) -> `200 OK`
6. `linear_api` (`action="create_issue"`, with team UUID) -> `201 Created`

### 4.3 Run B Metrics
| Metric | Recorded Value |
| :--- | :--- |
| **Status** | `COMPLETED` |
| **Benchmark Passed** | `True` |
| **Benchmark Score** | `1.0 / 1.0` |
| **Total Tool Calls** | 6 |
| **Tool Errors Encountered** | 2 |
| **Tool Error Rate** | 33.3% (2 / 6) |
| **Elapsed Latency** | 14,263.4 ms (14.26 s) |
| **Input Tokens** | 10,718 |
| **Output Tokens** | 1,242 |
| **Total Tokens** | 11,960 |
| **Execution Cost** | \$0.007222 USD |
| **Reliability Score** | 0.900 |

---

## 5. Metric Comparison & Deltas

| Metric | Run A (Cold) | Run B (Warm) | Absolute Delta | Percentage Change |
| :--- | :---: | :---: | :---: | :---: |
| **Benchmark Score** | 1.0 | 1.0 | 0.00 | 0.0% |
| **Tool Calls** | 6 | 6 | 0 | 0.0% |
| **Tool Errors Prevented** | — | — | 0 | 0.0% |
| **Elapsed Latency (ms)** | 14,196.7 | 14,263.4 | +66.7 ms | +0.47% (slower) |
| **Input Tokens** | 8,782 | 10,718 | +1,936 tokens | +22.04% |
| **Output Tokens** | 1,158 | 1,242 | +84 tokens | +7.25% |
| **Total Tokens** | 9,940 | 11,960 | +2,020 tokens | +20.32% |
| **Estimated Cost (USD)** | \$0.006128 | \$0.007222 | +\$0.001094 | +17.85% |
| **Reliability** | 0.900 | 0.900 | 0.000 | 0.0% |

---

## 6. Critical Findings & Empirical Analysis

The warm run **did not produce an efficiency improvement** on this task using `glm-4-7-flash`. In fact, token usage increased by +20.32% and cost increased by +17.85% due to prompt injection overhead without a corresponding reduction in tool steps.

This outcome demonstrates four vital empirical characteristics of LLM agent architectures:

### 1. System Prompt Attention Attenuation in Small Fast Models
* `glm-4-7-flash` is optimized for high-speed inference. During multi-step sequential tool calling, the model pays strong attention to the immediate `user` message (`Task Goal`) and recent `tool` observations, but attenuates attention to static operational rules embedded in the system prompt.
* Even though the rule `"Messages posted to #enterprise-escalations must include the tag '[SLA-ALERT]'"` was explicitly present in the system message, the agent defaulted to a natural conversational notification template on step 2 before being corrected by the tool's runtime error.

### 2. The "Context Tax" of Ineffective Memory Injection
* Adding learned playbooks into the prompt is not free: it adds ~320 tokens per model generation turn.
* Over a 6-step interaction, this memory payload repeated across every turn added **+1,936 prompt tokens**, increasing execution cost by 17.85% without preventing the exploratory tool calls.
* **Key Takeaway**: Memory injection is only cost-effective when the model adheres to the injected playbooks and eliminates at least one exploratory turn or tool retry.

### 3. Reflection Heuristic Granularity
* In Run A, the Linear failure was `Error 400 Bad Request: 'team_id' is required to create an issue.` rather than `Error 422: Invalid team UUID`.
* Because the reflection engine specifically looks for UUID rejection patterns (`invalid_team_uuid`), it did not distill a rule for the missing parameter. Therefore, no Linear rule existed in memory for Run B to consume.

### 4. Deterministic In-Turn Recovery Dominates Passive Guidance
* In both Run A and Run B, the agent successfully achieved 100% task completion (`Score: 1.0`) because the **runtime recovery loop** (observing the 400 error and immediately fixing the arguments in the subsequent step) is more influential on model behavior than passive system prompt guidance.

---

## 7. Limitations & Recommendations for Outer Loop (Evolution)

1. **Planner Mode Mutation Needed**:
   * A `re_act` planner failed to look ahead to the memory rules before taking Action 2. An evolved agent architecture using `structured_plan` or `plan_execute_verify` can be forced to cross-reference learned playbooks before issuing tool calls.
2. **Dynamic Just-In-Time Tool Guidance**:
   * Rather than placing playbooks purely in the global system instruction, injecting playbooks directly into the tool description schema or the immediate user prompt prior to action generation can increase model attention.
3. **Outer Loop Optimization**:
   * This empirical finding underscores why FORGE requires **outer evolutionary optimization** (mutating prompts, planners, and verifiers) rather than relying solely on inner memory retrieval.
