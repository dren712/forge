# FORGE — Canonical System Architecture & Contract Specification

**Status**: Architecture Locked (Section S1)  
**Baseline Commit**: `70689f9`  
**Test Suite**: 25/25 Passing Tests  
**Frontend**: Next.js 14.2.35 Production Verified  

---

## 1. System Overview

FORGE is an autonomous agent engineering and evolution engine designed to benchmark, diagnose, evolve, and persist learning across LLM agent architectures. 

The canonical execution flow traverses 12 distinct stages:

```text
User Goal (API / Web UI)
   ↓
Experiment (ExperimentService)
   ↓
Benchmark (SoftwareEngineeringBenchmark / ThirdPartyAutomationBenchmark)
   ↓
Agent Architect (AgentArchitect)
   ↓
AgentSpec (Pydantic Canonical Specification)
   ↓
Agent Runtime (AgentRuntime ReAct Loop)
   ↓
Tool System (ToolRegistry & Sandboxed Execution)
   ↓
Execution (TraceEvent stream & AgentState)
   ↓
Evaluation (TaskEvaluation & ExecutionMetrics)
   ↓
Failure Analysis (FailureAnalyzer taxonomy classification)
   ↓
Memory / Reflection (ToolReflectionEngine & ToolMemoryStore)
   ↓
Mutation (MutationGenerator target proposals)
   ↓
Candidate Generation (GenerationModel G_{n+1})
   ↓
Acceptance (Pareto AcceptanceEngine multi-objective gate)
   ↓
Generation Lineage (Parent-child DAG in SQLite)
   ↓
Provenance (Canonical RFC 8785 JSON + SHA-256 Chained Hasher)
```

---

## 2. Component Responsibilities & Contract Boundaries

Every subsystem has explicit ownership boundaries. Subsystems never reach across layer boundaries or assume hidden state.

### 2.1 Model Providers (`apps/api/app/providers/`)
* **Owns**: Network communication with LLM endpoints, prompt formatting, token usage parsing, latency measurement, exception normalization (`ProviderError`).
* **Does NOT Own**: Agent prompt logic, tool execution, retry loops, decision gates.
* **Receives**: `messages: list[dict[str, Any]]`, `tools: list[dict[str, Any]] | None`, `response_format: dict[str, Any] | None`, `temperature: float`.
* **Returns**: `LLMResponse(content, tool_calls, input_tokens, output_tokens, total_tokens, latency_ms, raw_response)`.
* **Called By**: `AgentArchitect`, `AgentRuntime`, `FailureAnalyzer`, `MutationGenerator`, `ExperimentService`.

### 2.2 Agent Specification (`apps/api/app/schemas/agent_spec.py`)
* **Owns**: Strongly typed, declarative definition of an agent's configuration.
* **Does NOT Own**: Execution state, runtime logic, mutation algorithms.
* **Receives**: Configuration parameters (`model`, `system_prompt`, `planner`, `tools`, `memory`, `verifier`, `retry_policy`, `orchestration`).
* **Returns**: Validated Pydantic model and `canonical_dict()`.
* **Called By**: `AgentArchitect`, `AgentRuntime`, `MutationGenerator`, `EvolutionEngine`.

### 2.3 Agent Runtime (`apps/api/app/agents/runtime.py`)
* **Owns**: The multi-turn ReAct step execution loop, prompt synthesis with tool memory injection, tool dispatch, error feedback, verifier invocation, and local trace event recording.
* **Does NOT Own**: Benchmark scoring, generation acceptance, database persistence, UI rendering.
* **Receives**: `goal: str`, `workspace: Path`, `generation_id: str | None`, `execution_id: str | None`.
* **Returns**: `AgentState` (messages, tool results, errors, token counters, wall-clock latency, status).
* **Called By**: `EvolutionEngine`, `ExperimentService`.

### 2.4 Tool Subsystem (`apps/api/app/tools/`)
* **Owns**: Sandboxed execution of actions within task workspaces or mock API boundaries. Path traversal interception (`sanitize_path`), command sanitization, and structured outputs (`ToolResult`).
* **Does NOT Own**: Agent goal management, error recovery strategies, model interaction.
* **Receives**: `input_data: dict[str, Any]`, `workspace: Path`.
* **Returns**: `ToolResult(success, output, error, latency_ms, metadata)`.
* **Called By**: `AgentRuntime`.

### 2.5 Benchmarks & Evaluator (`apps/api/app/benchmarks/`)
* **Owns**: Task definition, repository workspace seeding, isolated evaluation assertions, and test output collection.
* **Does NOT Own**: Agent architecture, mutation proposals, generation acceptance decisions.
* **Receives**: Task workspace, agent execution state.
* **Returns**: `TaskEvaluation(task_id, passed, score, reason, test_stdout, test_stderr, failed_tests, verification_passed, details)`.
* **Called By**: `EvolutionEngine`.

