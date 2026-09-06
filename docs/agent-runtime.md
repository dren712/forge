# FORGE — Agent Runtime, Tool Execution & Enterprise Environment Specification (Section S3)

**Status**: Verified & Hardened  
**Audit Baseline**: Section S3  
**Commit Baseline**: Branch `main`  
**Test Suite**: 39/39 Passing Tests (100% Green)  

---

## 1. Execution Lifecycle

The FORGE agent execution lifecycle is deterministic, bounded, and observable. Every task execution adheres to this exact sequence:

```text
AgentExecution
    │
    ├── 1. Load AgentSpec (model, tools, prompt, planner, verifier, retry_policy)
    ├── 2. Initialize AgentState (status: CREATED)
    ├── 3. Discover Tools via ToolRegistry (resolve Tool protocols and function schemas)
    ├── 4. Transition State -> RUNNING
    │
    ├── 5. EXECUTION LOOP (bounded by MAX_AGENT_STEPS and MAX_AGENT_RUNTIME_SECONDS)
    │     ├── Check limits (timeout, step ceiling, tool call ceiling)
    │     ├── Build model context (system prompt, playbooks, messages, observations)
    │     ├── Call LLM provider (bounded retries via MAX_MODEL_RETRIES)
    │     ├── Parse response (native function calls or embedded regex fallback)
    │     │
    │     ├── IF tool calls requested:
    │     │     ├── Transition State -> WAITING_FOR_TOOL
    │     │     ├── For each tool call sequentially:
    │     │     │     ├── Emit TOOL_CALL event
    │     │     │     ├── Validate tool existence in registry
    │     │     │     ├── Validate argument types and required schema properties
    │     │     │     ├── Enforce sandbox security constraints (sanitize_path)
    │     │     │     ├── If invalid: produce structured ToolResult observation without crashing
    │     │     │     ├── If valid: execute tool within designated workspace
    │     │     │     ├── If tool throws: retry according to spec.retry_policy
    │     │     │     ├── If tool returns business constraint error: record observation
    │     │     │     ├── Emit TOOL_RESULT event (status_code, error_type, latency_ms)
    │     │     │     └── Record observation in state and message history
    │     │     └── Transition State -> RECOVERING (if errors present) or RUNNING
    │     │
    │     └── ELSE (terminal text generated / agent declares completion):
    │           ├── Transition State -> VERIFYING
    │           ├── Emit VERIFICATION_STARTED
    │           ├── Execute AgentVerifier.verify(state, workspace)
    │           ├── Emit VERIFICATION_RESULT (checks, passed, evidence)
    │           ├── IF verifier passes:
    │           │     ├── Transition State -> COMPLETED
    │           │     └── BREAK loop
    │           └── ELSE (verifier rejects completion):
    │                 ├── Transition State -> RECOVERING
    │                 ├── Inject [VERIFIER NOTICE] observation into conversation
    │                 └── CONTINUE loop for agent self-correction
    │
    ├── 6. Post-Loop Finalization
    │     ├── If still RUNNING/WAITING/RECOVERING: Transition State -> MAX_STEPS
    │     ├── Emit AGENT_COMPLETED
    │     ├── Run autonomous ToolReflectionEngine (if memory_store configured)
    │     └── Compute latency_ms and return AgentState
```

---

## 2. State Model & Transition Invariants

Agent state is encapsulated in `app.agents.state:AgentState`.

### Canonical Attributes
- `goal: str`: Objective assigned to the agent.
- `messages: list[dict[str, Any]]`: OpenAI-compatible message history.
- `plan: list[str]`: Planner subgoals or structured milestones.
- `observations: list[dict[str, Any]]`: Structured chronological record of environment and tool observations.
- `tool_results: list[dict[str, Any]]`: Raw execution history of every tool invoked.
- `memory_context: list[str]`: Memory playbooks and distilled rules injected into the prompt.
- `current_step: int`: Current loop iteration counter.
- `tool_call_count: int`: Cumulative tool calls executed.
- `model_call_count: int`: Cumulative model inference turns.
- `total_tokens`, `input_tokens`, `output_tokens`: Cumulative token usage.
- `status: AgentStatus`: Explicit lifecycle status.
- `errors: list[str]`: Log of operational errors encountered.
- `verification_passed: bool`, `verification_feedback: str | None`, `verification_result: VerificationResult | None`: Verification audit gate.
- `final_output: str | None`: Terminal answer text.
- `latency_ms: float`: Wall-clock execution duration.

