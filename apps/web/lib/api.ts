export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface Experiment {
  id: string;
  name: string;
  goal: string;
  benchmark_id: string;
  tool_ids: string[];
  current_generation_id: string | null;
  best_generation_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  generations_count: number;
  best_accuracy: number | null;
  best_reliability: number | null;
}

export interface Generation {
  id: string;
  experiment_id: string;
  parent_generation_id: string | null;
  generation_number: number;
  agent_spec: {
    model: string;
    system_prompt: string;
    planner: { type: string; max_subgoals: number; require_replan_on_error: boolean };
    tools: string[];
    memory: { type: string; max_history_items: number };
    verifier: { type: string; require_zero_failed_tests: boolean; enforce_before_complete: boolean };
    retry_policy: { max_attempts: number; retry_on_tool_failure: boolean; backoff_seconds: number };
    orchestration: { type: string };
  };
  mutation_id: string | null;
  metrics: {
    generation_number: number;
    total_tasks: number;
    successful_tasks: number;
    accuracy: number;
    reliability: number;
    total_cost_usd: number;
    avg_cost_per_task: number;
    avg_latency_ms: number;
    composite_score: number;
    total_tokens: number;
    total_model_calls: number;
    total_tool_calls: number;
    verification_pass_rate: number;
    failure_breakdown: Record<string, number>;
    recovery_rate?: number;
  } | null;
  benchmark_id: string;
  status: string;
  rejection_reason: string | null;
  created_at: string;
}

export interface TraceEvent {
  event_id: string;
  experiment_id: string;
  generation_id: string | null;
  execution_id: string | null;
  timestamp: string;
  type: string;
  payload: any;
  previous_event_hash: string;
  event_hash: string;
}

export interface ProvenanceReport {
  experiment_id: string;
  is_valid: boolean;
  total_events: number;
  broken_index: number | null;
  message: string;
  genesis_hash: string;
  latest_hash: string;
}

export async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }
  return res.json();
}

export interface ToolMemoryEntry {
  id: string;
  experiment_id: string;
  tool_name: string;
  category: "SCHEMA_QUIRK" | "CONTEXTUAL_LOGIC" | "WORKFLOW_DEPENDENCY" | "ERROR_RECOVERY" | string;
  pattern_trigger: string;
  learned_rule: string;
  evidence?: string;
  confidence: number;
  observation_count: number;
  created_at: string;
  execution_id?: string | null;
  failure_id?: string | null;
  reflection_id?: string | null;
}

export interface FailureEvidence {
  failure_id: string;
  task_id: string | null;
  execution_id: string | null;
  failure_type: string | null;
  root_cause: string | null;
  evidence: string[];
}

export interface MemoryEvidence {
  id: string;
  tool_name: string;
  category: string;
  pattern_trigger: string;
  learned_rule: string;
  evidence?: string;
  confidence: number;
  observation_count: number;
  execution_id?: string | null;
  failure_id?: string | null;
  reflection_id?: string | null;
}

export interface MutationEvidence {
  id: string;
  generation_id: string;
  mutation_type: string;
  target: string;
  before: any;
  after: any;
  reason: string;
  observed_failure?: string | null;
  expected_effect?: string | null;
  failure_cluster_id?: string | null;
  failure_ids?: string[];
}

export interface DecisionEvidence {
  decision_id?: string | null;
  accepted?: boolean;
  status?: string;
  reason?: string | null;
  dominance_result?: string | null;
  metrics_delta?: Record<string, any>;
  parent_generation_id?: string | null;
  candidate_generation_id?: string | null;
  mutation_id?: string | null;
}

export interface EvidenceResponse {
  generation: string | null;
  parent_generation: string | null;
  metrics: Record<string, any>;
  failures: FailureEvidence[];
  memory: MemoryEvidence[];
  mutations: MutationEvidence[];
  decision: DecisionEvidence;
  provenance: {
    valid: boolean;
    total_events: number;
    broken_index: number | null;
    message: string;
    genesis_hash: string;
    latest_hash: string;
  };
}

