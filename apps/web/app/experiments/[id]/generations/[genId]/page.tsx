"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Generation } from "../../../../../lib/api";
import {
  ArrowLeft,
  Cpu,
  Shield,
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileCode,
  Terminal,
  Activity,
  Layers,
  Volume2,
  GitBranch,
  Scale,
} from "lucide-react";

export default function GenerationDetailPage() {
  const params = useParams();
  const expId = params?.id as string;
  const genId = params?.genId as string;

  const [data, setData] = useState<{ generation: Generation; mutation: any; executions_count: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const handleToggleAudio = () => {
    if (isPlayingAudio) {
      audioRef.current?.pause();
      setIsPlayingAudio(false);
      return;
    }

    const audioUrl = api.getNarrationAudioUrl(genId);
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    setIsPlayingAudio(true);

    audio.onended = () => {
      setIsPlayingAudio(false);
    };

    audio.onerror = () => {
      alert("Unable to play voice debrief (check SMALLEST_API_KEY).");
      setIsPlayingAudio(false);
    };

    audio.play().catch((e) => {
      console.error(e);
      setIsPlayingAudio(false);
    });
  };

  useEffect(() => {
    if (!genId) return;
    api.getGenerationDetail(genId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [genId]);

  if (loading || !data) {
    return <div className="py-20 text-center text-gray-400">Loading generation architecture...</div>;
  }

  const { generation, mutation } = data;
  const spec = generation.agent_spec;
  const m = generation.metrics;

  const getStatusBadge = (status: string) => {
    if (status === "ACCEPTED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" /> ACCEPTED
        </span>
      );
    }
    if (status === "REJECTED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <XCircle className="w-3.5 h-3.5" /> REJECTED
        </span>
      );
    }
    if (status === "RUNNING") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
          <RotateCw className="w-3.5 h-3.5 animate-spin" /> RUNNING
        </span>
      );
    }
    if (status === "FAILED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-950/40 text-red-400 border border-red-500/40">
          <AlertTriangle className="w-3.5 h-3.5" /> FAILED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-gray-700/20 text-gray-400 border border-gray-700/30">
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <Link
        href={`/experiments/${expId}`}
        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Experiment Command Center
      </Link>

      {/* Header Card */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-white font-mono">Generation {generation.generation_number}</h1>
            {getStatusBadge(generation.status)}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <p className="text-xs text-gray-500 font-mono">ID: {generation.id}</p>
            <button
              onClick={handleToggleAudio}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border text-xs font-semibold transition-colors cursor-pointer ${
                isPlayingAudio
                  ? "bg-orange-500/20 text-orange-400 border-orange-500/50 animate-pulse"
                  : "bg-[#0d1117] border-[#30363d] text-gray-300 hover:text-white hover:border-gray-500"
              }`}
            >
              <Volume2 className="w-3.5 h-3.5" />
              {isPlayingAudio ? "Playing Voice Debrief..." : "Play Voice Debrief"}
            </button>
            <Link
              href={`/experiments/${expId}/compare`}
              className="inline-flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 font-semibold"
            >
              Compare with other generations →
            </Link>
          </div>
        </div>

        {/* Primary Metrics Strip */}
        {m && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-sm">
            <div>
              <span className="text-[11px] text-gray-500 block">Accuracy</span>
              <span className="font-bold text-emerald-400 text-lg">{(m.accuracy * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block">Reliability</span>
              <span className="font-bold text-cyan-400 text-lg">{(m.reliability * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block">Cost / task</span>
              <span className="text-amber-400 text-lg">${m.avg_cost_per_task.toFixed(4)}</span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 block">Latency / task</span>
              <span className="text-purple-400 text-lg">{(m.avg_latency_ms / 1000).toFixed(2)}s</span>
            </div>
          </div>
        )}
      </div>

      {/* Decision & Parent Generation Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Parent Generation */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
            <GitBranch className="w-4 h-4 text-orange-400" /> Parent Generation
          </div>
          {generation.parent_generation_id ? (
            <div className="space-y-1">
              <div className="text-sm font-bold text-white font-mono">
                Parent ID: {generation.parent_generation_id}
              </div>
              <p className="text-xs text-gray-400">
                Evolved from predecessor generation through automated mutation and candidate evaluation.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="text-sm font-bold text-white font-mono">
                None (Root Baseline Generation G0)
              </div>
              <p className="text-xs text-gray-400">
                Initial architecture synthesized directly by AgentArchitect from high-level experiment goal.
              </p>
            </div>
          )}
        </div>

        {/* Acceptance / Rejection Decision */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
            <Scale className="w-4 h-4 text-orange-400" /> Acceptance Decision
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(generation.status)}
            <span className="text-xs text-gray-400">
              {generation.status === "ACCEPTED" ? "Pareto dominant candidate" : "Pareto trade-off gate"}
            </span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">
            {generation.status === "REJECTED"
              ? generation.rejection_reason || "Candidate failed multi-objective Pareto trade-off relative to token cost."
              : generation.status === "ACCEPTED"
              ? "Candidate accepted: demonstrated empirical improvements in correctness and reliability without unacceptable cost regression."
              : "Generation status pending benchmark execution and Pareto trade-off evaluation."}
          </p>
        </div>
      </div>

      {/* Mutation Info if evolved */}
      {mutation ? (
        <div className="bg-[#161b22] border border-orange-500/30 rounded-xl p-6 shadow-md">
          <div className="flex items-center gap-2 text-orange-400 text-sm font-bold uppercase tracking-wider mb-2">
            <RotateCw className="w-4 h-4" /> Architectural Mutation from Parent
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-3 text-xs">
            <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 block">Mutation Type</span>
              <span className="font-mono text-white font-bold">{mutation.type}</span>
            </div>
            <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 block">Target Subsystem</span>
              <span className="font-mono text-white font-bold">{mutation.target}</span>
            </div>
            <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 block">Observed Failure Trigger</span>
              <span className="font-mono text-rose-400 font-bold">{mutation.observed_failure}</span>
            </div>
            <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 block">Expected Effect</span>
              <span className="text-gray-300">{mutation.expected_effect}</span>
            </div>
          </div>

          <div className="mt-4 p-3 rounded bg-[#0d1117] border border-[#30363d] text-xs">
            <span className="text-gray-500 block mb-1 font-semibold">Empirical Reason for Mutation:</span>
            <p className="text-gray-300">{mutation.reason}</p>
          </div>

          {/* Before vs After Diff */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 rounded bg-[#0a0c10] border border-rose-500/30">
              <span className="text-rose-400 font-bold block mb-1">- BEFORE (Parent)</span>
              <pre className="text-gray-400 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(mutation.before, null, 2)}</pre>
            </div>
            <div className="p-3 rounded bg-[#0a0c10] border border-emerald-500/30">
              <span className="text-emerald-400 font-bold block mb-1">+ AFTER (Mutated)</span>
              <pre className="text-gray-300 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(mutation.after, null, 2)}</pre>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 text-xs text-gray-400">
          <span className="font-semibold text-gray-300 block mb-1">Mutation Status:</span>
          Root Generation G0 — Initial architecture synthesized directly from goal; no parent mutation applied.
        </div>
      )}

      {/* Metrics Card */}
      {m && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 shadow-md space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" /> Full Evaluated Metrics
          </h2>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Accuracy</span>
              <span className="text-xl font-bold text-emerald-400 block mt-0.5">{(m.accuracy * 100).toFixed(1)}%</span>
              <span className="text-[10px] text-gray-500">{m.successful_tasks} of {m.total_tasks} passed</span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Reliability</span>
              <span className="text-xl font-bold text-cyan-400 block mt-0.5">{(m.reliability * 100).toFixed(1)}%</span>
              <span className="text-[10px] text-gray-500">Fidelity score</span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Composite Score</span>
              <span className="text-xl font-bold text-orange-400 block mt-0.5">{m.composite_score.toFixed(3)}</span>
              <span className="text-[10px] text-gray-500">Weighted index</span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Cost / task</span>
              <span className="text-xl font-bold text-amber-400 block mt-0.5">${m.avg_cost_per_task.toFixed(4)}</span>
              <span className="text-[10px] text-gray-500">${m.total_cost_usd.toFixed(4)} total</span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Latency / task</span>
              <span className="text-xl font-bold text-purple-400 block mt-0.5">{(m.avg_latency_ms / 1000).toFixed(2)}s</span>
              <span className="text-[10px] text-gray-500">{Math.round(m.avg_latency_ms)} ms avg</span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-gray-500 uppercase text-[10px] block">Tool Calls</span>
              <span className="text-xl font-bold text-white block mt-0.5">{m.total_tool_calls}</span>
              <span className="text-[10px] text-gray-500">{m.total_tasks > 0 ? (m.total_tool_calls / m.total_tasks).toFixed(1) : 0} calls/task</span>
            </div>
          </div>

          {/* Failure breakdown if present */}
          {m.failure_breakdown && Object.keys(m.failure_breakdown).length > 0 && (
            <div className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2">
              <span className="text-xs font-semibold text-gray-400 block">Failure Taxonomy Breakdown:</span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(m.failure_breakdown).map(([k, v]) => (
                  <span key={k} className="px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 font-mono text-xs font-semibold">
                    {k}: {v}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Declarative Agent Architecture Grid */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 shadow-md">
        <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-orange-400" /> Declarative AgentSpec
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Model & Inference</span>
            <span className="font-mono text-white text-sm font-bold">{spec.model}</span>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Planner Subsystem</span>
            <span className="font-mono text-cyan-400 text-sm font-bold">{spec.planner?.type || "none"}</span>
            <p className="text-[11px] text-gray-500 mt-1">Replan on error: {String(spec.planner?.require_replan_on_error)}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Verifier Subsystem</span>
            <span className="font-mono text-emerald-400 text-sm font-bold">{spec.verifier?.type || "none"}</span>
            <p className="text-[11px] text-gray-500 mt-1">Zero failed tests required: {String(spec.verifier?.require_zero_failed_tests)}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Orchestration</span>
            <span className="font-mono text-amber-400 text-sm font-bold">{spec.orchestration?.type || "direct"}</span>
            <p className="text-[11px] text-gray-500 mt-1">Execution loop pattern</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Retry Policy</span>
            <span className="font-mono text-purple-400 text-sm font-bold">{spec.retry_policy?.max_attempts} attempts</span>
            <p className="text-[11px] text-gray-500 mt-1">Backoff: {spec.retry_policy?.backoff_seconds}s</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <span className="text-gray-500 font-semibold uppercase block mb-1">Working Memory</span>
            <span className="font-mono text-white text-sm font-bold">{spec.memory?.type || "working_context"}</span>
            <p className="text-[11px] text-gray-500 mt-1">Max history items: {spec.memory?.max_history_items || 30}</p>
          </div>
        </div>

        {/* System Prompt */}
        <div className="mt-4 p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
          <span className="text-xs font-semibold text-gray-400 block mb-1">Synthesized System Prompt</span>
          <p className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{spec.system_prompt}</p>
        </div>

        {/* Tools */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500 font-semibold">Enabled Tools:</span>
          {spec.tools.map((t) => (
            <span key={t} className="px-2.5 py-1 rounded bg-[#0d1117] border border-[#30363d] text-xs font-mono text-gray-300">
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
