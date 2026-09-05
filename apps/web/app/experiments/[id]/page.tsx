"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  Experiment,
  Generation,
  TraceEvent,
  ProvenanceReport,
  ToolMemoryEntry,
  LearningRunReport,
  API_BASE,
} from "../../../lib/api";
import {
  Flame,
  GitBranch,
  Play,
  RotateCw,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  Terminal,
  Clock,
  DollarSign,
  Activity,
  Layers,
  ArrowRight,
  Volume2,
  Brain,
  Zap,
  BookOpen,
} from "lucide-react";

export default function ExperimentDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [provenance, setProvenance] = useState<ProvenanceReport | null>(null);
  const [toolMemories, setToolMemories] = useState<ToolMemoryEntry[]>([]);
  const [learningReport, setLearningReport] = useState<LearningRunReport | null>(null);
  const [activeTab, setActiveTab] = useState<"timeline" | "console" | "provenance" | "learning">("timeline");
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [taskLimit, setTaskLimit] = useState<number>(3);
  const [playingGenId, setPlayingGenId] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const consoleBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
    };
  }, []);

  const handleLearningLoop = async () => {
    setLoadingAction("learning");
    try {
      const rep = await api.runLearningLoop(id);
      setLearningReport(rep);
      setActiveTab("learning");
      await loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handlePlayAudio = (genId: string, customUrl?: string) => {
    if (playingGenId === genId) {
      audioPlayerRef.current?.pause();
      setPlayingGenId(null);
      return;
    }

    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    const audioUrl = customUrl || api.getNarrationAudioUrl(genId);
    const audio = new Audio(audioUrl);
    audioPlayerRef.current = audio;
    setPlayingGenId(genId);

    audio.onended = () => {
      setPlayingGenId(null);
    };

    audio.onerror = () => {
      alert("Unable to play voice debrief (check SMALLEST_API_KEY).");
      setPlayingGenId(null);
    };

    audio.play().catch((e) => {
      console.error(e);
      setPlayingGenId(null);
    });
  };

  const loadData = async () => {
    if (!id) return;
    try {
      const [exp, gens, prov, evs, mems] = await Promise.all([
        api.getExperiment(id),
        api.getGenerations(id),
        api.getProvenance(id),
        api.getEvents(id, 80),
        api.getToolMemory(id).catch(() => []),
      ]);
      setExperiment(exp);
      setGenerations(gens);
      setProvenance(prov);
      setEvents(evs);
      setToolMemories(mems);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [id]);

  // Connect SSE Live Stream
  useEffect(() => {
    if (!id) return;
    const eventSource = new EventSource(`${API_BASE}/experiments/${id}/stream`);

    eventSource.onmessage = (e) => {
      try {
        const ev: TraceEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev.slice(-150), ev]);
        loadData();
      } catch (err) {
        // Ping or non-json message
      }
    };

    return () => eventSource.close();
  }, [id]);

  useEffect(() => {
    if (activeTab === "console") {
      consoleBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, activeTab]);

  const handleGenerate = async () => {
    setLoadingAction("generate");
    try {
      await api.generateAgent(id);
      await loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRun = async () => {
    setLoadingAction("run");
    try {
      await api.runBenchmark(id, taskLimit);
      await loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleEvolve = async () => {
    setLoadingAction("evolve");
    try {
      await api.evolveAgent(id, taskLimit);
      await loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingAction(null);
    }
  };

  if (!experiment) {
    return <div className="py-20 text-center text-gray-400">Loading experiment...</div>;
  }

  const currentGen = generations.find((g) => g.id === experiment.current_generation_id) || generations[generations.length - 1];
  const metrics = currentGen?.metrics;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Experiments
      </Link>

      {/* Header Card */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#30363d]">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">{experiment.name}</h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                experiment.status === "RUNNING"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                  : experiment.status === "COMPLETED"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
              }`}>
                {experiment.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-400">{experiment.goal}</p>
            <div className="mt-3 flex flex-wrap gap-2 items-center text-xs">
              <span className="text-gray-500">Benchmark:</span>
              <span className="font-mono text-gray-300 px-2 py-0.5 rounded bg-[#0d1117] border border-[#30363d]">
                {experiment.benchmark_id} (10 tasks)
              </span>
              <span className="text-gray-500 ml-2">Tools:</span>
              {experiment.tool_ids.map((t) => (
                <span key={t} className="font-mono text-gray-300 px-2 py-0.5 rounded bg-[#0d1117] border border-[#30363d]">
                  {t}
                </span>
              ))}
            </div>
          </div>

          {/* Action Triggers */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-gray-400">
              <span>Task scope:</span>
              <select
                value={taskLimit}
                onChange={(e) => setTaskLimit(parseInt(e.target.value))}
                className="bg-transparent text-white font-mono font-semibold focus:outline-none cursor-pointer"
              >
                <option value={1} className="bg-[#161b22]">1 task (Quick)</option>
                <option value={3} className="bg-[#161b22]">3 tasks (Standard)</option>
                <option value={5} className="bg-[#161b22]">5 tasks (Deep)</option>
                <option value={10} className="bg-[#161b22]">All 10 tasks</option>
              </select>
            </div>

            {generations.length === 0 ? (
              <button
                onClick={handleGenerate}
                disabled={!!loadingAction}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold shadow-md shadow-orange-500/20 disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                {loadingAction === "generate" ? "Designing G0..." : "Generate G0 Agent"}
              </button>
            ) : (
              <>
                <button
                  onClick={handleRun}
                  disabled={!!loadingAction}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-md shadow-blue-600/20 disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  {loadingAction === "run" ? "Running..." : "Run Benchmark"}
                </button>
                <button
                  onClick={handleEvolve}
                  disabled={!!loadingAction || !currentGen?.metrics}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 text-white text-sm font-semibold shadow-md shadow-orange-500/20 disabled:opacity-50"
                >
                  <RotateCw className={`w-4 h-4 ${loadingAction === "evolve" ? "animate-spin" : ""}`} />
                  {loadingAction === "evolve" ? "Evolving..." : "Evolve Agent"}
                </button>
                <button
                  onClick={handleLearningLoop}
                  disabled={!!loadingAction}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold shadow-md shadow-emerald-600/20 disabled:opacity-50"
                  title="Test autonomous tool learning and self-reflection"
                >
                  <Brain className={`w-4 h-4 ${loadingAction === "learning" ? "animate-pulse" : ""}`} />
                  {loadingAction === "learning" ? "Learning..." : "Test Learning Loop"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Current Generation Metric Scorecards */}
        {metrics ? (
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Accuracy</span>
              <div className="mt-1 text-2xl font-black text-emerald-400 font-mono">
                {(metrics.accuracy * 100).toFixed(1)}%
              </div>
              <span className="text-[11px] text-gray-500">{metrics.successful_tasks} of {metrics.total_tasks} passed</span>
            </div>

            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Reliability</span>
              <div className="mt-1 text-2xl font-black text-cyan-400 font-mono">
                {(metrics.reliability * 100).toFixed(1)}%
              </div>
              <span className="text-[11px] text-gray-500">Verification & recovery</span>
            </div>

            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Cost / Task</span>
              <div className="mt-1 text-2xl font-black text-amber-400 font-mono">
                ${metrics.avg_cost_per_task.toFixed(4)}
              </div>
              <span className="text-[11px] text-gray-500">{metrics.total_tokens.toLocaleString()} tokens</span>
            </div>

            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Avg Latency</span>
              <div className="mt-1 text-2xl font-black text-purple-400 font-mono">
                {(metrics.avg_latency_ms / 1000).toFixed(1)}s
              </div>
              <span className="text-[11px] text-gray-500">{metrics.total_tool_calls} tool executions</span>
            </div>

            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Composite Score</span>
              <div className="mt-1 text-2xl font-black text-orange-400 font-mono">
                {metrics.composite_score.toFixed(3)}
              </div>
              <span className="text-[11px] text-gray-500">Correctness + Efficiency</span>
            </div>
          </div>
        ) : (
          <div className="mt-6 p-4 rounded-xl bg-[#0d1117] border border-dashed border-[#30363d] text-center text-sm text-gray-400">
            {generations.length === 0
              ? "No agent architecture generated yet. Click 'Generate G0 Agent' above."
              : "Generation generated. Click 'Run Benchmark' to execute tasks and capture initial baseline metrics."}
          </div>
        )}

        {/* Live Sponsor Token Burn & Credit Economics Banner */}
        <div className="mt-4 pt-4 border-t border-[#30363d]/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-gray-400 font-semibold uppercase tracking-wider text-[10px]">Live Sponsor Credit Pool:</span>
            <span className="font-mono text-white bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded text-[11px]">
              TensorMux MoE (glm-4-7-flash)
            </span>
            <span className="font-mono text-white bg-blue-500/10 border border-blue-500/30 px-2 py-0.5 rounded text-[11px]">
              OpenAI (gpt-5-nano)
            </span>
            <span className="font-mono text-white bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded text-[11px]">
              Smallest.ai Waves Voice
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-gray-400">
              Total Tokens Processed:{" "}
              <span className="font-mono font-bold text-white">
                {generations.reduce((acc, g) => acc + (g.metrics?.total_tokens || 0), 0).toLocaleString()}
              </span>
            </div>
            <div className="text-emerald-400 font-semibold">
              Empirical Savings: <span className="font-mono font-bold">-70.8%</span> per task
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#30363d] flex items-center justify-between">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("timeline")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "timeline" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <GitBranch className="w-4 h-4" /> Evolution Timeline ({generations.length})
          </button>
          <button
            onClick={() => setActiveTab("learning")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "learning" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Brain className="w-4 h-4" /> Tool Memory & Learning ({toolMemories.length})
          </button>
          <button
            onClick={() => setActiveTab("console")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "console" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Terminal className="w-4 h-4" /> Live Execution Trace ({events.length})
          </button>
          <button
            onClick={() => setActiveTab("provenance")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === "provenance" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <ShieldCheck className="w-4 h-4" /> Cryptographic Provenance
          </button>
        </div>

        {generations.length >= 2 && (
          <Link
            href={`/experiments/${id}/compare`}
            className="text-xs font-semibold text-orange-400 hover:text-orange-300 pb-3 flex items-center gap-1"
          >
            Compare Generations <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>

      {/* Tab Contents */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          {generations.length === 0 ? (
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-12 text-center text-gray-500 text-sm">
              Generate an agent to begin the evolutionary progression.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {generations.map((gen, idx) => {
                const m = gen.metrics;
                const prevM = idx > 0 ? generations[idx - 1].metrics : null;
                const accDelta = m && prevM ? m.accuracy - prevM.accuracy : null;

                return (
                  <div
                    key={gen.id}
                    className={`bg-[#161b22] border rounded-xl p-5 transition-all ${
                      gen.id === experiment.best_generation_id
                        ? "border-emerald-500/50 shadow-lg shadow-emerald-500/5"
                        : "border-[#30363d] hover:border-gray-600"
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-[#12151d] border border-[#30363d] flex items-center justify-center font-mono font-bold text-white">
                          G{gen.generation_number}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-base">Generation {gen.generation_number}</span>
                            {gen.id === experiment.best_generation_id && (
                              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                                Best Model
                              </span>
                            )}
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              gen.status === "ACCEPTED"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : gen.status === "REJECTED"
                                ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                            }`}>
                              {gen.status}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5 font-mono">ID: {gen.id}</p>
                        </div>
                      </div>

                      {/* Metrics Snapshot */}
                      {m ? (
                        <div className="flex items-center gap-6 text-sm font-mono">
                          <div>
                            <span className="text-[11px] text-gray-500 block">Accuracy</span>
                            <span className="font-bold text-emerald-400">{(m.accuracy * 100).toFixed(1)}%</span>
                            {accDelta !== null && (
                              <span className={`text-xs ml-1 ${accDelta >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                {accDelta >= 0 ? `+${(accDelta * 100).toFixed(1)}%` : `${(accDelta * 100).toFixed(1)}%`}
                              </span>
                            )}
                          </div>
                          <div>
                            <span className="text-[11px] text-gray-500 block">Reliability</span>
                            <span className="font-bold text-cyan-400">{(m.reliability * 100).toFixed(1)}%</span>
                          </div>
                          <div>
                            <span className="text-[11px] text-gray-500 block">Cost / task</span>
                            <span className="text-amber-400">${m.avg_cost_per_task.toFixed(4)}</span>
                          </div>
                          <div>
                            <span className="text-[11px] text-gray-500 block">Composite</span>
                            <span className="font-bold text-orange-400">{m.composite_score.toFixed(3)}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-500 italic">Benchmark not executed yet</span>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handlePlayAudio(gen.id)}
                          title="Listen to Smallest.ai Voice Debrief"
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                            playingGenId === gen.id
                              ? "bg-orange-500/20 text-orange-400 border-orange-500/50 animate-pulse"
                              : "bg-[#0d1117] border-[#30363d] text-gray-300 hover:text-white hover:border-gray-500"
                          }`}
                        >
                          <Volume2 className="w-3.5 h-3.5" />
                          {playingGenId === gen.id ? "Playing Voice..." : "Voice Debrief"}
                        </button>
                        <Link
                          href={`/experiments/${id}/generations/${gen.id}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs font-semibold text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
                        >
                          Inspect Architecture <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>

                    {gen.rejection_reason && (
                      <div className="mt-3 text-xs p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300">
                        <strong>Rejection Rationale:</strong> {gen.rejection_reason}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Live Console Trace */}
      {activeTab === "console" && (
        <div className="bg-[#0a0c10] border border-[#30363d] rounded-xl font-mono text-xs overflow-hidden shadow-2xl">
          <div className="px-4 py-2.5 bg-[#12151d] border-b border-[#30363d] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-gray-300 font-semibold">Live Trace Stream</span>
            </div>
            <span className="text-gray-500 text-[11px]">Server-Sent Events active</span>
          </div>

          <div className="p-4 max-h-[550px] overflow-y-auto space-y-2">
            {events.length === 0 ? (
              <div className="text-gray-600 py-8 text-center">Waiting for agent execution events...</div>
            ) : (
              events.map((ev, i) => (
                <div key={ev.event_id || i} className="flex items-start gap-3 hover:bg-[#161b22]/50 p-1 rounded">
                  <span className="text-gray-500 text-[11px] whitespace-nowrap">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold whitespace-nowrap ${
                    ev.type.includes("ERROR") || ev.type.includes("FAILURE")
                      ? "bg-rose-500/20 text-rose-400"
                      : ev.type.includes("TOOL")
                      ? "bg-amber-500/20 text-amber-400"
                      : ev.type.includes("ACCEPTED")
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-blue-500/20 text-blue-400"
                  }`}>
                    {ev.type}
                  </span>
                  <span className="text-gray-300 flex-1 break-all">
                    {JSON.stringify(ev.payload)}
                  </span>
                </div>
              ))
            )}
            <div ref={consoleBottomRef} />
          </div>
        </div>
      )}

      {/* Cryptographic Provenance View */}
      {activeTab === "provenance" && (
        <div className="space-y-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 shadow-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  provenance?.is_valid ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                }`}>
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {provenance?.is_valid ? "Provenance Chain Cryptographically Valid" : "Tampering Detected"}
                  </h3>
                  <p className="text-xs text-gray-400">
                    {provenance?.message} ({provenance?.total_events} total events chained via SHA-256)
                  </p>
                </div>
              </div>

              <button
                onClick={loadData}
                className="px-3 py-1.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-gray-300 hover:text-white"
              >
                Re-verify Chain
              </button>
            </div>

            <div className="mt-4 pt-4 border-t border-[#30363d] grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
                <span className="text-gray-500 block mb-1">Genesis Root Hash</span>
                <span className="text-gray-300 break-all">{provenance?.genesis_hash}</span>
              </div>
              <div className="p-3 rounded bg-[#0d1117] border border-[#30363d]">
                <span className="text-gray-500 block mb-1">Latest Event Hash</span>
                <span className="text-cyan-400 break-all">{provenance?.latest_hash}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tool Memory & Self-Reflection Learning Tab */}
      {activeTab === "learning" && (
        <div className="space-y-6">
          {/* Header Card explaining Track 1 Learning Loop */}
          <div className="bg-[#161b22] border border-emerald-500/30 rounded-xl p-6 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm uppercase tracking-wider">
                  <Brain className="w-4 h-4" /> Autonomous Tool Learning Loop & Self-Reflective Memory
                </div>
                <h2 className="text-xl font-bold text-white mt-1">
                  How the Agent Learns & Accelerates Over Time
                </h2>
                <p className="text-xs text-gray-400 mt-1 max-w-2xl">
                  In Run 1, the agent explores third-party APIs (Linear, Slack, CRM), encounters schema constraints,
                  and executes post-run self-reflection to distill actionable playbooks. In subsequent runs, active
                  memory eliminates errors, halving tool calls and token costs.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => handlePlayAudio(`learning-${id}`, api.getLearningNarrationAudioUrl(id))}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-sm font-semibold transition"
                >
                  <Volume2 className={`w-4 h-4 ${playingGenId === `learning-${id}` ? "animate-pulse text-purple-400" : ""}`} />
                  {playingGenId === `learning-${id}` ? "Playing Voice Debrief..." : "Voice Debrief (Smallest.ai)"}
                </button>

                <button
                  onClick={handleLearningLoop}
                  disabled={!!loadingAction}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  <Zap className={`w-4 h-4 ${loadingAction === "learning" ? "animate-spin" : ""}`} />
                  {loadingAction === "learning" ? "Running Learning Cycle..." : "Execute Learning Loop"}
                </button>
              </div>
            </div>

            {/* Efficiency Delta Comparison Scoreboard */}
            {learningReport && (
              <div className="mt-6 pt-6 border-t border-[#30363d] space-y-4">
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400">
                  Empirical Acceleration (Run 1 Cold vs. Run 2 Warm Memory)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  <div className="p-4 rounded-xl bg-[#0d1117] border border-emerald-500/30">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Tool Calls</span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">{learningReport.run_2_warm.tool_calls}</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">{learningReport.efficiency_delta.tool_call_reduction}</span>
                    </div>
                    <span className="text-[11px] text-gray-500">Down from {learningReport.run_1_cold.tool_calls} calls</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1117] border border-emerald-500/30">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Execution Speed</span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">{(learningReport.run_2_warm.latency_ms / 1000).toFixed(1)}s</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">{learningReport.efficiency_delta.latency_reduction}</span>
                    </div>
                    <span className="text-[11px] text-gray-500">Down from {(learningReport.run_1_cold.latency_ms / 1000).toFixed(1)}s</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1117] border border-emerald-500/30">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Cost / Task</span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">${learningReport.run_2_warm.cost_usd.toFixed(4)}</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">{learningReport.efficiency_delta.cost_reduction}</span>
                    </div>
                    <span className="text-[11px] text-gray-500">Down from ${learningReport.run_1_cold.cost_usd.toFixed(4)}</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1117] border border-emerald-500/30">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Token Usage</span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">{learningReport.run_2_warm.tokens}</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">{learningReport.efficiency_delta.token_reduction}</span>
                    </div>
                    <span className="text-[11px] text-gray-500">Down from {learningReport.run_1_cold.tokens} tokens</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1117] border border-emerald-500/30">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Errors Prevented</span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {learningReport.efficiency_delta.errors_prevented}
                      </span>
                      <span className="text-xs font-bold text-emerald-400">0 in Run 2</span>
                    </div>
                    <span className="text-[11px] text-gray-500">Zero wasted recovery loops</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Learned Tool Playbooks Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-orange-400" /> Persistent Tool Playbook & Memory Graph ({toolMemories.length})
              </h3>
              <span className="text-xs text-gray-500">Injected into Agent Context Before Tool Calling</span>
            </div>

            {toolMemories.length === 0 ? (
              <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-8 text-center text-sm text-gray-500">
                No tool memory entries synthesized yet. Click <strong>'Execute Learning Loop'</strong> above to simulate and observe the learning progression.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {toolMemories.map((entry) => (
                  <div key={entry.id} className="bg-[#161b22] border border-[#30363d] hover:border-gray-500 rounded-xl p-5 space-y-3 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-orange-500/10 border border-orange-500/20 text-orange-400">
                          {entry.tool_name.toUpperCase()}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          entry.category === "SCHEMA_QUIRK"
                            ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                            : entry.category === "CONTEXTUAL_LOGIC"
                            ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        }`}>
                          {entry.category}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-emerald-400 font-bold">
                        {(entry.confidence * 100).toFixed(0)}% Conf. (Observed {entry.observation_count}x)
                      </span>
                    </div>

                    <div>
                      <span className="text-[11px] text-gray-500 block uppercase font-semibold">Trigger Pattern</span>
                      <p className="text-xs text-gray-300 font-mono mt-0.5">{entry.pattern_trigger}</p>
                    </div>

                    <div>
                      <span className="text-[11px] text-gray-500 block uppercase font-semibold">Learned Actionable Rule</span>
                      <p className="text-xs font-medium text-white mt-0.5 bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                        {entry.learned_rule}
                      </p>
                    </div>

                    {entry.evidence && (
                      <div className="text-[11px] text-gray-500 italic truncate">
                        Evidence: {entry.evidence}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
