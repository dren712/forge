# FORGE — Model Intelligence Layer & Provider Abstraction (Section S2)

**Status**: Verified & Operational  
**Last Audited**: September 6, 2026  
**Primary Engine**: TensorMux (`glm-4-7-flash`)  
**Reasoning & Reflection Engine**: OpenAI AI Grants (`gpt-5-nano`)  
**Offline Deterministic Engine**: `DeterministicMockProvider`  

---

## 1. Provider Architecture Overview

FORGE implements a strictly decoupled, provider-agnostic model intelligence architecture. The core agent runtime, evolutionary architect, failure analyzer, and reflection engines depend entirely on the `LLMProvider` protocol rather than vendor-specific SDK classes.

```text
FORGE Agent Subsystems
(Architect, AgentRuntime, FailureAnalyzer, MutationGenerator)
                           │
                           ▼
          apps/api/app/providers/router.py:ModelRouter
          apps/api/app/providers/factory.py:get_llm_provider
                           │
                           ▼
          apps/api/app/providers/base.py:LLMProvider (Protocol)
     ┌─────────────────────┼─────────────────────┬─────────────────────┐
     ▼                     ▼                     ▼                     ▼
TensorMuxProvider     AIGrantsIndiaProvider  DeterministicMock    ExperientialProvider
 (glm-4-7-flash)         (gpt-5-nano)         (Offline CI Suite)     (gpt-6-astra)
     │                     │                     │                     │
     └─────────────────────┴─────────────────────┴─────────────────────┘
                           │
                           ▼
              Normalized LLMResponse & ToolCall
            (content, tool_calls, usage, latency, finish_reason)
```

---

## 2. Canonical Provider Contract

The canonical protocol is defined in `apps/api/app/providers/base.py`:

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
        """Generate normalized response from the model."""
        ...
```

### 2.1 Normalized Response & Tool Call Models
```python
class ToolCallItem(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]

# Canonical alias
ToolCall = ToolCallItem

class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCallItem] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str | None = None
    provider: str = ""
    model: str = ""
    raw_response: Any = None
```

---

## 3. Truthful Provider Status Table

| Capability | TensorMux (`glm-4-7-flash`) | OpenAI (`gpt-5-nano`) | Deterministic Mock |
| :--- | :--- | :--- | :--- |
| **Basic Generation** | `VERIFIED` (Live: 2063ms, 133 tokens) | `VERIFIED` (Live: 1487ms, 199 tokens) | `VERIFIED` (Offline: 0.1ms) |
| **Structured Tool Calling** | `VERIFIED` (Live: `read_file` called) | `VERIFIED` (Live: `read_file` called) | `VERIFIED` (Simulated tool calls) |
| **Multi-Turn Continuation** | `VERIFIED` (Live: 3-turn loop passed) | `VERIFIED` (Live: 3-turn loop passed) | `VERIFIED` (Multi-step verification) |
| **Structured Output / JSON** | `VERIFIED` (Schema repair & retry) | `VERIFIED` (Schema repair & retry) | `VERIFIED` (Deterministic JSON) |
| **Streaming Token Delivery** | `PARTIAL` (HTTP stream works, generator teardown issue in Python 3.13) | `UNVERIFIED` (Not currently requested by agent runtime) | `N/A` (Deterministic batch) |
| **Usage / Token Accounting** | `VERIFIED` (prompt, completion, total) | `VERIFIED` (prompt, completion, total) | `VERIFIED` (Simulated usage metrics) |
| **Timeout Handling** | `VERIFIED` (`ProviderTimeoutError`) | `VERIFIED` (`ProviderTimeoutError`) | `VERIFIED` (Controlled execution) |
| **Error Normalization** | `VERIFIED` (`AuthenticationError`, `BadRequest`) | `VERIFIED` (`AuthenticationError`, `BadRequest`) | `VERIFIED` (Normalized hierarchy) |

---

## 4. Live Verification Findings

### 4.1 TensorMux Live Verification
* **Script**: `scripts/test_tensormux.py` and `scripts/test_live_models.py`
* **Target Endpoint**: `https://api.tensormux.com/v1`
* **Model**: `glm-4-7-flash`
* **Single Turn**: Returned `'pong'` in 2,063.42ms (29 input tokens, 104 output tokens).
* **Tool Calling & Multi-Turn**:
  - Turn 1 (Tool Call): Emitted native `tool_calls` for `read_file` (`{'path': 'README.md'}`) in 1,318.4ms (211 input, 45 output tokens).
  - Turn 2: Executed `SimpleReadFileTool` in sandbox.
  - Turn 3 (Final Answer): Received tool output, synthesized final tagline: `"Agents don't just run. They evolve."` in 861.5ms (252 input, 67 output tokens).
  - Total latency: 2,179.9ms, Total tokens: 575.
* **AgentRuntime Execution**: Executed `AgentRuntime` live with `TensorMuxProvider` on file inspection task. Reached `COMPLETED` in 3 steps, 2 tool calls, 1,824 tokens, 4,453.9ms.

