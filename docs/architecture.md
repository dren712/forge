# FORGE System Architecture

## 1. System Overview
FORGE is structured as an autonomous agent engineering and evolution engine with clear boundary isolation between components:

```
┌─────────────────────────────────────────────────────────────┐
│                    FORGE Web Dashboard                      │
│        (Next.js 14, TypeScript, Tailwind, Lucide)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / SSE Stream
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      FORGE REST API                         │
│               (FastAPI, Pydantic, SQLAlchemy)               │
├──────────────────────────────┬──────────────────────────────┤
│  Agent Evolution Engine      │  Tamper-Evident Provenance   │
│  - FailureAnalyzer           │  - SHA-256 Chained Hasher    │
│  - MutationGenerator         │  - EventRecorder             │
│  - AcceptanceEngine          │  - Chain Validator           │
├──────────────────────────────┼──────────────────────────────┤
│  Agent Runtime & Verifier    │  Controlled Benchmark Suite  │
│  - AgentArchitect            │  - 10 Software Eng. Tasks    │
│  - Step Execution Loop       │  - Real Pytest Codebases     │
│  - State & Context Manager   │  - Evaluator & Scoring       │
├──────────────────────────────┴──────────────────────────────┤
│                 Sandboxed Tool Subsystem                    │
│      (Repository, File Editor, Shell, TestRunner, Search)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Inference Provider Layer (LLMProvider)         │
│  TensorMuxProvider (GLM-4.7-Flash) / Deterministic Mock     │
└─────────────────────────────────────────────────────────────┘
```

## 2. Module Boundaries
- **`app/core`**: Configuration (`config.py`), Structured Logging (`logging.py`), Error Hierarchy (`errors.py`), Database Engine (`database.py`).
- **`app/providers`**: `LLMProvider` protocol interface isolating all model calls. `TensorMuxProvider` provides OpenAI-compatible access to GLM-4.7-Flash.
- **`app/schemas`**: Strongly typed `AgentSpec`, API payloads, and execution models.
- **`app/tools`**: Sandboxed tools ensuring all filesystem operations are strictly confined to the task workspace.
- **`app/agents`**: `AgentArchitect` (designs AgentSpec), `AgentRuntime` (executes loop), `AgentVerifier` (enforces completion criteria).
- **`app/benchmarks`**: 10 controlled, reproducible software engineering tasks with automated evaluation.
- **`app/evaluation`**: Failure taxonomy, empirical root-cause analysis, multi-dimensional metrics (accuracy, reliability, cost, latency).
- **`app/evolution`**: Targeted mutation operators, candidate generation, Pareto-aware acceptance logic.
- **`app/provenance`**: Audit-grade cryptographic SHA-256 event chaining.

## 3. Security Boundaries
1. **Workspace Sandboxing**: Path traversal attempts (e.g. `../../etc/passwd`) are intercepted and rejected via `sanitize_path`.
2. **Restricted Shell**: Shell executions are confined to the workspace directory with timeouts and blacklisted dangerous commands.
3. **Secret Scrubbing**: Environment variables containing keys or credentials are automatically scrubbed from subprocess environments.