### 2.6 Evaluation & Scoring (`apps/api/app/evaluation/scoring.py`)
* **Owns**: Mathematical aggregation of task evaluations into `GenerationMetrics` (accuracy, reliability, cost, latency, composite score).
* **Does NOT Own**: Rejection/acceptance decisions, agent execution.
* **Receives**: `task_metrics: list[ExecutionMetrics]`, `evaluations: list[TaskEvaluation]`.
* **Returns**: `GenerationMetrics`.
* **Called By**: `EvolutionEngine`.

### 2.7 Failure Diagnosis (`apps/api/app/evaluation/failure_analyzer.py`)
* **Owns**: Categorizing execution failures into fixed taxonomy (`REASONING_FAILURE`, `PLANNING_FAILURE`, `TOOL_SELECTION_FAILURE`, `TOOL_EXECUTION_FAILURE`, `CONTEXT_FAILURE`, `MEMORY_FAILURE`, `VERIFICATION_FAILURE`, `RECOVERY_FAILURE`, `TASK_MISINTERPRETATION`, `TIMEOUT`, `COST_LIMIT`).
* **Does NOT Own**: Modifying AgentSpec, executing tasks.
* **Receives**: `BenchmarkTask`, `AgentSpec`, `AgentState`, `TaskEvaluation`, `ExecutionMetrics`.
* **Returns**: `FailureAnalysis(task_id, failure_type, severity, evidence, root_cause, recommended_mutation, confidence)`.
* **Called By**: `EvolutionEngine`.

### 2.8 Memory & Self-Reflection (`apps/api/app/memory/`, `apps/api/app/agents/reflection.py`)
* **Owns**: Persistent discovery, storage, deduplication, and confidence scoring of tool playbooks and operational heuristics in SQLite.
* **Does NOT Own**: Short-term agent conversation history (`AgentState.messages`).
* **Receives**: Execution traces, tool error patterns, customer tier contexts.
* **Returns**: `ToolPlaybookEntry` objects and formatted prompt injection strings.
* **Called By**: `AgentRuntime`, `ExperimentService`.

### 2.9 Mutation Engine (`apps/api/app/evolution/mutation_generator.py`)
* **Owns**: Generating targeted architectural mutations (`PROMPT_UPDATE`, `PLANNER_UPDATE`, `TOOL_POLICY_UPDATE`, `MEMORY_UPDATE`, `VERIFIER_UPDATE`, `RETRY_POLICY_UPDATE`, `ORCHESTRATION_UPDATE`) based on empirical failure analysis.
* **Does NOT Own**: Arbitrary code generation, candidate acceptance.
* **Receives**: `current_spec: AgentSpec`, `failures: list[FailureAnalysis]`.
* **Returns**: `(candidate_spec: AgentSpec, mutation: Mutation)`.
* **Called By**: `EvolutionEngine`.

### 2.10 Acceptance Engine (`apps/api/app/evolution/acceptance.py`)
* **Owns**: Pareto multi-objective decision logic comparing candidate generation against parent baseline across accuracy, reliability, cost, and latency.
* **Does NOT Own**: Running benchmarks, saving generations.
* **Receives**: `parent: GenerationMetrics`, `candidate: GenerationMetrics`.
* **Returns**: `AcceptanceDecision(accepted, status, reason, accuracy_delta, reliability_delta, cost_delta_percent, latency_delta_percent, composite_delta)`.
* **Called By**: `EvolutionEngine`.

### 2.11 Tracing & Provenance (`apps/api/app/tracing/`, `apps/api/app/provenance/`)
* **Owns**: Recording canonical timeline events and calculating SHA-256 chained hashes over `(previous_hash + event_type + timestamp + canonical_json_payload)`. Verifying chain continuity and detecting payload tampering.
* **Does NOT Own**: Business logic decisions.
* **Receives**: `TraceEvent`.
* **Returns**: Signed `TraceEvent`, validation tuple `(is_valid: bool, broken_index: int | None, message: str)`.
* **Called By**: `EventRecorder`, `AgentRuntime`, `EvolutionEngine`, `ExperimentService`.

### 2.12 Application Services & API (`apps/api/app/services/`, `apps/api/app/api/`)
* **Owns**: Orchestration of domain components, database transactions (SQLAlchemy async sessions), SSE event broadcasting, HTTP REST serialization.
* **Does NOT Own**: Direct tool execution, model calling.
* **Receives**: Pydantic request models.
* **Returns**: Pydantic response models, SSE streams, audio streams.
* **Called By**: FastAPI router, Next.js Web Client.

---

## 3. Dependency Direction

Dependencies flow strictly inward from transport to abstractions:

```text
Presentation Layer (Next.js Web UI)
        ↓ HTTP / SSE
Transport Layer (FastAPI Routes: apps/api/app/api/routes.py)
        ↓ Calls
Application Service Layer (ExperimentService: apps/api/app/services/)
        ↓ Orchestrates
Domain Engine Layer (EvolutionEngine, AgentRuntime, FailureAnalyzer)
        ↓ Depends upon
Canonical Contracts (Protocols: LLMProvider, Tool, Benchmark, AgentSpec)
        ↓ Implemented by
Infrastructure & Persistence (SQLite Models, TensorMuxProvider, Tool Implementations)
```

**Invariants**:
* Zero circular dependencies.
* Domain engines depend on protocols (`LLMProvider`, `Tool`, `Benchmark`), never on concrete provider classes.
* No provider leakage into `app/agents/`, `app/evolution/`, or `app/tools/`.

---

## 4. Canonical Contract Definitions

### 4.1 LLMProvider Contract (`apps/api/app/providers/base.py`)
```python
@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        ...
```
* **Supported Implementations**: `TensorMuxProvider` (`glm-4-7-flash`), `AIGrantsIndiaProvider` (`gpt-5-nano`), `DeterministicMockProvider` (offline testing), `ExperientialProvider` (`gpt-6-astra`).
* **Factory**: `apps/api/app/providers/factory.py:get_llm_provider()`.

### 4.2 Tool Contract (`apps/api/app/tools/base.py`)
```python
@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        ...
```
* **Standard Suite**: `repository`, `file_editor`, `shell`, `test_runner`, `search`.
* **Third-Party Suite (Track 1)**: `linear_api`, `slack_api`, `crm_api`, `github_api`, `sentry_api`.
* **Security Gate**: All filesystem interactions pass through `sanitize_path(workspace, target_path)`.

### 4.3 Benchmark & Evaluator Contract (`apps/api/app/benchmarks/base.py`)
```python
@runtime_checkable
class Benchmark(Protocol):
    name: str
    version: str

    def list_tasks(self) -> list[BenchmarkTask]:
        ...

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        ...

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        ...
```
* **Benchmarks**: `software_engineering` (10 tasks), `third_party_automation` (10 tasks).

### 4.4 AgentSpec Contract (`apps/api/app/schemas/agent_spec.py`)
```python
class AgentSpec(BaseModel):
    model: str = "glm-4-7-flash"
    system_prompt: str
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    tools: list[str] = Field(default_factory=...)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)

    def canonical_dict(self) -> dict: ...
```

### 4.5 Failure Analysis Contract (`apps/api/app/evaluation/failure_analyzer.py`)
```python
class FailureAnalysis(BaseModel):
    task_id: str
    failure_type: FailureType
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    evidence: list[str]
    root_cause: str
    recommended_mutation: dict[str, Any]
    confidence: float
```

### 4.6 Acceptance Engine Contract (`apps/api/app/evolution/acceptance.py`)
```python
class AcceptanceEngine:
    def evaluate_candidate(
        self,
        parent: GenerationMetrics,
        candidate: GenerationMetrics,
    ) -> AcceptanceDecision:
        ...
```

### 4.7 Provenance & Event Chaining (`apps/api/app/provenance/hasher.py`)
```python
def sign_event(event: TraceEvent, previous_hash: str | None = None) -> TraceEvent: ...
def verify_event_chain(events: list[TraceEvent]) -> Tuple[bool, int | None, str]: ...
```
Hash equation:
$$\text{event\_hash} = \text{SHA-256}(\text{previous\_hash} + \text{event\_type} + \text{timestamp} + \text{canonical\_payload})$$

---

## 5. Generation Lineage & Data Model

Every generation in FORGE is persisted in SQLite with full lineage:
```text
Experiment (id, name, goal, benchmark_id, best_generation_id)
  └── Generation G0 (generation_number=0, agent_spec, metrics, status=COMPLETED)
        └── Mutation M1 (target=verifier, type=VERIFIER_UPDATE, observed_failure=...)
              └── Generation G1 (parent_id=G0, generation_number=1, status=ACCEPTED)
                    └── Mutation M2 (target=planner, type=PLANNER_UPDATE)
                          └── Generation G2 (parent_id=G1, generation_number=2, status=REJECTED)
```
* **Rejection Preservation**: Rejected candidates are stored with `status="REJECTED"` and `rejection_reason`. They remain permanently visible in the lineage tree.

---

## 6. Sponsor Integration Isolation

1. **TensorMux**: Isolated behind `TensorMuxProvider` (`apps/api/app/providers/tensormux.py`). Model defaults to `glm-4-7-flash`.
2. **AI Grants (OpenAI)**: Isolated behind `AIGrantsIndiaProvider` (`apps/api/app/providers/aigrants.py`). Model defaults to `gpt-5-nano`.
3. **Smallest.ai**: Isolated behind `SmallestAIVoiceService` (`apps/api/app/providers/voice.py`). Generates lightning-fast audio debriefs without impacting agent execution.
4. **Maximor AO**: Isolated behind `AOOrchestratorBridge` (`apps/api/app/agents/ao_integration.py`). Provides CLI status checks; fully optional at runtime.