### 4.2 OpenAI (AI Grants) Live Verification
* **Script**: `scripts/test_live_models.py`
* **Target Endpoint**: `https://api.openai.com/v1`
* **Model**: `gpt-5-nano`
* **Tool Calling & Multi-Turn**:
  - Turn 1 (Tool Call): Emitted native `tool_calls` for `read_file` (`{'path': 'README.md'}`) in 1,487.9ms (175 input, 24 output tokens).
  - Turn 2: Executed `SimpleReadFileTool` in sandbox.
  - Turn 3 (Final Answer): Received tool output, generated answer: `"The tagline is: 'Agents don't just run. They evolve.'"` in 1,745.4ms (228 input, 214 output tokens).
  - Total latency: 3,233.3ms, Total tokens: 641.

---

## 5. Model Roles & Configuration-Driven Routing

The `ModelRouter` (`apps/api/app/providers/router.py`) maps functional roles to configured inference providers:

```env
# Centralized Environment Overrides
FORGE_LLM_PROVIDER=tensormux
FORGE_ARCHITECT_PROVIDER=tensormux
FORGE_EXECUTOR_PROVIDER=tensormux
FORGE_REFLECTOR_PROVIDER=openai
FORGE_MUTATOR_PROVIDER=tensormux
```

* **`ARCHITECT`**: Generates initial candidate `AgentSpec` structures. Defaults to TensorMux.
* **`EXECUTOR`**: Powers the high-throughput `AgentRuntime` ReAct tool loop. Defaults to TensorMux (`glm-4-7-flash`).
* **`REFLECTOR`**: High-confidence reasoning engine for analyzing execution traces and distilling tool playbooks. Defaults to OpenAI (`gpt-5-nano`).
* **`MUTATOR`**: Proposes targeted mutations to AgentSpec based on failure analysis. Defaults to TensorMux.
* **`NARRATOR`**: Synthesizes audio debriefs via Smallest.ai voice TTS.

---

## 6. Structured Output & Bounded JSON Repair

Three core components require structured outputs:
1. **AgentArchitect**: Produces Pydantic-validated `AgentSpec`.
2. **FailureAnalyzer**: Produces Pydantic-validated `FailureAnalysis`.
3. **MutationGenerator**: Produces Pydantic-validated `Mutation`.

### Repair Invariants
* Markdown code fences (```` ```json { ... } ``` ````) and outermost curly braces are extracted.
* If parsing or validation fails, bounded retries (maximum 3 attempts) are executed with explicit validation error feedback.
* Silent coercion of nonsense is strictly prohibited; invalid payloads after 3 attempts raise `ProviderResponseFormatError`.

---

## 7. Error Normalization Hierarchy

All provider exceptions are caught and transformed into normalized `ForgeError` subclasses (`apps/api/app/core/errors.py`):

```text
ForgeError
  └── ProviderError
        ├── ProviderAuthenticationError   (Invalid/missing API key)
        ├── ProviderInvalidRequestError    (400 Bad Request, invalid schema)
        ├── ProviderTimeoutError           (Request deadline exceeded)
        ├── ProviderRateLimitError         (429 Too Many Requests)
        └── ProviderResponseFormatError    (Malformed JSON / schema mismatch)
```

Raw SDK exceptions (`openai.BadRequestError`, `openai.AuthenticationError`, etc.) never leak past the provider boundary into agent or domain logic.

---

## 8. Empirical Token Accounting & Cost Estimation

Estimated pricing rates per 1,000 tokens are defined as configured estimates in `apps/api/app/evaluation/metrics.py`:
* **`glm-4-7-flash`**: \$0.0005 prompt / \$0.0015 completion
* **`gpt-5-nano`**: \$0.00015 prompt / \$0.0006 completion

Total cost is calculated empirically from exact token counts reported by providers:
$$\text{Cost} = \left(\frac{\text{input\_tokens}}{1000} \times \text{Price}_{\text{prompt}}\right) + \left(\frac{\text{output\_tokens}}{1000} \times \text{Price}_{\text{completion}}\right)$$

Tokens are recorded on `TraceEvent` objects and aggregated into `GenerationMetrics`.

---

## 9. Secret Safety & Diagnostics

1. **Zero Secret Leakage**: An automated audit of all tracked files in git confirmed zero API keys are committed or exposed.
2. **Non-Secret Diagnostics Endpoint**: `GET /api/providers/status` reports provider configuration flags, model identifiers, and base URLs without ever exposing secrets:
```json
{
  "active_primary_provider": "tensormux",
  "test_mode": false,
  "role_routing": {
    "ARCHITECT": "tensormux",
    "EXECUTOR": "tensormux",
    "REFLECTOR": "openai",
    "MUTATOR": "tensormux"
  },
  "providers": {
    "tensormux": {
      "configured": true,
      "model": "glm-4-7-flash",
      "base_url": "https://api.tensormux.com/v1"
    },
    "aigrants": {
      "configured": true,
      "model": "gpt-5-nano",
      "base_url": "https://api.openai.com/v1"
    },
    "smallest_voice": {
      "configured": true,
      "voice_id": "emily"
    }
  }
}
```

---

## 10. Known Limitations

1. **Python 3.13 Stream Teardown**: TensorMux API supports SSE streaming chunks, but the current `httpcore2` async generator teardown in Python 3.13 can throw a cleanup warning if the stream is closed prematurely. Non-streaming ReAct execution is the verified production path.
2. **Tool Call Arguments Formatting**: Upstream API requires `function.arguments` in assistant messages to be strictly JSON-serialized with double quotes (`json.dumps(args)`). `AgentRuntime` enforces this normalization.