### Lifecycle Status State Machine
```text
                  ┌─────────┐
                  │ CREATED │
                  └────┬────┘
                       │ transition_to("RUNNING")
                       ▼
                 ┌───────────┐
       ┌─────────┤  RUNNING  ├──────────┐
       │         └─────┬─────┘          │
       │ tool calls    │                │ terminal text
       ▼               ▼                ▼
┌──────────────┐   ┌───────┐     ┌───────────┐
│WAITING_FOR_TOOL│ │TIMEOUT│     │ VERIFYING │
└──────┬───────┘   └───────┘     └─────┬─────┘
       │                               │
       │ tool errors                   │ verification failed
       ▼                               ▼
┌──────────────┐                 ┌───────────┐
│  RECOVERING  │◄────────────────┤RECOVERING │
└──────┬───────┘                 └───────────┘
       │                               │
       │ next turn                     │ verification passed
       ▼                               ▼
┌──────────────┐                 ┌───────────┐
│   RUNNING    │                 │ COMPLETED │ (Terminal)
└──────────────┘                 └───────────┘
```

Invalid transitions (e.g. `COMPLETED -> RUNNING`) strictly raise `RuntimeError`.

---

## 3. Tool Lifecycle & Validation Contract

Every tool satisfies the `app.tools.base:Tool` protocol:
```python
class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]
    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult: ...
```

### Pre-Execution Validation
Before any tool is executed, `AgentRuntime._validate_tool_call` enforces:
1. **Registry Membership**: Tool name must exist in `self.registry`. Unregistered tools return HTTP 404 `TOOL_NOT_FOUND`.
2. **Type Safety**: Arguments must be a JSON dictionary (`dict`). Malformed types return HTTP 400 `INVALID_TOOL_ARGUMENTS`.
3. **Required Schema**: All parameters listed in `input_schema["required"]` must be present. Missing fields return HTTP 400 `INVALID_TOOL_ARGUMENTS`.
4. **Property Type & Enum Checking**: Validates string, integer, number, boolean, array, object, and declared `enum` constraints.
5. **Path Traversal Interception**: Any filesystem path parameter (`path`, `filepath`, `target_path`, `rel_path`) is verified against `sanitize_path(workspace, path)`. Directory escape attempts return HTTP 403 `SECURITY_VIOLATION`.

### Normalized Tool Result
```python
class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None
    error_type: str | None = None
    status_code: int | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Tool Failure is an Observation
Operational errors (400 Bad Request, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity) **never crash the runtime**. They are returned as structured observations into the agent conversation:
```text
Tool Result (linear_api):
Error 422 Unprocessable Entity: team_id 'CORE' is invalid. Linear requires a 36-character team UUID...
```
This forces the model to reason about its failure and self-correct on subsequent steps.

---

## 4. Verification Gate

The agent's own declaration ("I am done") is insufficient. The completion gate is evaluated by `AgentVerifier`:

```python
class VerificationCheck(BaseModel):
    name: str
    passed: bool
    evidence: str

class VerificationResult(BaseModel):
    passed: bool
    checks: list[VerificationCheck]
    failure_reason: str | None = None
```

### Supported Modes:
- **`none`**: Naive baseline agent without verification gate.
- **`self_check`**: Checks state error volume (< 3 unhandled errors).
- **`mandatory_tests`**: Objective check verifying that `test_runner` was executed by the agent, that tests passed, and that failed test count is zero.
- **`strict_test_gate`**: In addition to agent test execution, executes an independent, isolated test runner pass in the workspace to guarantee repository state is clean.
- **`verify_enterprise_state`**: Deterministic inspection of workspace artifacts (`.linear_state.json`, `.slack_messages.json`, `.github_state.json`, `.sentry_state.json`) verifying real state mutations.

---

## 5. Runtime Limits & Sandboxing

### Configured Bounds (via `app.core.config:Settings`)
- `MAX_AGENT_STEPS`: 20 steps (configurable via environment variable).
- `MAX_TOOL_CALLS`: 30 cumulative calls.
- `MAX_AGENT_RUNTIME_SECONDS`: 180 seconds wall-clock ceiling.
- `MAX_MODEL_RETRIES`: 2 bounded attempts for transient network provider drops.

### Sandbox Confinement (`app.tools.base:sanitize_path`)
- All filesystem-altering tools (`file_editor`, `repository`, `search`, `shell`) operate strictly within the assigned task workspace.
- `sanitize_path` resolves symlinks and relative path components (`..`), enforcing `target.is_relative_to(workspace_resolved)`. Traversal attempts raise `PermissionError`.
- `ShellTool` strips all environment keys matching `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `AUTH`, sets `cwd=workspace`, enforces process timeouts, and prohibits dangerous commands (`rm -rf /`, `mkfs`, `curl`, `wget`).

