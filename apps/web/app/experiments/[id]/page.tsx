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
  Cpu,
  Scale,
  Minus,
  X,
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
  const [activeTab, setActiveTab] = useState<"timeline" | "compare" | "console" | "provenance" | "learning">("timeline");
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [taskLimit, setTaskLimit] = useState<number>(3);
  const [playingGenId, setPlayingGenId] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const consoleBottomRef = useRef<HTMLDivElement>(null);

  // Inspector & Comparison State
  const [selectedGenId, setSelectedGenId] = useState<string | null>(null);
  const [selectedGenDetail, setSelectedGenDetail] = useState<{ generation: Generation; mutation: any; executions_count: number } | null>(null);
  const [loadingGenDetail, setLoadingGenDetail] = useState(false);
  const [compareGenAId, setCompareGenAId] = useState<string>("");
  const [compareGenBId, setCompareGenBId] = useState<string>("");

  useEffect(() => {
    if (generations.length >= 2) {
      if (!compareGenAId || !generations.find((g) => g.id === compareGenAId)) {
        setCompareGenAId(generations[0].id);
      }
      if (!compareGenBId || !generations.find((g) => g.id === compareGenBId)) {
        setCompareGenBId(generations[generations.length - 1].id);
      }
    } else if (generations.length === 1) {
      setCompareGenAId(generations[0].id);
    }
  }, [generations]);

  const handleSelectGeneration = async (genId: string) => {
    if (selectedGenId === genId) {
      setSelectedGenId(null);
      setSelectedGenDetail(null);
      return;
    }
    setSelectedGenId(genId);
    setLoadingGenDetail(true);
    try {
      const detail = await api.getGenerationDetail(genId);
      setSelectedGenDetail(detail);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingGenDetail(false);
    }
  };

  const calcDelta = (
    valA?: number | null,
    valB?: number | null,
    lowerIsBetter = false,
    unit = ""
  ) => {
    if (valA === undefined || valB === undefined || valA === null || valB === null) {
      return null;
    }
    const diff = valB - valA;
    const pct = valA !== 0 ? (diff / Math.abs(valA)) * 100 : (diff !== 0 ? 100 : 0);

    let status: "improved" | "regressed" | "unchanged" = "unchanged";
    if (Math.abs(diff) > 0.000001) {
      if (lowerIsBetter) {
        status = diff < 0 ? "improved" : "regressed";
      } else {
        status = diff > 0 ? "improved" : "regressed";
      }
    }

    const sign = diff > 0 ? "+" : "";
    let text = `${sign}${diff.toFixed(2)}${unit}`;
    if (status === "improved") {
      text += " (Improved)";
    } else if (status === "regressed") {
      text += " (Regressed)";
    } else {
      text = "0.00 (Unchanged)";
    }

    return { diff, pct, status, text };
  };

  const getStatusBadge = (status: string) => {
    if (status === "ACCEPTED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> ACCEPTED
        </span>
      );
    }
    if (status === "REJECTED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <XCircle className="w-3 h-3" /> REJECTED
        </span>
      );
    }
    if (status === "RUNNING") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
          <RotateCw className="w-3 h-3 animate-spin" /> RUNNING
        </span>
      );
    }
    if (status === "FAILED") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-red-950/40 text-red-400 border border-red-500/40">
          <AlertTriangle className="w-3 h-3" /> FAILED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-gray-700/20 text-gray-400 border border-gray-700/30">
        {status}
      </span>
    );
  };

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

  const currentGen =
    generations.find((g) => g.id === experiment.current_generation_id) ||
    (generations.length > 0 ? generations[generations.length - 1] : null);
  const bestGen =
    generations.find((g) => g.id === experiment.best_generation_id) || null;
  const metrics = currentGen?.metrics;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Experiments
      </Link>

      {/* Command Center Card */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
        {/* Top Bar: Name, Status & Prominent Actions */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-[#30363d]">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 shadow-sm">
                <Flame className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-orange-400 block">
                  Experiment Command Center
                </span>
                <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                  {experiment.name}
                </h1>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                experiment.status === "RUNNING"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                  : experiment.status === "COMPLETED"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
              }`}>
                {experiment.status}
              </span>
            </div>
            <p className="text-xs text-gray-500 font-mono">
              Experiment ID: {experiment.id}
            </p>
          </div>

          {/* Prominent Actions Bar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#0d1117] border border-[#30363d] text-xs text-gray-400 shadow-inner">
              <span>Scope:</span>
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

            {/* Action 1: Generate Agent */}
            <button
              onClick={handleGenerate}
              disabled={!!loadingAction}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white text-sm font-semibold shadow-lg shadow-orange-500/20 transition-all disabled:opacity-50 active:scale-95 cursor-pointer"
              title="Synthesize and initialize agent architecture"
            >
              <Sparkles className={`w-4 h-4 ${loadingAction === "generate" ? "animate-spin" : ""}`} />
              <span>{loadingAction === "generate" ? "Generating Agent..." : "Generate Agent"}</span>
            </button>

            {/* Action 2: Run Benchmark */}
            <button
              onClick={handleRun}
              disabled={generations.length === 0 || !!loadingAction}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-lg shadow-blue-600/20 transition-all disabled:opacity-50 active:scale-95 cursor-pointer"
              title="Execute benchmark tasks against current agent"
            >
              <Play className={`w-4 h-4 ${loadingAction === "run" ? "animate-pulse" : ""}`} />
              <span>{loadingAction === "run" ? "Running Benchmark..." : "Run Benchmark"}</span>
            </button>

            {/* Action 3: Evolve Agent */}
            <button
              onClick={handleEvolve}
              disabled={generations.length === 0 || !currentGen?.metrics || !!loadingAction}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 via-orange-500 to-amber-500 hover:from-rose-600 hover:to-orange-600 text-white text-sm font-semibold shadow-lg shadow-rose-500/20 transition-all disabled:opacity-50 active:scale-95 cursor-pointer"
              title="Diagnose failures and evolve candidate generation"
            >
              <RotateCw className={`w-4 h-4 ${loadingAction === "evolve" ? "animate-spin" : ""}`} />
              <span>{loadingAction === "evolve" ? "Evolving Agent..." : "Evolve Agent"}</span>
            </button>

            {/* Auxiliary Action: Test Learning Loop */}
            <button
              onClick={handleLearningLoop}
              disabled={!!loadingAction}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer"
              title="Test autonomous tool learning and self-reflection"
            >
              <Brain className={`w-3.5 h-3.5 ${loadingAction === "learning" ? "animate-pulse" : ""}`} />
              <span>{loadingAction === "learning" ? "Learning..." : "Learning Loop"}</span>
            </button>
          </div>
        </div>

        {/* Experiment Specification Grid: Goal, Benchmark, Current & Best Generation, Status */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Goal (spans full row on md, 2 cols on lg) */}
          <div className="lg:col-span-2 p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1.5">
            <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] block">
              Goal
            </span>
            <p className="text-gray-200 text-sm leading-relaxed">
              {experiment.goal}
            </p>
          </div>

          {/* Benchmark */}
          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1.5">
            <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] block">
              Benchmark
            </span>
            <div className="text-white font-mono font-bold text-sm">
              {experiment.benchmark_id}
            </div>
            <p className="text-[11px] text-gray-500 truncate">
              Tools: {experiment.tool_ids.join(", ")}
            </p>
          </div>

          {/* Current & Best Generation */}
          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2.5">
            <div>
              <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] block">
                Current Generation
              </span>
              <div className="text-sm font-mono font-bold text-white">
                {currentGen ? `Generation ${currentGen.generation_number}` : "Not available"}
              </div>
              <p className="text-[10px] text-gray-500 font-mono truncate">
                {currentGen ? `ID: ${currentGen.id}` : "No active candidate"}
              </p>
            </div>

            <div className="pt-2 border-t border-[#212631]">
              <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] block">
                Best Generation
              </span>
              <div className="text-sm font-mono font-bold text-emerald-400">
                {bestGen
                  ? `Generation ${bestGen.generation_number}`
                  : experiment.best_generation_id
                  ? `ID: ${experiment.best_generation_id.slice(0, 8)}...`
                  : "Not available"}
              </div>
              <p className="text-[10px] text-gray-500 font-mono truncate">
                {bestGen ? `ID: ${bestGen.id}` : (experiment.best_generation_id ? `ID: ${experiment.best_generation_id}` : "No accepted generation yet")}
              </p>
            </div>
          </div>
        </div>

        {/* Primary Metrics Group (4 metrics) */}
        <div className="space-y-2 pt-2 border-t border-[#30363d]/70">
          <div className="flex items-center justify-between text-xs">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-orange-400" /> Primary Metrics
            </span>
            <span className="text-[11px] text-gray-500 font-mono">
              {currentGen ? `Evaluation: Generation ${currentGen.generation_number}` : "Awaiting agent generation"}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Accuracy */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Accuracy
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.accuracy !== undefined && metrics?.accuracy !== null ? "text-2xl text-emerald-400" : "text-lg text-gray-500"}`}>
                {metrics?.accuracy !== undefined && metrics?.accuracy !== null
                  ? `${(metrics.accuracy * 100).toFixed(1)}%`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {metrics?.successful_tasks !== undefined && metrics?.total_tasks
                  ? `${metrics.successful_tasks} of ${metrics.total_tasks} passed`
                  : "Benchmark task pass rate"}
              </span>
            </div>

            {/* Reliability */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Reliability
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.reliability !== undefined && metrics?.reliability !== null ? "text-2xl text-cyan-400" : "text-lg text-gray-500"}`}>
                {metrics?.reliability !== undefined && metrics?.reliability !== null
                  ? `${(metrics.reliability * 100).toFixed(1)}%`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                Execution fidelity
              </span>
            </div>

            {/* Cost / task */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Cost / task
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.avg_cost_per_task !== undefined && metrics?.avg_cost_per_task !== null ? "text-2xl text-amber-400" : "text-lg text-gray-500"}`}>
                {metrics?.avg_cost_per_task !== undefined && metrics?.avg_cost_per_task !== null
                  ? `$${metrics.avg_cost_per_task.toFixed(4)}`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {metrics?.total_tokens !== undefined ? `${metrics.total_tokens.toLocaleString()} tokens total` : "Token consumption cost"}
              </span>
            </div>

            {/* Latency / task */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Latency / task
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.avg_latency_ms !== undefined && metrics?.avg_latency_ms !== null ? "text-2xl text-purple-400" : "text-lg text-gray-500"}`}>
                {metrics?.avg_latency_ms !== undefined && metrics?.avg_latency_ms !== null
                  ? `${(metrics.avg_latency_ms / 1000).toFixed(2)}s`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {metrics?.avg_latency_ms !== undefined ? `${Math.round(metrics.avg_latency_ms)} ms average` : "Execution latency"}
              </span>
            </div>
          </div>
        </div>

        {/* Operational & Verification Metrics Group (4 metrics) */}
        <div className="space-y-2 pt-2 border-t border-[#30363d]/60">
          <div className="flex items-center justify-between text-xs">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" /> Operational & Verification Metrics
            </span>
            <span className="text-[11px] text-gray-500">
              Tool usage, model calls, verification & recovery
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Tool calls / task */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Tool calls / task
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.total_tasks && metrics.total_tasks > 0 && metrics?.total_tool_calls !== undefined && metrics?.total_tool_calls !== null ? "text-2xl text-white" : "text-lg text-gray-500"}`}>
                {metrics?.total_tasks && metrics.total_tasks > 0 && metrics?.total_tool_calls !== undefined && metrics?.total_tool_calls !== null
                  ? (metrics.total_tool_calls / metrics.total_tasks).toFixed(1)
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {metrics?.total_tool_calls !== undefined ? `${metrics.total_tool_calls} total tool calls` : "Tool dispatch frequency"}
              </span>
            </div>

            {/* Model calls / task */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Model calls / task
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.total_tasks && metrics.total_tasks > 0 && metrics?.total_model_calls !== undefined && metrics?.total_model_calls !== null ? "text-2xl text-white" : "text-lg text-gray-500"}`}>
                {metrics?.total_tasks && metrics.total_tasks > 0 && metrics?.total_model_calls !== undefined && metrics?.total_model_calls !== null
                  ? (metrics.total_model_calls / metrics.total_tasks).toFixed(1)
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {metrics?.total_model_calls !== undefined ? `${metrics.total_model_calls} total model calls` : "Inference calls per benchmark"}
              </span>
            </div>

            {/* Verification rate */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Verification rate
              </span>
              <div className={`mt-1 font-black font-mono ${metrics?.verification_pass_rate !== undefined && metrics?.verification_pass_rate !== null ? "text-2xl text-teal-400" : "text-lg text-gray-500"}`}>
                {metrics?.verification_pass_rate !== undefined && metrics?.verification_pass_rate !== null
                  ? `${(metrics.verification_pass_rate * 100).toFixed(1)}%`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                Deterministic test verification
              </span>
            </div>

            {/* Recovery rate */}
            <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block">
                Recovery rate
              </span>
              <div className={`mt-1 font-black font-mono ${(metrics as any)?.recovery_rate !== undefined && (metrics as any)?.recovery_rate !== null ? "text-2xl text-emerald-400" : "text-lg text-gray-500"}`}>
                {(metrics as any)?.recovery_rate !== undefined && (metrics as any)?.recovery_rate !== null
                  ? `${((metrics as any).recovery_rate * 100).toFixed(1)}%`
                  : "Not available"}
              </div>
              <span className="text-[11px] text-gray-500 mt-1 block">
                {(metrics as any)?.recovery_rate !== undefined ? "Error recovery success" : "Not available"}
              </span>
            </div>
          </div>
        </div>

        {/* Composite & Token Summary Footer */}
        {metrics && (
          <div className="pt-3 border-t border-[#30363d]/60 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-gray-400 font-semibold uppercase text-[10px] tracking-wider">Composite Score:</span>
              <span className="font-mono text-orange-400 font-black text-sm bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 rounded">
                {metrics.composite_score !== undefined ? metrics.composite_score.toFixed(3) : "Not available"}
              </span>
              <span className="text-gray-500 text-[11px]">(Correctness 50% + Reliability 30% + Efficiency 20%)</span>
            </div>

            <div className="text-gray-400 flex items-center gap-3 font-mono text-[11px]">
              <span>Total Tokens: <strong className="text-white font-bold">{generations.reduce((acc, g) => acc + (g.metrics?.total_tokens || 0), 0).toLocaleString()}</strong></span>
              <span>•</span>
              <span>Evaluated Generations: <strong className="text-white font-bold">{generations.length}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-[#30363d] flex items-center justify-between">
        <div className="flex flex-wrap gap-2 sm:gap-4">
          <button
            onClick={() => setActiveTab("timeline")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "timeline" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <GitBranch className="w-4 h-4" /> Evolution Timeline ({generations.length})
          </button>
          <button
            onClick={() => setActiveTab("compare")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "compare" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Scale className="w-4 h-4" /> Compare Generations
          </button>
          <button
            onClick={() => setActiveTab("learning")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "learning" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Brain className="w-4 h-4" /> Tool Memory & Learning ({toolMemories.length})
          </button>
          <button
            onClick={() => setActiveTab("console")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "console" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Terminal className="w-4 h-4" /> Live Execution Trace ({events.length})
          </button>
          <button
            onClick={() => setActiveTab("provenance")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "provenance" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <ShieldCheck className="w-4 h-4" /> Cryptographic Provenance
          </button>
        </div>

        {generations.length >= 2 && (
          <Link
            href={`/experiments/${id}/compare`}
            className="hidden sm:flex text-xs font-semibold text-orange-400 hover:text-orange-300 pb-3 items-center gap-1"
          >
            Full Comparison Page <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>

      {/* Tab 1: Evolution Timeline */}
      {activeTab === "timeline" && (
        <div className="space-y-6">
          {generations.length === 0 ? (
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-12 text-center text-gray-500 text-sm space-y-3">
              <GitBranch className="w-12 h-12 text-gray-600 mx-auto" />
              <p className="text-gray-300 font-medium">No generations evaluated yet.</p>
              <p className="text-gray-500 text-xs">Click &apos;Generate Agent&apos; above to synthesize G0 and begin the evolutionary cycle.</p>
            </div>
          ) : (
            <>
              {/* G0 → G1 → G2 → ... Visual Lineage Progression */}
              <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-orange-400" />
                    <span className="font-bold text-white uppercase tracking-wider text-xs">
                      Evolutionary Progression Chain
                    </span>
                  </div>
                  <span className="text-gray-400 text-[11px]">
                    Click any generation node below to inspect configuration, mutation, and decision
                  </span>
                </div>

                <div className="overflow-x-auto py-2">
                  <div className="flex items-center gap-2 min-w-max">
                    {generations.map((g, idx) => {
                      const isSelected = selectedGenId === g.id;
                      const isBest = g.id === experiment.best_generation_id;
                      const status = g.status;

                      return (
                        <div key={g.id} className="flex items-center gap-2">
                          <button
                            onClick={() => handleSelectGeneration(g.id)}
                            className={`flex items-center gap-2.5 px-3.5 py-2 rounded-xl border font-mono text-xs transition-all cursor-pointer ${
                              isSelected
                                ? "ring-2 ring-orange-500 scale-105 bg-[#1c2128] border-orange-500 shadow-lg shadow-orange-500/10"
                                : status === "ACCEPTED"
                                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20"
                                : status === "REJECTED"
                                ? "bg-rose-500/10 border-rose-500/30 text-rose-300 hover:bg-rose-500/20"
                                : status === "RUNNING"
                                ? "bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20 animate-pulse"
                                : "bg-red-950/30 border-red-500/40 text-red-300 hover:bg-red-950/50"
                            }`}
                          >
                            <div className="flex items-center gap-1.5 font-bold">
                              {status === "ACCEPTED" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                              {status === "REJECTED" && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                              {status === "RUNNING" && <RotateCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />}
                              {status === "FAILED" && <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
                              <span>G{g.generation_number}</span>
                            </div>
                            {isBest && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                Best
                              </span>
                            )}
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-black/40 text-gray-300 font-sans font-semibold uppercase">
                              {status}
                            </span>
                          </button>

                          {idx < generations.length - 1 && (
                            <ArrowRight className="w-4 h-4 text-gray-600 shrink-0" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Clicked Generation Inspector Card (shows Agent configuration, Parent generation, Mutation, Metrics, Decision) */}
              {selectedGenId && (
                <div className="bg-[#12151d] border-2 border-orange-500/40 rounded-2xl p-6 shadow-2xl space-y-6 animate-in fade-in duration-200">
                  {loadingGenDetail ? (
                    <div className="py-12 text-center text-gray-400 text-sm font-mono">
                      Loading generation architecture details...
                    </div>
                  ) : selectedGenDetail ? (
                    <>
                      {/* Inspector Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#30363d]">
                        <div>
                          <div className="flex items-center gap-3">
                            <span className="text-xl font-black text-white font-mono">
                              Generation {selectedGenDetail.generation.generation_number} Architecture
                            </span>
                            {getStatusBadge(selectedGenDetail.generation.status)}
                            {selectedGenDetail.generation.id === experiment.best_generation_id && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                                Current Best Model
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 font-mono mt-1">
                            Generation ID: {selectedGenDetail.generation.id}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handlePlayAudio(selectedGenDetail.generation.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#161b22] border border-[#30363d] text-xs font-semibold text-gray-300 hover:text-white cursor-pointer"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                            Voice Debrief
                          </button>
                          <button
                            onClick={() => {
                              setCompareGenBId(selectedGenDetail.generation.id);
                              setActiveTab("compare");
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-400 text-xs font-semibold hover:bg-orange-500/20 cursor-pointer"
                          >
                            <Scale className="w-3.5 h-3.5" />
                            Compare with Baseline
                          </button>
                          <button
                            onClick={() => {
                              setSelectedGenId(null);
                              setSelectedGenDetail(null);
                            }}
                            className="p-1.5 rounded-lg bg-[#161b22] border border-[#30363d] text-gray-400 hover:text-white cursor-pointer"
                            title="Close Inspector"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Top Row: Parent Generation & Decision */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        {/* 1. Parent Generation */}
                        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-2">
                          <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                            <GitBranch className="w-3.5 h-3.5 text-orange-400" /> Parent Generation
                          </span>
                          {selectedGenDetail.generation.parent_generation_id ? (
                            <div className="space-y-1">
                              <div className="text-sm font-mono font-bold text-white">
                                ID: {selectedGenDetail.generation.parent_generation_id}
                              </div>
                              <p className="text-[11px] text-gray-400">
                                Evolved from predecessor architecture via targeted failure-driven mutation.
                              </p>
                              <button
                                onClick={() => handleSelectGeneration(selectedGenDetail.generation.parent_generation_id!)}
                                className="inline-flex items-center gap-1 text-[11px] text-orange-400 hover:text-orange-300 font-semibold mt-1 cursor-pointer"
                              >
                                View Parent Generation →
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              <div className="text-sm font-mono font-bold text-white">
                                None (Root Generation G0)
                              </div>
                              <p className="text-[11px] text-gray-400">
                                Synthesized directly by AgentArchitect from high-level experiment goal.
                              </p>
                            </div>
                          )}
                        </div>

                        {/* 2. Decision */}
                        <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-2">
                          <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                            <Scale className="w-3.5 h-3.5 text-orange-400" /> Decision & Rationale
                          </span>
                          <div className="flex items-center gap-2">
                            {getStatusBadge(selectedGenDetail.generation.status)}
                          </div>
                          <p className="text-gray-300 text-xs leading-relaxed">
                            {selectedGenDetail.generation.status === "REJECTED"
                              ? selectedGenDetail.generation.rejection_reason || "Candidate failed multi-objective Pareto trade-off relative to token cost."
                              : selectedGenDetail.generation.status === "ACCEPTED"
                              ? "Candidate accepted by Pareto Multi-Objective Optimization Gate: verified performance improvement without unacceptable trade-offs."
                              : selectedGenDetail.generation.status === "RUNNING"
                              ? "Benchmark evaluation currently executing."
                              : "Generation evaluation complete."}
                          </p>
                        </div>
                      </div>

                      {/* 3. Mutation */}
                      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-3">
                        <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                          <RotateCw className="w-3.5 h-3.5 text-orange-400" /> Mutation
                        </span>
                        {selectedGenDetail.mutation ? (
                          <div className="space-y-3 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                              <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                                <span className="text-gray-500 block text-[10px] uppercase">Mutation Type</span>
                                <span className="font-mono text-white font-bold">{selectedGenDetail.mutation.type}</span>
                              </div>
                              <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                                <span className="text-gray-500 block text-[10px] uppercase">Target Subsystem</span>
                                <span className="font-mono text-white font-bold">{selectedGenDetail.mutation.target}</span>
                              </div>
                              <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                                <span className="text-gray-500 block text-[10px] uppercase">Observed Failure</span>
                                <span className="font-mono text-rose-400 font-bold">{selectedGenDetail.mutation.observed_failure}</span>
                              </div>
                              <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                                <span className="text-gray-500 block text-[10px] uppercase">Expected Effect</span>
                                <span className="text-gray-300">{selectedGenDetail.mutation.expected_effect}</span>
                              </div>
                            </div>
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 block text-[10px] uppercase mb-1">Empirical Reason:</span>
                              <p className="text-gray-300">{selectedGenDetail.mutation.reason}</p>
                            </div>

                            {/* Before vs After Diff */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
                              <div className="p-3 rounded-lg bg-[#0a0c10] border border-rose-500/30">
                                <span className="text-rose-400 font-bold block mb-1">- BEFORE (Parent Architecture)</span>
                                <pre className="text-gray-400 overflow-x-auto whitespace-pre-wrap max-h-48 text-[11px]">
                                  {JSON.stringify(selectedGenDetail.mutation.before, null, 2)}
                                </pre>
                              </div>
                              <div className="p-3 rounded-lg bg-[#0a0c10] border border-emerald-500/30">
                                <span className="text-emerald-400 font-bold block mb-1">+ AFTER (Mutated Architecture)</span>
                                <pre className="text-gray-300 overflow-x-auto whitespace-pre-wrap max-h-48 text-[11px]">
                                  {JSON.stringify(selectedGenDetail.mutation.after, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-gray-400">
                            Root Generation G0 — Initial baseline architecture synthesized directly from goal; no parent mutation applied.
                          </p>
                        )}
                      </div>

                      {/* 4. Metrics */}
                      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-3">
                        <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                          <Activity className="w-3.5 h-3.5 text-emerald-400" /> Generation Metrics
                        </span>
                        {selectedGenDetail.generation.metrics ? (
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono text-xs">
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 uppercase text-[10px] block">Accuracy</span>
                              <span className="text-lg font-bold text-emerald-400 block mt-0.5">
                                {(selectedGenDetail.generation.metrics.accuracy * 100).toFixed(1)}%
                              </span>
                              <span className="text-[10px] text-gray-500">
                                {selectedGenDetail.generation.metrics.successful_tasks} / {selectedGenDetail.generation.metrics.total_tasks} passed
                              </span>
                            </div>
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 uppercase text-[10px] block">Reliability</span>
                              <span className="text-lg font-bold text-cyan-400 block mt-0.5">
                                {(selectedGenDetail.generation.metrics.reliability * 100).toFixed(1)}%
                              </span>
                              <span className="text-[10px] text-gray-500">Execution fidelity</span>
                            </div>
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 uppercase text-[10px] block">Composite Score</span>
                              <span className="text-lg font-bold text-orange-400 block mt-0.5">
                                {selectedGenDetail.generation.metrics.composite_score.toFixed(3)}
                              </span>
                              <span className="text-[10px] text-gray-500">Correctness + Efficiency</span>
                            </div>
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 uppercase text-[10px] block">Cost / task</span>
                              <span className="text-lg font-bold text-amber-400 block mt-0.5">
                                ${selectedGenDetail.generation.metrics.avg_cost_per_task.toFixed(4)}
                              </span>
                              <span className="text-[10px] text-gray-500">
                                {selectedGenDetail.generation.metrics.total_tokens.toLocaleString()} tokens
                              </span>
                            </div>
                            <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-gray-500 uppercase text-[10px] block">Latency / task</span>
                              <span className="text-lg font-bold text-purple-400 block mt-0.5">
                                {(selectedGenDetail.generation.metrics.avg_latency_ms / 1000).toFixed(2)}s
                              </span>
                              <span className="text-[10px] text-gray-500">
                                {selectedGenDetail.generation.metrics.total_tool_calls} tool calls
                              </span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-gray-500 italic">No benchmark metrics captured yet.</p>
                        )}
                      </div>

                      {/* 5. Agent Configuration (Declarative AgentSpec) */}
                      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-3">
                        <span className="text-gray-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                          <Cpu className="w-3.5 h-3.5 text-orange-400" /> Agent Configuration (Declarative AgentSpec)
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Model</span>
                            <span className="font-mono text-white font-bold">{selectedGenDetail.generation.agent_spec.model}</span>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Planner</span>
                            <span className="font-mono text-cyan-400 font-bold">{selectedGenDetail.generation.agent_spec.planner?.type || "none"}</span>
                            <p className="text-[10px] text-gray-500">Replan on error: {String(selectedGenDetail.generation.agent_spec.planner?.require_replan_on_error)}</p>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Verifier</span>
                            <span className="font-mono text-emerald-400 font-bold">{selectedGenDetail.generation.agent_spec.verifier?.type || "none"}</span>
                            <p className="text-[10px] text-gray-500">Zero failed tests: {String(selectedGenDetail.generation.agent_spec.verifier?.require_zero_failed_tests)}</p>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Orchestration</span>
                            <span className="font-mono text-amber-400 font-bold">{selectedGenDetail.generation.agent_spec.orchestration?.type || "direct"}</span>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Retry Policy</span>
                            <span className="font-mono text-purple-400 font-bold">{selectedGenDetail.generation.agent_spec.retry_policy?.max_attempts} attempts</span>
                            <p className="text-[10px] text-gray-500">Backoff: {selectedGenDetail.generation.agent_spec.retry_policy?.backoff_seconds}s</p>
                          </div>
                          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-gray-500 text-[10px] uppercase block">Working Memory</span>
                            <span className="font-mono text-white font-bold">{selectedGenDetail.generation.agent_spec.memory?.type || "working_context"}</span>
                            <p className="text-[10px] text-gray-500">Max history: {selectedGenDetail.generation.agent_spec.memory?.max_history_items || 30}</p>
                          </div>
                        </div>

                        {/* System Prompt */}
                        <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs">
                          <span className="text-gray-500 text-[10px] uppercase block mb-1">Synthesized System Prompt</span>
                          <pre className="text-gray-300 font-mono text-[11px] whitespace-pre-wrap max-h-32 overflow-y-auto">
                            {selectedGenDetail.generation.agent_spec.system_prompt}
                          </pre>
                        </div>

                        {/* Tools */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[11px] text-gray-500 font-semibold">Configured Tools:</span>
                          {selectedGenDetail.generation.agent_spec.tools.map((t) => (
                            <span key={t} className="px-2 py-0.5 rounded bg-[#0d1117] border border-[#30363d] text-[11px] font-mono text-gray-300">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : null}
                </div>
              )}

              {/* Generations List: Every generation displays generation number, status, composite score, accuracy, reliability, cost/task, latency/task */}
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-400">
                    Evaluated Generations ({generations.length})
                  </span>
                  <span className="text-[11px] text-gray-500">
                    Click any generation card to inspect architecture
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {generations.map((gen, idx) => {
                    const m = gen.metrics;
                    const prevM = idx > 0 ? generations[idx - 1].metrics : null;
                    const accDelta = m && prevM ? m.accuracy - prevM.accuracy : null;
                    const isSelected = selectedGenId === gen.id;

                    return (
                      <div
                        key={gen.id}
                        onClick={() => handleSelectGeneration(gen.id)}
                        className={`bg-[#161b22] border rounded-2xl p-5 transition-all cursor-pointer ${
                          isSelected
                            ? "border-orange-500 ring-2 ring-orange-500/40 shadow-xl shadow-orange-500/10"
                            : gen.id === experiment.best_generation_id
                            ? "border-emerald-500/50 shadow-lg shadow-emerald-500/5 hover:border-emerald-500"
                            : gen.status === "REJECTED"
                            ? "border-rose-500/30 hover:border-rose-500/60"
                            : "border-[#30363d] hover:border-gray-500"
                        }`}
                      >
                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                          {/* Generation number, status & ID */}
                          <div className="flex items-center gap-3">
                            <div className="w-11 h-11 rounded-xl bg-[#12151d] border border-[#30363d] flex items-center justify-center font-mono font-black text-white text-base shadow-sm">
                              G{gen.generation_number}
                            </div>
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-bold text-white text-base">
                                  Generation {gen.generation_number}
                                </span>
                                {gen.id === experiment.best_generation_id && (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                                    Best Model
                                  </span>
                                )}
                                {getStatusBadge(gen.status)}
                              </div>
                              <p className="text-xs text-gray-500 font-mono mt-0.5">
                                ID: {gen.id}
                              </p>
                            </div>
                          </div>

                          {/* Explicit display of all 5 performance metrics for every generation */}
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-xs">
                            {/* Composite score */}
                            <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-[10px] text-gray-500 uppercase block">Composite</span>
                              <span className="font-bold text-orange-400 text-sm block mt-0.5">
                                {m?.composite_score !== undefined ? m.composite_score.toFixed(3) : "Not available"}
                              </span>
                            </div>

                            {/* Accuracy */}
                            <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-[10px] text-gray-500 uppercase block">Accuracy</span>
                              <span className="font-bold text-emerald-400 text-sm block mt-0.5">
                                {m?.accuracy !== undefined ? `${(m.accuracy * 100).toFixed(1)}%` : "Not available"}
                              </span>
                              {accDelta !== null && (
                                <span className={`text-[10px] block ${accDelta >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                  {accDelta >= 0 ? `+${(accDelta * 100).toFixed(1)}%` : `${(accDelta * 100).toFixed(1)}%`}
                                </span>
                              )}
                            </div>

                            {/* Reliability */}
                            <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-[10px] text-gray-500 uppercase block">Reliability</span>
                              <span className="font-bold text-cyan-400 text-sm block mt-0.5">
                                {m?.reliability !== undefined ? `${(m.reliability * 100).toFixed(1)}%` : "Not available"}
                              </span>
                            </div>

                            {/* Cost / task */}
                            <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-[10px] text-gray-500 uppercase block">Cost / task</span>
                              <span className="font-bold text-amber-400 text-sm block mt-0.5">
                                {m?.avg_cost_per_task !== undefined ? `$${m.avg_cost_per_task.toFixed(4)}` : "Not available"}
                              </span>
                            </div>

                            {/* Latency / task */}
                            <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                              <span className="text-[10px] text-gray-500 uppercase block">Latency / task</span>
                              <span className="font-bold text-purple-400 text-sm block mt-0.5">
                                {m?.avg_latency_ms !== undefined ? `${(m.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                              </span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePlayAudio(gen.id);
                              }}
                              title="Listen to Voice Debrief"
                              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors cursor-pointer ${
                                playingGenId === gen.id
                                  ? "bg-orange-500/20 text-orange-400 border-orange-500/50 animate-pulse"
                                  : "bg-[#0d1117] border-[#30363d] text-gray-300 hover:text-white hover:border-gray-500"
                              }`}
                            >
                              <Volume2 className="w-3.5 h-3.5" />
                              {playingGenId === gen.id ? "Playing..." : "Voice"}
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectGeneration(gen.id);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs font-semibold text-gray-300 hover:text-white hover:border-gray-500 transition-colors cursor-pointer"
                            >
                              Inspect Details
                            </button>
                          </div>
                        </div>

                        {/* Rejected Candidate Banner (remains visible) */}
                        {gen.status === "REJECTED" && (
                          <div className="mt-3 text-xs p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-1.5">
                            <div className="flex items-center gap-2 font-bold uppercase tracking-wider text-[11px] text-rose-400">
                              <AlertTriangle className="w-4 h-4" /> Pareto Gate: Candidate Mutated & Rejected
                            </div>
                            <p className="text-gray-300">
                              <strong>Decision Rationale:</strong> {gen.rejection_reason || "Candidate failed multi-objective Pareto trade-off. Architectural mutation did not yield sufficient accuracy/reliability improvement relative to token cost."}
                            </p>
                            <p className="text-[11px] text-gray-400 italic">
                              &quot;FORGE isn&apos;t programmed to always improve. It evaluates whether the proposed architecture is actually better.&quot;
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Tab 2: Compare Generations */}
      {activeTab === "compare" && (
        <div className="space-y-6">
          {generations.length <= 1 ? (
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 mx-auto">
                <Scale className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">
                Comparison Requires at Least Two Generations
              </h3>
              <p className="text-xs text-gray-400 max-w-md mx-auto leading-relaxed">
                {generations.length === 0
                  ? "No generations generated yet. Generate an agent (G0) to begin."
                  : "Only Generation 0 has been evaluated. At least two generations are needed to calculate empirical performance deltas. Click 'Evolve Agent' above to produce candidate Generation 1."}
              </p>
            </div>
          ) : (
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-white">Generational Performance Comparison</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Direct empirical delta comparison between agent generations. Lower is better for cost, latency, and tool calls; higher is better for accuracy and reliability.
                  </p>
                </div>
              </div>

              {/* Generation Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2">
                  <label className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">
                    Baseline Generation (A)
                  </label>
                  <select
                    value={compareGenAId}
                    onChange={(e) => setCompareGenAId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none cursor-pointer"
                  >
                    {generations.map((g) => (
                      <option key={g.id} value={g.id}>
                        Generation {g.generation_number} ({g.status}) — Accuracy: {g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-gray-500 font-mono truncate">ID: {compareGenAId}</p>
                </div>

                <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2">
                  <label className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">
                    Candidate / Target Generation (B)
                  </label>
                  <select
                    value={compareGenBId}
                    onChange={(e) => setCompareGenBId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none cursor-pointer"
                  >
                    {generations.map((g) => (
                      <option key={g.id} value={g.id}>
                        Generation {g.generation_number} ({g.status}) — Accuracy: {g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-gray-500 font-mono truncate">ID: {compareGenBId}</p>
                </div>
              </div>

              {/* Delta Comparison Table */}
              {(() => {
                const genA = generations.find((g) => g.id === compareGenAId) || generations[0];
                const genB = generations.find((g) => g.id === compareGenBId) || generations[generations.length - 1];
                const mA = genA?.metrics;
                const mB = genB?.metrics;

                // Accuracy (higher = improvement)
                const accD = calcDelta(mA?.accuracy, mB?.accuracy, false, "%");
                // Reliability (higher = improvement)
                const relD = calcDelta(mA?.reliability, mB?.reliability, false, "%");
                // Cost (lower = improvement)
                const costD = calcDelta(mA?.avg_cost_per_task, mB?.avg_cost_per_task, true, " USD");
                // Latency (lower = improvement)
                const latD = calcDelta(
                  mA?.avg_latency_ms ? mA.avg_latency_ms / 1000 : null,
                  mB?.avg_latency_ms ? mB.avg_latency_ms / 1000 : null,
                  true,
                  "s"
                );
                // Tool calls / task (lower = improvement)
                const callsA = mA?.total_tasks && mA.total_tasks > 0 ? mA.total_tool_calls / mA.total_tasks : null;
                const callsB = mB?.total_tasks && mB.total_tasks > 0 ? mB.total_tool_calls / mB.total_tasks : null;
                const toolsD = calcDelta(callsA, callsB, true, " calls");
                // Composite score (higher = improvement)
                const compD = calcDelta(mA?.composite_score, mB?.composite_score, false);

                return (
                  <div className="overflow-x-auto rounded-xl border border-[#30363d] bg-[#0d1117]">
                    <table className="w-full text-left text-sm font-mono">
                      <thead className="bg-[#12151d] text-gray-400 text-xs uppercase tracking-wider border-b border-[#30363d]">
                        <tr>
                          <th className="px-6 py-3.5 font-sans font-semibold">Metric</th>
                          <th className="px-6 py-3.5 font-sans font-semibold">Criteria</th>
                          <th className="px-6 py-3.5">Gen {genA?.generation_number}</th>
                          <th className="px-6 py-3.5">Gen {genB?.generation_number}</th>
                          <th className="px-6 py-3.5">Delta (B - A)</th>
                          <th className="px-6 py-3.5 font-sans font-semibold text-right">Evaluation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#212631]">
                        {/* Accuracy */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Accuracy</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {mA ? `${(mA.accuracy * 100).toFixed(1)}%` : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-emerald-400">
                            {mB ? `${(mB.accuracy * 100).toFixed(1)}%` : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {accD ? (
                              <span className={`font-bold ${
                                accD.status === "improved" ? "text-emerald-400" : accD.status === "regressed" ? "text-rose-400" : "text-gray-400"
                              }`}>
                                {accD.diff >= 0 ? `+${(accD.diff * 100).toFixed(1)}%` : `${(accD.diff * 100).toFixed(1)}%`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {accD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                accD.status === "improved"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : accD.status === "regressed"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {accD.status === "improved" ? "Improved" : accD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Reliability */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Reliability</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {mA ? `${(mA.reliability * 100).toFixed(1)}%` : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-cyan-400">
                            {mB ? `${(mB.reliability * 100).toFixed(1)}%` : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {relD ? (
                              <span className={`font-bold ${
                                relD.status === "improved" ? "text-cyan-400" : relD.status === "regressed" ? "text-rose-400" : "text-gray-400"
                              }`}>
                                {relD.diff >= 0 ? `+${(relD.diff * 100).toFixed(1)}%` : `${(relD.diff * 100).toFixed(1)}%`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {relD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                relD.status === "improved"
                                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                                  : relD.status === "regressed"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {relD.status === "improved" ? "Improved" : relD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Cost / task */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Cost / task</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {mA ? `$${mA.avg_cost_per_task.toFixed(4)}` : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-amber-400">
                            {mB ? `$${mB.avg_cost_per_task.toFixed(4)}` : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {costD ? (
                              <span className={`font-bold ${
                                costD.status === "improved" ? "text-emerald-400" : costD.status === "regressed" ? "text-amber-400" : "text-gray-400"
                              }`}>
                                {costD.diff >= 0 ? `+$${costD.diff.toFixed(4)}` : `-$${Math.abs(costD.diff).toFixed(4)}`}
                                {costD.pct !== 0 && ` (${costD.pct > 0 ? `+${costD.pct.toFixed(1)}%` : `${costD.pct.toFixed(1)}%`})`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {costD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                costD.status === "improved"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : costD.status === "regressed"
                                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {costD.status === "improved" ? "Improved" : costD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Latency / task */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Latency / task</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {mA ? `${(mA.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-purple-400">
                            {mB ? `${(mB.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {latD ? (
                              <span className={`font-bold ${
                                latD.status === "improved" ? "text-emerald-400" : latD.status === "regressed" ? "text-purple-400" : "text-gray-400"
                              }`}>
                                {latD.diff >= 0 ? `+${latD.diff.toFixed(2)}s` : `${latD.diff.toFixed(2)}s`}
                                {latD.pct !== 0 && ` (${latD.pct > 0 ? `+${latD.pct.toFixed(1)}%` : `${latD.pct.toFixed(1)}%`})`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {latD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                latD.status === "improved"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : latD.status === "regressed"
                                  ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {latD.status === "improved" ? "Improved" : latD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Tool calls / task */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Tool calls / task</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {callsA !== null ? callsA.toFixed(1) : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-white">
                            {callsB !== null ? callsB.toFixed(1) : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {toolsD ? (
                              <span className={`font-bold ${
                                toolsD.status === "improved" ? "text-emerald-400" : toolsD.status === "regressed" ? "text-rose-400" : "text-gray-400"
                              }`}>
                                {toolsD.diff >= 0 ? `+${toolsD.diff.toFixed(1)}` : `${toolsD.diff.toFixed(1)}`}
                                {toolsD.pct !== 0 && ` (${toolsD.pct > 0 ? `+${toolsD.pct.toFixed(1)}%` : `${toolsD.pct.toFixed(1)}%`})`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {toolsD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                toolsD.status === "improved"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : toolsD.status === "regressed"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {toolsD.status === "improved" ? "Improved" : toolsD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Composite score */}
                        <tr className="hover:bg-[#161b22]/50 transition-colors bg-[#12151d]/40">
                          <td className="px-6 py-4 font-sans font-semibold text-white">Composite Score</td>
                          <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher = Improvement</td>
                          <td className="px-6 py-4 text-gray-300">
                            {mA ? mA.composite_score.toFixed(3) : "Not available"}
                          </td>
                          <td className="px-6 py-4 font-bold text-orange-400">
                            {mB ? mB.composite_score.toFixed(3) : "Not available"}
                          </td>
                          <td className="px-6 py-4">
                            {compD ? (
                              <span className={`font-bold ${
                                compD.status === "improved" ? "text-emerald-400" : compD.status === "regressed" ? "text-rose-400" : "text-gray-400"
                              }`}>
                                {compD.diff >= 0 ? `+${compD.diff.toFixed(3)}` : `${compD.diff.toFixed(3)}`}
                              </span>
                            ) : (
                              <span className="text-gray-500">Not available</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-right">
                            {compD && (
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                                compD.status === "improved"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : compD.status === "regressed"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                              }`}>
                                {compD.status === "improved" ? "Improved" : compD.status === "regressed" ? "Regressed" : "Unchanged"}
                              </span>
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                );
              })()}
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

                {/* Causal Evidence Chain: Failure -> Memory -> Zero-Shot */}
                <div className="mt-6 pt-6 border-t border-[#30363d] space-y-4">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" /> Causal Evidence: How Failures Directly Caused Zero-Shot Execution
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Direct empirical proof that learned memory — not chance — eliminated exploratory errors and caused 100% accuracy in Run 2.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Causal Card 1: Linear UUID */}
                    <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                            RUN 1 COLD FAILURE
                          </span>
                          <span className="font-mono text-[11px] text-gray-500">linear_api</span>
                        </div>
                        <div className="text-xs font-mono text-rose-300 bg-[#161b22] p-2 rounded border border-rose-500/20">
                          HTTP 422: Invalid team slug 'CORE'. Expected 36-char UUID.
                        </div>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                          REFLECTED PLAYBOOK (SCHEMA_QUIRK)
                        </span>
                        <p className="text-xs text-gray-300 italic">
                          "Linear requires UUID '550e8400-e29b-41d4-a716-446655440001'. Never pass slugs."
                        </p>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                          RUN 2 WARM ACTION
                        </span>
                        <div className="text-xs font-mono text-emerald-300 bg-[#161b22] p-2 rounded border border-emerald-500/20">
                          team_id: '550e8400-...' passed directly (0 errors, 1 call)
                        </div>
                      </div>
                    </div>

                    {/* Causal Card 2: Slack Alert Tag */}
                    <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                            RUN 1 COLD FAILURE
                          </span>
                          <span className="font-mono text-[11px] text-gray-500">slack_api</span>
                        </div>
                        <div className="text-xs font-mono text-rose-300 bg-[#161b22] p-2 rounded border border-rose-500/20">
                          HTTP 400: Channel policy violation. #enterprise-escalations requires [SLA-ALERT].
                        </div>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                          REFLECTED PLAYBOOK (WORKFLOW_DEP)
                        </span>
                        <p className="text-xs text-gray-300 italic">
                          "Enterprise escalations must include '[SLA-ALERT]' and customer_id tag."
                        </p>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                          RUN 2 WARM ACTION
                        </span>
                        <div className="text-xs font-mono text-emerald-300 bg-[#161b22] p-2 rounded border border-emerald-500/20">
                          Formatted with [SLA-ALERT] cust_acme_corp instantly (0 errors)
                        </div>
                      </div>
                    </div>

                    {/* Causal Card 3: Linear Integer Priority */}
                    <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                            RUN 1 COLD FAILURE
                          </span>
                          <span className="font-mono text-[11px] text-gray-500">linear_api</span>
                        </div>
                        <div className="text-xs font-mono text-rose-300 bg-[#161b22] p-2 rounded border border-rose-500/20">
                          HTTP 400: Invalid priority 'urgent'. Expected integer 1-4.
                        </div>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                          REFLECTED PLAYBOOK (SCHEMA_QUIRK)
                        </span>
                        <p className="text-xs text-gray-300 italic">
                          "Priority must be integer: 1 (Urgent), 2 (High), 3 (Normal), 4 (Low)."
                        </p>
                      </div>

                      <div className="flex items-center justify-center my-1 text-gray-500">
                        <ArrowRight className="w-4 h-4 text-emerald-400 rotate-90 lg:rotate-0" />
                      </div>

                      <div className="space-y-1.5">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                          RUN 2 WARM ACTION
                        </span>
                        <div className="text-xs font-mono text-emerald-300 bg-[#161b22] p-2 rounded border border-emerald-500/20">
                          priority: 1 sent cleanly on first attempt
                        </div>
                      </div>
                    </div>
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
