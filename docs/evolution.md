# FORGE Evolution Engine

## 1. The Evolutionary Cycle
FORGE evolves agents empirically using evidence from previous failures:

1. **Baseline ($G_0$)**: Initial architecture designed by `AgentArchitect` based on high-level goal and available tools.
2. **Benchmark Evaluation**: $G_0$ executes across benchmark tasks. Traces, tool results, and pytest logs are recorded.
3. **Failure Diagnosis**: `FailureAnalyzer` maps observed execution errors into a fixed taxonomy:
   - `VERIFICATION_FAILURE`
   - `PLANNING_FAILURE`
   - `TOOL_SELECTION_FAILURE`
   - `TOOL_EXECUTION_FAILURE`
   - `CONTEXT_FAILURE`
   - `RECOVERY_FAILURE`
   - `TIMEOUT`
   - `COST_LIMIT`
4. **Targeted Mutation**: `MutationGenerator` selects the dominant failure pattern and mutates the agent architecture:
   - `VERIFIER_UPDATE`: Introduces mandatory test verification gates.
   - `PLANNER_UPDATE`: Enables structured goal decomposition and replanning.
   - `RETRY_POLICY_UPDATE`: Enhances backoff and tool retry limits.
   - `PROMPT_UPDATE`: Injects targeted negative constraints and edge-case instructions.
5. **Candidate Evaluation**: Candidate generation $G_1$ executes on benchmark tasks.
6. **Pareto-Aware Acceptance**: `AcceptanceEngine` evaluates candidate metrics against parent metrics:
   - **ACCEPTED** if accuracy increases, or if reliability increases significantly without cost explosion.
   - **REJECTED** if accuracy degrades, or if trivial gains cause runaway cost/latency inflation.
   - Full rationale is recorded in the lineage.

## 2. Multi-Dimensional Scoring Function
The composite score balances correctness, reliability, and efficiency:
$$S_{\text{composite}} = 0.50 \times \text{Accuracy} + 0.30 \times \text{Reliability} + 0.10 \times S_{\text{cost}} + 0.10 \times S_{\text{speed}}$$

Where:
$$\text{Reliability} = 0.40 \times \text{VerifPass} + 0.30 \times (1 - \text{ToolErrorRate}) + 0.20 \times \text{CleanExit} + 0.10 \times \text{Recovery}$$