---

## 6. Enterprise Environment (The Five Tools)

The five enterprise tools simulate real SaaS APIs with realistic operational quirks:

| Tool | Action Suite | Key Operational Constraints / Quirks | State Persistence |
| :--- | :--- | :--- | :--- |
| **`linear_api`** | `list_teams`, `list_issues`, `create_issue`, `update_issue` | 1. `team_id` requires 36-char UUID (rejects slugs with 422).<br>2. `priority` requires integer 1–4 (rejects string with 400).<br>3. Transitioning to `In Progress` requires `assignee_id` (rejects with 409). | `.linear_state.json` |
| **`slack_api`** | `list_channels`, `post_message` | 1. Posting to `#enterprise-escalations` requires `[SLA-ALERT]` tag and `customer_id` citation (rejects with 400). | `.slack_messages.json` |
| **`crm_api`** | `list_customers`, `get_customer` | 1. Returns customer SLA tiers (Enterprise: 1h, Growth: 8h, Free: 48h). Determines incident priority. | In-memory seeded registry |
| **`github_api`** | `list_branches`, `create_pull_request`, `check_pr_status`, `merge_pull_request` | 1. Head branch must start with `fix/`, `feat/`, `hotfix/`, `chore/` (rejects with 403).<br>2. PR title requires ticket bracket tag e.g. `[LIN-101]` (rejects with 422).<br>3. Merge requires 2 approvals (rejects with 400). | `.github_state.json` |
| **`sentry_api`** | `list_services`, `fetch_error_trace`, `query_alert_thresholds`, `resolve_incident` | 1. Querying trace returns stack traces and connection pool errors.<br>2. Incident resolution requires `resolution_note` of at least 15 characters (rejects with 422). | `.sentry_state.json` |

---

## 7. Cross-Tool Workflows

Realistic enterprise incident resolution spans all 5 tools:
```text
CRM API (Lookup SLA: 1 hour)
   ↓
Sentry API (Fetch error trace: PoolAcquireTimeoutError in billing-api)
   ↓
Linear API (Create P1 issue and assign to user_alex)
   ↓
Slack API (Broadcast [SLA-ALERT] to #enterprise-escalations)
   ↓
GitHub API (Create hotfix/db-pool-increase PR and merge)
   ↓
Sentry API (Resolve SENTRY-891 with detailed resolution note)
   ↓
AgentVerifier (Objective verification of all 4 state files in workspace)
```
Verified end-to-end in `apps/api/tests/test_enterprise_workflow.py`.

---

## 8. Live vs Test Mode

- **`FORGE_TEST_MODE=1`**: Uses `DeterministicMockProvider` and offline workspaces for sub-second, zero-cost regression testing in CI (39/39 tests in 1.31s).
- **`FORGE_TEST_MODE=0` (Production/Live)**: Uses real model router (`ModelRouter`) connecting to configured providers (TensorMux `glm-4-7-flash` or OpenAI `gpt-5-nano`). Tested live via `scripts/test_live_enterprise_runtime.py`.
- The system never silently falls back to mocks if a live provider fails; it surfaces the genuine error to the caller.

---

## 9. Known Limitations

1. **Sequential Tool Execution**: Multiple tool calls in a single model turn are currently executed sequentially to guarantee safe state mutation order. Concurrent execution is not enabled for state-mutating enterprise tools.
2. **ReAct Planner Primary**: Full hierarchical multi-agent sub-delegation is guided via prompt decomposition; autonomous multi-agent swarm delegation is scheduled for Section S7.