export interface LearningRunReport {
  experiment_id: string;
  status: string;
  run_1_cold: {
    description: string;
    tool_calls: number;
    errors_encountered: number;
    latency_ms: number;
    tokens: number;
    cost_usd: number;
    accuracy: number;
    failures_observed: string[];
  };
  run_2_warm: {
    description: string;
    tool_calls: number;
    errors_encountered: number;
    latency_ms: number;
    tokens: number;
    cost_usd: number;
    accuracy: number;
    failures_observed: string[];
  };
  efficiency_delta: {
    tool_call_reduction: string;
    latency_reduction: string;
    token_reduction: string;
    cost_reduction: string;
    accuracy_gain: string;
    errors_prevented: number;
  };
  learned_playbooks: ToolMemoryEntry[];
}

export const api = {
  getHealth: () => fetchJson<{ status: string; product: string }>("/health"),
  getExperiments: () => fetchJson<Experiment[]>("/experiments"),
  getExperiment: (id: string) => fetchJson<Experiment>(`/experiments/${id}`),
  createExperiment: (data: { name: string; goal: string; benchmark_id?: string; tools?: string[]; max_generations?: number }) =>
    fetchJson<Experiment>("/experiments", { method: "POST", body: JSON.stringify(data) }),

  generateAgent: (id: string) => fetchJson<Generation>(`/experiments/${id}/generate`, { method: "POST" }),
  runBenchmark: (id: string, taskLimit?: number) =>
    fetchJson<Generation>(`/experiments/${id}/run${taskLimit ? `?task_limit=${taskLimit}` : ""}`, { method: "POST" }),
  evolveAgent: (id: string, taskLimit?: number) =>
    fetchJson<Generation>(`/experiments/${id}/evolve${taskLimit ? `?task_limit=${taskLimit}` : ""}`, { method: "POST" }),

  getGenerations: (id: string) => fetchJson<Generation[]>(`/experiments/${id}/generations`),
  getGenerationDetail: (id: string) => fetchJson<{ generation: Generation; mutation: any; executions_count: number }>(`/generations/${id}`),
  getExecutions: (id: string) => fetchJson<any[]>(`/experiments/${id}/executions`),
  getEvents: (id: string, limit = 150) => fetchJson<TraceEvent[]>(`/experiments/${id}/events?limit=${limit}`),
  getProvenance: (id: string) => fetchJson<ProvenanceReport>(`/experiments/${id}/provenance`),
  getEvidence: (id: string, generationId?: string) =>
    fetchJson<EvidenceResponse>(`/experiments/${id}/evidence${generationId ? `?generation_id=${generationId}` : ""}`),
  getBenchmarks: () => fetchJson<any[]>("/benchmarks"),
  getTools: () => fetchJson<any[]>("/tools"),
  getNarrationAudioUrl: (genId: string) => `${API_BASE}/generations/${genId}/narrate`,

  getToolMemory: (id: string) => fetchJson<ToolMemoryEntry[]>(`/experiments/${id}/tool-memory`),
  runLearningLoop: (id: string) => fetchJson<LearningRunReport>(`/experiments/${id}/learning-run`, { method: "POST" }),
  getLearningNarrationAudioUrl: (expId: string) => `${API_BASE}/experiments/${expId}/learning-narrate`,

  // Agent Orchestrator (AO) Developer Harness API (FORGE S8-G/H/I Task C)
  getAOStatus: () =>
    fetchJson<{ running: boolean; exit_code?: number; output?: string; error?: string; pid?: number | null; port?: number | null }>("/ao/status"),
  getAODoctor: () =>
    fetchJson<{ available: boolean; installed: boolean; exit_code?: number; output?: string; error?: string; daemon_ok?: boolean; sqlite_ok?: boolean; harness_detected?: boolean; auth_ready?: boolean }>("/ao/doctor"),
};
