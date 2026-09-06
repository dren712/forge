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
  EvidenceResponse,
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
  ArrowDown,
  Lightbulb,
  Database,
  Dna,
  Volume2,
  Brain,
  Zap,
  BookOpen,
  Cpu,
  Scale,
  Minus,
  X,
  Radio,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Check,
  Filter,
  Copy,
  Search,
  Lock,
  Link2,
  Eye,
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

  // Causal Evidence State (S8-D)
  const [evidenceData, setEvidenceData] = useState<EvidenceResponse | null>(null);
  const [selectedEvidenceGenId, setSelectedEvidenceGenId] = useState<string | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState<boolean>(false);
  const [causalViewMode, setCausalViewMode] = useState<"featured" | "experiment">("featured");

  // Live Execution Console State (FORGE S8-E)
  const [sseStatus, setSseStatus] = useState<"connecting" | "connected" | "disconnected" | "completed" | "failed">("connecting");
  const [sseError, setSseError] = useState<string | null>(null);
  const [sseReconnectCount, setSseReconnectCount] = useState<number>(0);
  const [consoleFilter, setConsoleFilter] = useState<"all" | "tools" | "model" | "errors" | "verify">("all");
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  // Provenance Inspector State (FORGE S8-F)
  const [selectedProvenanceEventId, setSelectedProvenanceEventId] = useState<string | null>(null);
  const [verifyingProvenance, setVerifyingProvenance] = useState<boolean>(false);
  const [provenanceSearchQuery, setProvenanceSearchQuery] = useState<string>("");
  const [copiedProvenanceText, setCopiedProvenanceText] = useState<string | null>(null);

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

  const formatEventTime = (timestamp: string) => {
    try {
      const d = new Date(timestamp);
      if (isNaN(d.getTime())) return "--:--:--";
      return d.toLocaleTimeString("en-GB", { hour12: false });
    } catch {
      return "--:--:--";
    }
  };

  interface EventDescriptor {
    title: string;
    category: "agent" | "model" | "tool" | "result" | "verify" | "recovery" | "mutation" | "system";
    toolOrModel?: string;
    statusCode?: number;
    isSuccess?: boolean | null;
    latencyMs?: number;
    summary?: string;
  }

  const getEventDescriptor = (ev: TraceEvent): EventDescriptor => {
    const p = ev.payload || {};
    const t = ev.type;

    switch (t) {
      case "AGENT_STARTED":
        return {
          title: p.phase ? `Agent started (${p.phase})` : "Agent started",
          category: "agent",
          toolOrModel: p.agent_model || p.model,
          isSuccess: true,
          summary: p.goal || p.task_id || undefined,
        };

      case "MODEL_CALL":
        return {
          title: "Model call",
          category: "model",
          toolOrModel: p.model,
          summary: p.step ? `Step ${p.step} (${p.messages_count || 0} messages)` : undefined,
        };

      case "MODEL_RESPONSE":
        return {
          title: "Model response",
          category: "model",
          toolOrModel: p.model,
          isSuccess: true,
          latencyMs: p.latency_ms,
          summary: p.tokens ? `${p.tokens} tokens` : (p.content_preview ? p.content_preview.slice(0, 80) : undefined),
        };

      case "TOOL_CALL":
        return {
          title: `Tool: ${p.tool || "unknown"}`,
          category: "tool",
          toolOrModel: p.tool,
          summary: p.arguments
            ? (typeof p.arguments === "string" ? p.arguments.slice(0, 70) : JSON.stringify(p.arguments).slice(0, 70))
            : undefined,
        };

      case "TOOL_RESULT": {
        const isSuccess = p.success !== false && (!p.status_code || p.status_code < 400);
        const code = p.status_code !== undefined ? p.status_code : (isSuccess ? 200 : (p.error_type ? 500 : undefined));
        return {
          title: code !== undefined ? `Tool result: ${code}` : "Tool result",
          category: "result",
          toolOrModel: p.tool,
          statusCode: code,
          isSuccess: isSuccess,
          latencyMs: p.latency_ms,
          summary: p.error_type || (p.output_preview ? p.output_preview.slice(0, 90) : undefined),
        };
      }

      case "STATE_UPDATE":
        if (p.state === "RECOVERING") {
          return {
            title: "Agent recovery",
            category: "recovery",
            isSuccess: null,
            summary: "Attempting autonomous error recovery",
          };
        }
        return {
          title: `State: ${p.state || "update"}`,
          category: "system",
          summary: p.step ? `Step ${p.step}` : undefined,
        };

      case "AGENT_ERROR":
        return {
          title: "Agent error",
          category: "recovery",
          statusCode: p.status_code || 500,
          isSuccess: false,
          summary: p.error || "Agent execution error",
        };

      case "FAILURE_DETECTED":
        return {
          title: `Failure: ${p.failure_type || "Detected"}`,
          category: "recovery",
          isSuccess: false,
          summary: p.root_cause || (p.evidence ? p.evidence[0] : undefined),
        };

      case "VERIFICATION_STARTED":
        return {
          title: "Verification",
          category: "verify",
          summary: p.verifier_type ? `Verifier: ${p.verifier_type}` : undefined,
        };

      case "VERIFICATION_RESULT":
        return {
          title: "Verification",
          category: "verify",
          isSuccess: p.passed === true,
          latencyMs: p.duration_ms,
          summary: p.feedback || (p.passed ? "Verification passed" : "Verification failed"),
        };

      case "AGENT_COMPLETED":
        return {
          title: "Completed",
          category: "agent",
          isSuccess: p.status === "COMPLETED" || p.verification_passed === true,
          summary: p.status ? `Status: ${p.status} (${p.steps || 0} steps, ${p.tool_calls || 0} tool calls)` : undefined,
        };

      case "SELF_REFLECTION_STARTED":
        return {
          title: "Self-reflection started",
          category: "system",
        };

      case "SELF_REFLECTION_COMPLETED":
        return {
          title: "Self-reflection completed",
          category: "system",
          summary: p.learned_rules_count ? `${p.learned_rules_count} rule(s) retained in tool memory` : undefined,
        };

      case "TOOL_PLAYBOOK_LEARNED":
        return {
          title: `Playbook learned: ${p.tool || "tool"}`,
          category: "system",
          toolOrModel: p.tool,
          isSuccess: true,
          summary: p.learned_rule,
        };

      case "MUTATION_PROPOSED":
        return {
          title: `Mutation proposed: ${p.type || "agent"}`,
          category: "mutation",
          summary: p.target,
        };

      case "MUTATION_APPLIED":
        return {
          title: "Mutation applied",
          category: "mutation",
          isSuccess: true,
          summary: p.reason || p.mutation_type,
        };

      case "GENERATION_ACCEPTED":
        return {
          title: "Generation accepted",
          category: "system",
          isSuccess: true,
          summary: p.reason,
        };

      case "GENERATION_REJECTED":
        return {
          title: "Generation rejected",
          category: "system",
          isSuccess: false,
          summary: p.reason,
        };

      case "EXPERIMENT_CREATED":
        return {
          title: "Experiment created",
          category: "system",
          summary: p.name,
        };

      case "GENERATION_CREATED":
        return {
          title: `Generation created (G${p.generation_index ?? p.generation ?? ""})`,
          category: "system",
          toolOrModel: p.model,
        };

      case "EVALUATION_STARTED":
        return {
          title: "Evaluation started",
          category: "system",
          summary: p.benchmark ? `Benchmark: ${p.benchmark}` : undefined,
        };

      case "EVALUATION_COMPLETED":
        return {
          title: "Completed",
          category: "agent",
          isSuccess: true,
          summary: p.accuracy !== undefined ? `Accuracy: ${(p.accuracy * 100).toFixed(1)}%` : undefined,
        };

      default:
        return {
          title: t.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()),
          category: "system",
        };
    }
  };

  const handleVerifyProvenance = async () => {
    setVerifyingProvenance(true);
    try {
      const prov = await api.getProvenance(id);
      setProvenance(prov);
    } catch (err: any) {
      console.error("Provenance verification error", err);
    } finally {
      setVerifyingProvenance(false);
    }
  };

  const handleCopyProvenance = (text: string, label: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedProvenanceText(label);
      setTimeout(() => setCopiedProvenanceText(null), 2000);
    }
  };

  // Safe redaction helper to prevent exposing secrets in event payloads (FORGE S8-F)
  const sanitizePayload = (obj: any): any => {
    if (obj === null || obj === undefined) return obj;
    if (typeof obj === "string") {
      if (/^(sk-[a-zA-Z0-9_-]{10,}|ghp_[a-zA-Z0-9]{10,}|Bearer\s+[a-zA-Z0-9_\-\.]{10,})/i.test(obj)) {
        return "[REDACTED_SECRET]";
      }
      return obj;
    }
    if (Array.isArray(obj)) {
      return obj.map(sanitizePayload);
    }
    if (typeof obj === "object") {
      const cleaned: Record<string, any> = {};
      for (const [k, v] of Object.entries(obj)) {
        const lower = k.toLowerCase();
        if (
          lower.includes("secret") ||
          lower.includes("token") ||
          lower.includes("password") ||
          lower.includes("api_key") ||
          lower.includes("apikey") ||
          lower.includes("auth") ||
          lower.includes("credential")
        ) {
          cleaned[k] = "[REDACTED_SECRET]";
        } else {
          cleaned[k] = sanitizePayload(v);
        }
      }
      return cleaned;
    }
    return obj;
  };

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
      const [exp, gens, prov, evs, mems, evd] = await Promise.all([
        api.getExperiment(id),
        api.getGenerations(id),
        api.getProvenance(id),
        api.getEvents(id, 150),
        api.getToolMemory(id).catch(() => []),
        api.getEvidence(id, selectedEvidenceGenId || undefined).catch(() => null),
      ]);
      setExperiment(exp);
      setGenerations(gens);
      setProvenance(prov);
      setEvents((prev) => {
        const map = new Map<string, TraceEvent>();
        for (const ev of [...prev, ...evs]) {
          const key = ev.event_id || `${ev.timestamp}-${ev.type}`;
          map.set(key, ev);
        }
        return Array.from(map.values()).sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
      });
      setToolMemories(mems);
      if (evd) setEvidenceData(evd);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectEvidenceGen = async (genId: string) => {
    setSelectedEvidenceGenId(genId);
    setLoadingEvidence(true);
    try {
      const ev = await api.getEvidence(id, genId);
      setEvidenceData(ev);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingEvidence(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [id]);

  // Connect SSE Live Stream (FORGE S8-E)
  useEffect(() => {
    if (!id) return;

    setSseStatus("connecting");
    setSseError(null);

    let isSubscribed = true;
    let es: EventSource | null = null;

    try {
      es = new EventSource(`${API_BASE}/experiments/${id}/stream`);

      es.onopen = () => {
        if (!isSubscribed) return;
        setSseStatus("connected");
        setSseError(null);
      };

      const handleTraceEvent = (e: MessageEvent) => {
        if (!isSubscribed) return;
        try {
          const ev: TraceEvent = JSON.parse(e.data);
          setEvents((prev) => {
            const exists = prev.some(
              (p) => p.event_id === ev.event_id || (p.timestamp === ev.timestamp && p.type === ev.type)
            );
            if (exists) return prev;
            const updated = [...prev, ev];
            return updated.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
          });

          if (ev.type === "AGENT_COMPLETED" || ev.type === "EVALUATION_COMPLETED") {
            setSseStatus("completed");
          } else {
            setSseStatus("connected");
          }
        } catch (err) {
          // Non-JSON or heartbeat
        }
      };

      // Named event types dispatched by backend FastAPI StreamingResponse
      const eventTypes = [
        "connected",
        "EXPERIMENT_CREATED",
        "GENERATION_CREATED",
        "AGENT_STARTED",
        "MODEL_CALL",
        "MODEL_RESPONSE",
        "TOOL_CALL",
        "TOOL_RESULT",
        "STATE_UPDATE",
        "AGENT_ERROR",
        "AGENT_COMPLETED",
        "VERIFICATION_STARTED",
        "VERIFICATION_RESULT",
        "EVALUATION_STARTED",
        "EVALUATION_COMPLETED",
        "FAILURE_DETECTED",
        "MUTATION_PROPOSED",
        "MUTATION_APPLIED",
        "GENERATION_ACCEPTED",
        "GENERATION_REJECTED",
        "SELF_REFLECTION_STARTED",
        "SELF_REFLECTION_COMPLETED",
        "TOOL_PLAYBOOK_LEARNED",
      ];

      es.addEventListener("connected", () => {
        if (!isSubscribed) return;
        setSseStatus("connected");
        setSseError(null);
      });

      for (const et of eventTypes) {
        if (et !== "connected") {
          es.addEventListener(et, handleTraceEvent);
        }
      }

      es.onmessage = handleTraceEvent;

      es.onerror = () => {
        if (!isSubscribed) return;
        if (es?.readyState === EventSource.CLOSED) {
          setSseStatus("failed");
          setSseError(`Live event stream disconnected or unreachable at ${API_BASE}/experiments/${id}/stream.`);
        } else if (es?.readyState === EventSource.CONNECTING) {
          setSseStatus("connecting");
        }
      };
    } catch (e: any) {
      if (isSubscribed) {
        setSseStatus("failed");
        setSseError(e?.message || "Failed to initialize EventSource stream.");
      }
    }

    return () => {
      isSubscribed = false;
      if (es) {
        es.close();
      }
    };
  }, [id, sseReconnectCount]);

  useEffect(() => {
    if (activeTab === "console" && autoScroll) {
      consoleBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, activeTab, autoScroll]);

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

  const effectiveStatus: "connecting" | "connected" | "disconnected" | "completed" | "failed" =
    sseStatus === "failed"
      ? "failed"
      : sseStatus === "disconnected"
      ? "disconnected"
      : sseStatus === "connecting"
      ? "connecting"
      : (sseStatus === "completed" || experiment.status === "COMPLETED" || (events.length > 0 && (events[events.length - 1].type === "AGENT_COMPLETED" || events[events.length - 1].type === "EVALUATION_COMPLETED")))
      ? "completed"
      : "connected";

  const filteredEvents = events.filter((ev) => {
    if (consoleFilter === "all") return true;
    if (consoleFilter === "tools") return ev.type.includes("TOOL");
    if (consoleFilter === "model") return ev.type.includes("MODEL");
    if (consoleFilter === "errors") {
      return (
        ev.type.includes("ERROR") ||
        ev.type.includes("FAILURE") ||
        (ev.type === "TOOL_RESULT" && ev.payload?.success === false) ||
        (ev.type === "STATE_UPDATE" && ev.payload?.state === "RECOVERING") ||
        (ev.type === "VERIFICATION_RESULT" && ev.payload?.passed === false)
      );
    }
    if (consoleFilter === "verify") return ev.type.includes("VERIF");
    return true;
  });

  const firstEvent = events.length > 0 ? events[0] : null;
  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
  const selectedProvenanceEvent =
    events.find((e) => e.event_id === selectedProvenanceEventId) ||
    latestEvent ||
    firstEvent ||
    null;
  const selectedProvenanceIndex = selectedProvenanceEvent
    ? events.findIndex((e) => e.event_id === selectedProvenanceEvent.event_id)
    : -1;
  const previousEventOfSelected =
    selectedProvenanceIndex > 0 ? events[selectedProvenanceIndex - 1] : null;

  const filteredProvenanceEvents = events.filter((ev) => {
    if (!provenanceSearchQuery) return true;
    const q = provenanceSearchQuery.toLowerCase();
    return (
      ev.type.toLowerCase().includes(q) ||
      ev.event_id.toLowerCase().includes(q) ||
      ev.event_hash.toLowerCase().includes(q) ||
      ev.previous_event_hash.toLowerCase().includes(q)
    );
  });

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
            <Brain className="w-4 h-4" /> Causal Evidence & Learning ({toolMemories.length})
          </button>
          <button
            onClick={() => setActiveTab("console")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "console" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Terminal className="w-4 h-4" /> Live Execution Console ({events.length})
            {effectiveStatus === "connected" && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("provenance")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === "provenance" ? "border-orange-500 text-white" : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <ShieldCheck className="w-4 h-4" /> Provenance Inspector
            {provenance?.is_valid && !verifyingProvenance && (
              <span className="text-[10px] px-1.5 py-0.2 rounded font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ✓ Valid
              </span>
            )}
            {provenance && !provenance.is_valid && !verifyingProvenance && (
              <span className="text-[10px] px-1.5 py-0.2 rounded font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                ⚠ Failed
              </span>
            )}
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

      {/* Live Execution Console (FORGE S8-E) */}
      {activeTab === "console" && (
        <div className="bg-[#0a0c10] border border-[#30363d] rounded-2xl overflow-hidden shadow-2xl">
          {/* Console Header Bar */}
          <div className="px-5 py-3.5 bg-[#12151d] border-b border-[#30363d] flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
                <Terminal className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white tracking-wide">Live Execution Console</h3>
                  <span className="text-[10px] text-gray-500 font-mono">/api/experiments/{id}/stream</span>
                </div>
                <p className="text-[11px] text-gray-400">
                  Real-time agent telemetry via Server-Sent Events (SSE) • Exact database records in chronological order
                </p>
              </div>
            </div>

            {/* Connection Status & Stream Controls */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* SSE Connection Status Pill */}
              {effectiveStatus === "connecting" && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
                  <RotateCw className="w-3 h-3 animate-spin" /> Connecting...
                </span>
              )}
              {effectiveStatus === "connected" && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live Stream Connected
                </span>
              )}
              {effectiveStatus === "completed" && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  <CheckCircle2 className="w-3 h-3" /> Execution Completed
                </span>
              )}
              {effectiveStatus === "disconnected" && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/30">
                  <Radio className="w-3 h-3" /> Disconnected
                </span>
              )}
              {effectiveStatus === "failed" && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <AlertTriangle className="w-3 h-3" /> Connection Failed
                </span>
              )}

              {/* Auto-Scroll Toggle */}
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer ${
                  autoScroll
                    ? "bg-orange-500/20 text-orange-300 border-orange-500/40"
                    : "bg-[#161b22] text-gray-400 border-[#30363d] hover:text-gray-200"
                }`}
                title="Automatically scroll to newest events"
              >
                <ArrowDown className="w-3 h-3" />
                Auto-scroll {autoScroll ? "ON" : "OFF"}
              </button>

              {/* Reconnect / Refresh Button */}
              <button
                onClick={() => {
                  setSseReconnectCount((c) => c + 1);
                  loadData();
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-[#161b22] hover:bg-[#21262d] text-gray-300 border border-[#30363d] transition cursor-pointer"
                title="Reconnect SSE stream and reload database events"
              >
                <RefreshCw className="w-3 h-3" /> Reconnect
              </button>
            </div>
          </div>

          {/* Truthful Error Banner if SSE is Unavailable */}
          {(effectiveStatus === "failed" || sseError) && (
            <div className="mx-4 mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-start gap-2.5 text-rose-200">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-rose-300">Live SSE Stream Unavailable:</span>{" "}
                  {sseError || "Unable to establish real-time stream connection with backend."}{" "}
                  Showing persisted database telemetry ({events.length} events loaded). No fake stream is being simulated.
                </div>
              </div>
              <button
                onClick={() => {
                  setSseReconnectCount((c) => c + 1);
                  loadData();
                }}
                className="self-start sm:self-auto px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/30 font-semibold transition cursor-pointer shrink-0"
              >
                Retry Connection
              </button>
            </div>
          )}

          {/* Filter Toolbar */}
          <div className="px-5 py-2.5 bg-[#0d1117] border-b border-[#21262d] flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-gray-500 mr-1 flex items-center gap-1 text-[11px]">
                <Filter className="w-3 h-3" /> Filter:
              </span>
              <button
                onClick={() => setConsoleFilter("all")}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer text-xs ${
                  consoleFilter === "all"
                    ? "bg-[#21262d] text-white font-bold border border-[#30363d]"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161b22]"
                }`}
              >
                All Events ({events.length})
              </button>
              <button
                onClick={() => setConsoleFilter("tools")}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer text-xs ${
                  consoleFilter === "tools"
                    ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161b22]"
                }`}
              >
                Tools & Results ({events.filter((e) => e.type.includes("TOOL")).length})
              </button>
              <button
                onClick={() => setConsoleFilter("model")}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer text-xs ${
                  consoleFilter === "model"
                    ? "bg-blue-500/20 text-blue-300 font-bold border border-blue-500/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161b22]"
                }`}
              >
                Model Calls ({events.filter((e) => e.type.includes("MODEL")).length})
              </button>
              <button
                onClick={() => setConsoleFilter("errors")}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer text-xs ${
                  consoleFilter === "errors"
                    ? "bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161b22]"
                }`}
              >
                Errors & Recovery ({events.filter((e) => e.type.includes("ERROR") || e.type.includes("FAILURE") || (e.payload?.status_code && e.payload?.status_code >= 400) || e.payload?.state === "RECOVERING").length})
              </button>
              <button
                onClick={() => setConsoleFilter("verify")}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer text-xs ${
                  consoleFilter === "verify"
                    ? "bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161b22]"
                }`}
              >
                Verification ({events.filter((e) => e.type.includes("VERIF")).length})
              </button>
            </div>

            <div className="text-[11px] text-gray-500 hidden lg:block font-mono">
              Click event row to expand raw payload
            </div>
          </div>

          {/* Chronological Event Stream Feed */}
          <div className="max-h-[580px] overflow-y-auto divide-y divide-[#21262d]/40 font-mono text-xs select-text">
            {filteredEvents.length === 0 ? (
              <div className="py-16 text-center text-gray-500 font-mono space-y-2">
                <Terminal className="w-8 h-8 mx-auto text-gray-600 opacity-60" />
                <p>No events match the selected filter.</p>
                <p className="text-[11px] text-gray-600">
                  Execute "Run Benchmark" or "Evolve Agent" to trigger live execution events.
                </p>
              </div>
            ) : (
              filteredEvents.map((ev, i) => {
                const desc = getEventDescriptor(ev);
                const rowKey = ev.event_id || `${ev.timestamp}-${i}`;
                const isExpanded = expandedEventId === rowKey;
                const timeStr = formatEventTime(ev.timestamp);

                return (
                  <div key={rowKey} className="group hover:bg-[#161b22]/70 transition-colors">
                    <div
                      onClick={() => setExpandedEventId(isExpanded ? null : rowKey)}
                      className="px-4 py-2 flex items-center gap-3 cursor-pointer"
                    >
                      {/* 1. Timestamp (e.g. 20:41:03) */}
                      <span className="text-gray-500 text-[11px] w-18 shrink-0 font-medium tracking-tight">
                        {timeStr}
                      </span>

                      {/* 2. Success / Failure indicator dot */}
                      <span className="shrink-0 flex items-center justify-center w-3 h-3">
                        {desc.isSuccess === true ? (
                          <span className="w-2 h-2 rounded-full bg-emerald-400" title="Success" />
                        ) : desc.isSuccess === false ? (
                          <span className="w-2 h-2 rounded-full bg-rose-500" title="Failure" />
                        ) : (
                          <span className="w-2 h-2 rounded-full bg-amber-400" title="State transition / Warning" />
                        )}
                      </span>

                      {/* 3. Event Type / Title */}
                      <span className={`font-semibold shrink-0 ${
                        desc.isSuccess === false
                          ? "text-rose-400"
                          : desc.category === "tool" || desc.category === "result"
                          ? "text-amber-300"
                          : desc.category === "model"
                          ? "text-blue-300"
                          : desc.category === "recovery"
                          ? "text-orange-400"
                          : desc.category === "verify"
                          ? "text-purple-300"
                          : "text-gray-200"
                      }`}>
                        {desc.title}
                      </span>

                      {/* 4. Tool/Model Name where safe */}
                      {desc.toolOrModel && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#1c2128] text-cyan-300 border border-[#30363d] shrink-0">
                          {desc.toolOrModel}
                        </span>
                      )}

                      {/* 5. Relevant status code badge */}
                      {desc.statusCode !== undefined && (
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                          desc.statusCode >= 200 && desc.statusCode < 300
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : desc.statusCode === 422
                            ? "bg-orange-500/10 text-orange-400 border border-orange-500/30"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                        }`}>
                          {desc.statusCode}
                        </span>
                      )}

                      {/* 6. Latency when available */}
                      {desc.latencyMs !== undefined && (
                        <span className="text-gray-500 text-[10px] shrink-0 flex items-center gap-1 font-mono">
                          <Clock className="w-2.5 h-2.5" />
                          {desc.latencyMs >= 1000
                            ? `${(desc.latencyMs / 1000).toFixed(2)}s`
                            : `${Math.round(desc.latencyMs)}ms`}
                        </span>
                      )}

                      {/* Context / Preview summary */}
                      {desc.summary && (
                        <span className="text-gray-400 text-[11px] truncate flex-1 min-w-0 font-normal">
                          {desc.summary}
                        </span>
                      )}

                      {/* Expand / collapse icon */}
                      <span className="text-gray-600 group-hover:text-gray-400 ml-auto shrink-0 pl-2 transition-colors">
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </span>
                    </div>

                    {/* Expandable JSON Payload & Provenance Inspector */}
                    {isExpanded && (
                      <div className="px-4 pb-3 pt-1.5 bg-[#0d1117] border-t border-[#21262d]">
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex flex-wrap items-center justify-between gap-2">
                          <span>Event ID: {ev.event_id || "unassigned"}</span>
                          <span>Type: {ev.type}</span>
                          {ev.generation_id && <span>Gen ID: {ev.generation_id.slice(0, 8)}...</span>}
                          {ev.execution_id && <span>Exec ID: {ev.execution_id.slice(0, 8)}...</span>}
                          <span>
                            SHA-256 Hash:{" "}
                            {ev.event_hash ? (
                              <span className="text-cyan-400">{ev.event_hash.slice(0, 16)}...</span>
                            ) : (
                              "Genesis Root"
                            )}
                          </span>
                        </div>
                        <pre className="p-3 rounded-lg bg-[#161b22] text-gray-300 text-[11px] overflow-x-auto border border-[#30363d] leading-relaxed">
                          {JSON.stringify(ev.payload, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })
            )}
            <div ref={consoleBottomRef} />
          </div>

          {/* Console Footer Bar */}
          <div className="px-5 py-2.5 bg-[#12151d] border-t border-[#30363d] flex flex-wrap items-center justify-between gap-3 text-[11px] text-gray-400 font-mono">
            <div className="flex items-center gap-3">
              <span>Showing {filteredEvents.length} of {events.length} telemetry events</span>
              <span>•</span>
              <span className="text-gray-500">Auto-scroll: {autoScroll ? "Active" : "Disabled"}</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-500">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Cryptographic hash verification chained</span>
            </div>
          </div>
        </div>
      )}

      {/* Cryptographic Provenance Inspector (FORGE S8-F) */}
      {activeTab === "provenance" && (
        <div className="space-y-6">
          {/* Main Verification Status Card */}
          <div className={`rounded-2xl p-6 border shadow-2xl transition-all ${
            verifyingProvenance || !provenance
              ? "bg-[#161b22] border-[#30363d]"
              : provenance.is_valid
              ? "bg-gradient-to-r from-[#161b22] to-[#12231c] border-emerald-500/30 shadow-emerald-950/20"
              : "bg-gradient-to-r from-[#161b22] to-[#251318] border-rose-500/30 shadow-rose-950/20"
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start sm:items-center gap-4">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 border ${
                  verifyingProvenance || !provenance
                    ? "bg-[#21262d] text-gray-400 border-[#30363d]"
                    : provenance.is_valid
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-lg shadow-emerald-500/10"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-lg shadow-rose-500/10"
                }`}>
                  {verifyingProvenance ? (
                    <RotateCw className="w-7 h-7 animate-spin text-orange-400" />
                  ) : !provenance ? (
                    <ShieldCheck className="w-7 h-7 text-gray-400" />
                  ) : provenance.is_valid ? (
                    <Check className="w-8 h-8 text-emerald-400 stroke-[2.5]" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-rose-400 stroke-[2.5]" />
                  )}
                </div>

                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-gray-400 flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-gray-400" />
                    Provenance
                  </div>
                  <div className="text-2xl sm:text-3xl font-black mt-0.5 flex items-center gap-2 tracking-tight">
                    {verifyingProvenance ? (
                      <span className="text-gray-300">Verifying chain...</span>
                    ) : !provenance ? (
                      <span className="text-gray-400">Verification pending</span>
                    ) : provenance.is_valid ? (
                      <span className="text-emerald-400 flex items-center gap-2">
                        <span>✓</span> Valid
                      </span>
                    ) : (
                      <span className="text-rose-400 flex items-center gap-2">
                        <span>⚠</span> Verification failed
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-1 max-w-2xl font-mono">
                    {provenance?.message || (verifyingProvenance ? "Auditing SHA-256 links across all stored events..." : "Click verify to compute cryptographic event hashes.")}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 self-start sm:self-auto">
                <button
                  onClick={handleVerifyProvenance}
                  disabled={verifyingProvenance}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d1117] hover:bg-[#21262d] text-gray-200 border border-[#30363d] text-xs font-semibold shadow-md transition cursor-pointer disabled:opacity-50"
                  title="Run cryptographic verification over full event chain"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${verifyingProvenance ? "animate-spin text-orange-400" : ""}`} />
                  {verifyingProvenance ? "Auditing..." : "Re-verify Hash Chain"}
                </button>
              </div>
            </div>

            {/* Tamper-evident SHA-256 chain blockquote callout */}
            <div className="mt-5 p-3.5 rounded-xl bg-[#0d1117]/80 border border-[#30363d] flex items-start gap-3 text-xs text-gray-300">
              <Lock className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div>
                  <span className="font-bold text-white">Tamper-evident SHA-256 chain:</span> Each trace event derives its hash deterministically from the predecessor hash and canonical payload representation:
                </div>
                <code className="text-cyan-300 font-mono text-[11px] block bg-[#161b22] px-2 py-1 rounded border border-[#21262d]">
                  H_n = SHA-256( previous_hash + event_type + timestamp + canonical(payload) )
                </code>
                <p className="text-[11px] text-gray-400">
                  Any modified payload, altered hash, reordered event, or deleted record is immediately detected by the verification algorithm.
                </p>
              </div>
            </div>
          </div>

          {/* 5 Primary Summary Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5 text-xs">
            {/* 1. Total Event Count */}
            <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-1.5 flex flex-col justify-between">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">
                Total Event Count
              </span>
              <div>
                <div className="text-2xl font-black font-mono text-white">
                  {provenance?.total_events !== undefined ? provenance.total_events : events.length}
                </div>
                <p className="text-[11px] text-gray-500 font-mono mt-0.5">
                  Chained records
                </p>
              </div>
              <span className="text-[10px] text-emerald-400 font-mono">
                100% indexed
              </span>
            </div>

            {/* 2. First Event (Genesis) */}
            <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-1.5 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">
                  First Event (Genesis)
                </span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono font-bold">
                  #0
                </span>
              </div>
              <div>
                <div className="font-bold text-gray-200 text-xs truncate">
                  {firstEvent ? firstEvent.type : "N/A"}
                </div>
                <div className="text-[11px] text-gray-500 font-mono mt-0.5 truncate">
                  {firstEvent ? formatEventTime(firstEvent.timestamp) : "--:--:--"}
                </div>
              </div>
              <div className="text-[10px] font-mono text-gray-400 truncate" title={firstEvent?.event_hash || "Genesis"}>
                Hash: <span className="text-cyan-400">{firstEvent?.event_hash ? `${firstEvent.event_hash.slice(0, 10)}...` : "Genesis"}</span>
              </div>
            </div>

            {/* 3. Latest Event (Tip) */}
            <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-1.5 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">
                  Latest Event (Tip)
                </span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono font-bold">
                  #{events.length > 0 ? events.length - 1 : 0}
                </span>
              </div>
              <div>
                <div className="font-bold text-gray-200 text-xs truncate">
                  {latestEvent ? latestEvent.type : "N/A"}
                </div>
                <div className="text-[11px] text-gray-500 font-mono mt-0.5 truncate">
                  {latestEvent ? formatEventTime(latestEvent.timestamp) : "--:--:--"}
                </div>
              </div>
              <div className="text-[10px] font-mono text-gray-400 truncate" title={latestEvent?.event_hash || provenance?.latest_hash || ""}>
                Hash: <span className="text-cyan-400">{latestEvent?.event_hash ? `${latestEvent.event_hash.slice(0, 10)}...` : provenance?.latest_hash ? `${provenance.latest_hash.slice(0, 10)}...` : "N/A"}</span>
              </div>
            </div>

            {/* 4. Hash-Chain Status */}
            <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-1.5 flex flex-col justify-between">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">
                Hash-Chain Status
              </span>
              <div>
                <div className="text-sm font-bold font-mono">
                  {verifyingProvenance ? (
                    <span className="text-gray-400">Verifying...</span>
                  ) : !provenance ? (
                    <span className="text-gray-500">Unverified</span>
                  ) : provenance.is_valid ? (
                    <span className="text-emerald-400">Unbroken Chain</span>
                  ) : (
                    <span className="text-rose-400">Broken at #{provenance.broken_index}</span>
                  )}
                </div>
                <p className="text-[11px] text-gray-500 font-mono mt-0.5">
                  Tamper-evident
                </p>
              </div>
              <div className="text-[10px] font-mono text-gray-400 truncate" title={provenance?.genesis_hash}>
                Root: <span className="text-gray-400">{provenance?.genesis_hash ? `${provenance.genesis_hash.slice(0, 8)}...` : "00000000..."}</span>
              </div>
            </div>

            {/* 5. Verification Result */}
            <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] space-y-1.5 flex flex-col justify-between">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">
                Verification Result
              </span>
              <div>
                <div className="text-sm font-black font-mono">
                  {verifyingProvenance ? (
                    <span className="text-gray-400">PENDING</span>
                  ) : !provenance ? (
                    <span className="text-gray-500">AWAITING</span>
                  ) : provenance.is_valid ? (
                    <span className="text-emerald-400">PASS (Deterministic)</span>
                  ) : (
                    <span className="text-rose-400">FAIL (Tamper Detected)</span>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 mt-0.5 truncate" title={provenance?.message}>
                  {provenance?.message || "Audit required"}
                </p>
              </div>
              <div className="text-[10px] font-mono text-gray-400">
                Broken index: <strong className={provenance?.broken_index !== null && provenance?.broken_index !== undefined ? "text-rose-400" : "text-emerald-400"}>{provenance?.broken_index !== null && provenance?.broken_index !== undefined ? `#${provenance.broken_index}` : "None"}</strong>
              </div>
            </div>
          </div>

          {/* Interactive Individual Event Inspector */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl overflow-hidden shadow-xl">
            <div className="px-5 py-4 border-b border-[#30363d] flex flex-col md:flex-row md:items-center justify-between gap-3 bg-[#12151d]">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Eye className="w-4 h-4 text-orange-400" />
                  Individual Event Provenance Inspector
                </h4>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Select any event in the tamper-evident chain to audit its input hash, canonical payload, and resulting hash
                </p>
              </div>

              {/* Event Search / Filter */}
              <div className="relative w-full md:w-72">
                <Search className="w-3.5 h-3.5 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter events by type or hash..."
                  value={provenanceSearchQuery}
                  onChange={(e) => setProvenanceSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-orange-500 font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-[#30363d]">
              {/* Event List / Chain Navigator (5 cols) */}
              <div className="lg:col-span-5 max-h-[560px] overflow-y-auto divide-y divide-[#21262d]/60 font-mono text-xs">
                {filteredProvenanceEvents.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    No events match the search filter.
                  </div>
                ) : (
                  filteredProvenanceEvents.map((ev, i) => {
                    const originalIdx = events.findIndex((e) => e.event_id === ev.event_id);
                    const isSelected = selectedProvenanceEvent?.event_id === ev.event_id;

                    return (
                      <div
                        key={ev.event_id || i}
                        onClick={() => setSelectedProvenanceEventId(ev.event_id)}
                        className={`p-3 cursor-pointer transition-colors flex items-center gap-3 ${
                          isSelected
                            ? "bg-orange-500/10 border-l-4 border-orange-500"
                            : "hover:bg-[#21262d]/50"
                        }`}
                      >
                        <span className="text-[10px] font-bold text-gray-500 w-8 shrink-0">
                          #{originalIdx >= 0 ? originalIdx : i}
                        </span>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold truncate ${
                              ev.type.includes("ERROR") || ev.type.includes("FAILURE")
                                ? "bg-rose-500/20 text-rose-300"
                                : ev.type.includes("TOOL")
                                ? "bg-amber-500/20 text-amber-300"
                                : ev.type.includes("ACCEPTED")
                                ? "bg-emerald-500/20 text-emerald-300"
                                : "bg-blue-500/20 text-blue-300"
                            }`}>
                              {ev.type}
                            </span>
                            <span className="text-[10px] text-gray-500 truncate">
                              {formatEventTime(ev.timestamp)}
                            </span>
                          </div>
                          <div className="text-[10px] text-gray-400 font-mono truncate mt-1">
                            Hash: <span className="text-cyan-400">{ev.event_hash ? ev.event_hash.slice(0, 14) + "..." : "Genesis"}</span>
                          </div>
                        </div>

                        <ChevronRight className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-orange-400" : "text-gray-600"}`} />
                      </div>
                    );
                  })
                )}
              </div>

              {/* Event Detail & Cryptographic Hash Auditor (7 cols) */}
              <div className="lg:col-span-7 p-5 space-y-4 max-h-[560px] overflow-y-auto bg-[#0d1117]/60">
                {selectedProvenanceEvent ? (
                  <>
                    {/* Event Metadata Header */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#30363d]">
                      <div>
                        <div className="flex items-center gap-2 font-mono">
                          <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 font-bold text-xs border border-orange-500/30">
                            Event #{selectedProvenanceIndex >= 0 ? selectedProvenanceIndex : 0}
                          </span>
                          <span className="text-white font-bold text-xs">
                            {selectedProvenanceEvent.type}
                          </span>
                        </div>
                        <div className="text-[11px] text-gray-400 font-mono mt-1 flex items-center gap-2">
                          <span>Time: {new Date(selectedProvenanceEvent.timestamp).toISOString()}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs font-mono">
                        <button
                          onClick={() => handleCopyProvenance(selectedProvenanceEvent.event_hash, "hash")}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#161b22] hover:bg-[#21262d] text-gray-300 border border-[#30363d] transition cursor-pointer text-[11px]"
                          title="Copy full 64-character SHA-256 event hash"
                        >
                          <Copy className="w-3 h-3" />
                          {copiedProvenanceText === "hash" ? "Copied Hash!" : "Copy Hash"}
                        </button>
                      </div>
                    </div>

                    {/* Hash Continuity Link Verification */}
                    <div className="p-3.5 rounded-xl bg-[#161b22] border border-[#30363d] space-y-3 font-mono text-xs">
                      <div className="flex items-center justify-between text-[11px] text-gray-400 pb-1 border-b border-[#21262d]">
                        <span className="flex items-center gap-1.5 font-bold text-gray-300">
                          <Link2 className="w-3.5 h-3.5 text-cyan-400" />
                          Cryptographic Hash Link Verification
                        </span>
                        {selectedProvenanceIndex === 0 ? (
                          <span className="text-purple-400">Genesis State (Root)</span>
                        ) : previousEventOfSelected && previousEventOfSelected.event_hash === selectedProvenanceEvent.previous_event_hash ? (
                          <span className="text-emerald-400">✓ Predecessor Link Valid</span>
                        ) : (
                          <span className="text-rose-400">⚠ Hash Link Mismatch</span>
                        )}
                      </div>

                      <div>
                        <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                          <span>PREVIOUS EVENT HASH (H_{selectedProvenanceIndex > 0 ? selectedProvenanceIndex - 1 : "genesis"})</span>
                          <button
                            onClick={() => handleCopyProvenance(selectedProvenanceEvent.previous_event_hash, "prev_hash")}
                            className="hover:text-gray-300 text-[10px]"
                          >
                            {copiedProvenanceText === "prev_hash" ? "Copied" : "Copy"}
                          </button>
                        </div>
                        <div className="p-2 rounded bg-[#0d1117] text-gray-300 text-[11px] break-all border border-[#21262d]">
                          {selectedProvenanceEvent.previous_event_hash || "0".repeat(64)}
                        </div>
                      </div>

                      <div className="text-center text-gray-500 text-[10px] flex items-center justify-center gap-2">
                        <ArrowDown className="w-3 h-3 text-orange-400" />
                        <span>SHA-256( previous_hash + type + timestamp + canonical_payload )</span>
                        <ArrowDown className="w-3 h-3 text-orange-400" />
                      </div>

                      <div>
                        <div className="flex items-center justify-between text-[10px] text-gray-500 mb-1">
                          <span>THIS EVENT HASH (H_{selectedProvenanceIndex >= 0 ? selectedProvenanceIndex : 0})</span>
                          <button
                            onClick={() => handleCopyProvenance(selectedProvenanceEvent.event_hash, "this_hash")}
                            className="hover:text-gray-300 text-[10px]"
                          >
                            {copiedProvenanceText === "this_hash" ? "Copied" : "Copy"}
                          </button>
                        </div>
                        <div className="p-2 rounded bg-[#0d1117] text-cyan-300 text-[11px] break-all border border-[#21262d] font-bold">
                          {selectedProvenanceEvent.event_hash || "Unassigned"}
                        </div>
                      </div>
                    </div>

                    {/* Sanitized Payload View (Secrets Redacted!) */}
                    <div className="space-y-1.5 font-mono text-xs">
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span className="flex items-center gap-1.5 font-semibold text-gray-300">
                          <Lock className="w-3 h-3 text-emerald-400" />
                          Canonical Event Payload (Secrets Redacted)
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Safe Display
                          </span>
                          <button
                            onClick={() => handleCopyProvenance(JSON.stringify(sanitizePayload(selectedProvenanceEvent.payload), null, 2), "payload")}
                            className="hover:text-gray-300 text-[10px] text-gray-500"
                          >
                            {copiedProvenanceText === "payload" ? "Copied JSON" : "Copy JSON"}
                          </button>
                        </div>
                      </div>

                      <pre className="p-3.5 rounded-xl bg-[#161b22] text-gray-300 text-[11px] overflow-x-auto border border-[#30363d] leading-relaxed max-h-[220px]">
                        {JSON.stringify(sanitizePayload(selectedProvenanceEvent.payload), null, 2)}
                      </pre>
                    </div>

                    {/* Cross-Link Identifiers */}
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                      <div className="p-2 rounded bg-[#161b22] border border-[#21262d]">
                        <span className="text-gray-500 block text-[10px]">Generation ID:</span>
                        <span className="text-gray-300 truncate block">
                          {selectedProvenanceEvent.generation_id || "None (Root/Genesis)"}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-[#161b22] border border-[#21262d]">
                        <span className="text-gray-500 block text-[10px]">Execution ID:</span>
                        <span className="text-gray-300 truncate block">
                          {selectedProvenanceEvent.execution_id || "None (Lifecycle)"}
                        </span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-12 text-center text-gray-500 font-mono">
                    No event selected. Select an event from the sequence list to inspect its provenance.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Causal Evidence & Learning Tab (FORGE S8-D) */}
      {activeTab === "learning" && (
        <div className="space-y-6">
          {/* Header Card */}
          <div className="bg-[#161b22] border border-orange-500/30 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-orange-400 font-bold text-xs uppercase tracking-wider">
                  <Brain className="w-4 h-4 text-orange-400" /> Causal Learning Architecture & Evidence Graph
                </div>
                <h2 className="text-xl font-black text-white mt-1">
                  Evidence-Linked Causal Learning Flow
                </h2>
                <p className="text-xs text-gray-400 mt-1 max-w-3xl">
                  Inspect the unbroken causal chain connecting failure telemetry, self-reflection, persistent tool memory,
                  evolutionary mutations, and evaluated downstream generations. Every link is backed by persisted foreign keys and cryptographic provenance.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => handlePlayAudio(`learning-${id}`, api.getLearningNarrationAudioUrl(id))}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-sm font-semibold transition cursor-pointer"
                >
                  <Volume2 className={`w-4 h-4 ${playingGenId === `learning-${id}` ? "animate-pulse text-purple-400" : ""}`} />
                  {playingGenId === `learning-${id}` ? "Playing Voice Debrief..." : "Voice Debrief (Smallest.ai)"}
                </button>

                <button
                  onClick={handleLearningLoop}
                  disabled={!!loadingAction}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white text-sm font-semibold shadow-lg shadow-orange-500/20 disabled:opacity-50 cursor-pointer"
                >
                  <Zap className={`w-4 h-4 ${loadingAction === "learning" ? "animate-spin" : ""}`} />
                  {loadingAction === "learning" ? "Running Learning Cycle..." : "Execute Learning Loop"}
                </button>
              </div>
            </div>

            {/* Dual-Pass Run 1 vs Run 2 Live Scoreboard (if executed) */}
            {learningReport && (
              <div className="mt-6 pt-6 border-t border-[#30363d] space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Live Dual-Pass Learning Acceleration (Run 1 Cold vs. Run 2 Warm Memory)
                  </div>
                  <span className="text-[11px] font-mono text-gray-500">
                    Evidence-linked cause: reflected memory prevents cold exploration errors
                  </span>
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
                    <span className="text-[11px] text-gray-500">Zero exploratory recovery loops</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 5-STAGE CAUSAL EVIDENCE PIPELINE */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 shadow-xl space-y-6">
            {/* Pipeline Header & View Mode Switch */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#30363d] pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-orange-400" /> Causal Trace Progression (5 Stages)
                </span>
                <p className="text-xs text-gray-400 mt-0.5">
                  Visual communication of failure reflection and evolutionary adaptation
                </p>
              </div>

              <div className="flex items-center gap-2 bg-[#0d1117] p-1 rounded-xl border border-[#30363d]">
                <button
                  onClick={() => setCausalViewMode("featured")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                    causalViewMode === "featured"
                      ? "bg-orange-500 text-white shadow"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  Stored Real Example (Linear API)
                </button>
                <button
                  onClick={() => setCausalViewMode("experiment")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                    causalViewMode === "experiment"
                      ? "bg-orange-500 text-white shadow"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  Live Experiment Evidence ({evidenceData?.mutations?.length || 0} mutations)
                </button>
              </div>
            </div>

            {/* Horizontal 5-Step Pipeline Overview Indicator */}
            <div className="bg-[#0d1117] border border-[#30363d] rounded-xl p-3.5 overflow-x-auto">
              <div className="flex items-center justify-between gap-2 min-w-max text-xs font-mono">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 font-bold">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                  <span>FAILURE</span>
                </div>
                <div className="text-gray-600 font-bold px-1">↓</div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 font-bold">
                  <Lightbulb className="w-3.5 h-3.5 text-purple-400" />
                  <span>REFLECTION</span>
                </div>
                <div className="text-gray-600 font-bold px-1">↓</div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 font-bold">
                  <Database className="w-3.5 h-3.5 text-amber-400" />
                  <span>MEMORY</span>
                </div>
                <div className="text-gray-600 font-bold px-1">↓</div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-300 font-bold">
                  <Dna className="w-3.5 h-3.5 text-blue-400" />
                  <span>MUTATION</span>
                </div>
                <div className="text-gray-600 font-bold px-1">↓</div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>NEW GENERATION</span>
                </div>
              </div>
            </div>

            {/* VIEW 1: FEATURED STORED REAL EXAMPLE (LINEAR API QUIRK) */}
            {causalViewMode === "featured" && (
              <div className="space-y-4">
                {/* 1. FAILURE */}
                <div className="rounded-2xl border border-rose-500/30 bg-[#0d1117] p-5 shadow-lg relative overflow-hidden">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 w-full">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          FAILURE
                        </span>
                        <span className="font-mono text-xs font-bold text-rose-400">HTTP 422</span>
                        <span className="font-mono text-xs text-gray-500">• linear_api</span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        Linear team identifier rejected
                      </h3>
                      <div className="bg-[#161b22] p-3 rounded-lg border border-rose-500/20 font-mono text-xs text-rose-300 space-y-1">
                        <div>HTTP 422 Unprocessable Entity: team_id must be a valid 36-character team UUID (e.g. &apos;550e8400-e29b-41d4-a716-446655440001&apos;).</div>
                        <div className="text-[11px] text-gray-500">Root cause: agent passed team slug &apos;CORE&apos; rather than UUID schema identifier.</div>
                      </div>
                    </div>
                    <div className="text-right font-mono text-[11px] text-gray-500 hidden sm:block shrink-0">
                      <span className="block text-gray-400 font-semibold">Persisted Source</span>
                      <span>Task: task_02_contextual_sla_routing</span>
                      <span className="block text-gray-500">Execution #33781481</span>
                    </div>
                  </div>
                </div>

                {/* Downward Connector 1 */}
                <div className="flex flex-col items-center justify-center my-1">
                  <div className="w-0.5 h-3 bg-gradient-to-b from-rose-500/40 to-purple-500/40"></div>
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                    <ArrowDown className="w-3 h-3 text-purple-400 animate-bounce" /> Evidence-linked cause
                  </div>
                  <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500/40 to-purple-500/40"></div>
                </div>

                {/* 2. REFLECTION */}
                <div className="rounded-2xl border border-purple-500/30 bg-[#0d1117] p-5 shadow-lg relative overflow-hidden">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 w-full">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          REFLECTION
                        </span>
                        <span className="font-mono text-xs font-bold text-purple-300">Category: SCHEMA_QUIRK</span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        Self-Reflection & Rule Synthesis
                      </h3>
                      <div className="bg-[#161b22] p-3 rounded-lg border border-purple-500/20 space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 block">Actual Learned Rule from Stored Evidence:</span>
                        <p className="text-xs text-white font-mono italic">
                          &ldquo;Linear requires a 36-character team UUID (&apos;550e8400-e29b-41d4-a716-446655440001&apos;). Do not pass team slugs like &apos;CORE&apos;.&rdquo;
                        </p>
                        <div className="text-[11px] text-gray-500 italic">
                          Evidence: &ldquo;Error 422 Unprocessable Entity: Linear requires 36-character team UUID.&rdquo;
                        </div>
                      </div>
                    </div>
                    <div className="text-right font-mono text-[11px] text-gray-500 hidden sm:block shrink-0">
                      <span className="block text-gray-400 font-semibold">Engine</span>
                      <span>ToolReflectionEngine</span>
                      <span className="block text-gray-500">Reflection Record #b2edeb2e</span>
                    </div>
                  </div>
                </div>

                {/* Downward Connector 2 */}
                <div className="flex flex-col items-center justify-center my-1">
                  <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500/40 to-amber-500/40"></div>
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                    <ArrowDown className="w-3 h-3 text-amber-400 animate-bounce" /> Evidence-linked cause
                  </div>
                  <div className="w-0.5 h-3 bg-gradient-to-b from-amber-500/40 to-amber-500/40"></div>
                </div>

                {/* 3. MEMORY */}
                <div className="rounded-2xl border border-amber-500/30 bg-[#0d1117] p-5 shadow-lg relative overflow-hidden">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          MEMORY
                        </span>
                        <span className="font-mono text-xs font-bold text-amber-400">ToolMemoryStore</span>
                      </div>
                      <span className="text-xs font-mono text-gray-500">Persisted in database tool_memories</span>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      Stored Tool Playbook Heuristic
                    </h3>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Stored Playbook</span>
                        <span className="font-mono text-xs font-bold text-white mt-1 block">linear_api</span>
                        <span className="text-[11px] text-gray-400 mt-0.5 block font-mono">create_issue with team_id</span>
                      </div>

                      <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Confidence</span>
                        <span className="font-mono text-xs font-bold text-emerald-400 mt-1 block">1.00 (100%)</span>
                        <span className="text-[11px] text-gray-400 mt-0.5 block">Observed 2x across runs</span>
                      </div>

                      <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Source Execution</span>
                        <span className="font-mono text-xs font-bold text-cyan-400 mt-1 block truncate">33781481-e1e1-421e</span>
                        <span className="text-[11px] text-gray-400 mt-0.5 block">Persisted foreign key link</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Downward Connector 3 */}
                <div className="flex flex-col items-center justify-center my-1">
                  <div className="w-0.5 h-3 bg-gradient-to-b from-amber-500/40 to-blue-500/40"></div>
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                    <ArrowDown className="w-3 h-3 text-blue-400 animate-bounce" /> Evidence-linked cause
                  </div>
                  <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500/40 to-blue-500/40"></div>
                </div>

                {/* 4. MUTATION */}
                <div className="rounded-2xl border border-blue-500/30 bg-[#0d1117] p-5 shadow-lg relative overflow-hidden">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          MUTATION
                        </span>
                        <span className="font-mono text-xs font-bold text-blue-400">VERIFIER_UPDATE</span>
                      </div>
                      <div className="font-mono text-xs text-gray-400">
                        Target: <strong className="text-white font-mono">verifier</strong>
                      </div>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      Mutation Spec & Rationale
                    </h3>

                    <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">Reason:</span>
                      <p className="text-xs text-gray-200 font-mono">
                        Observed 1 verification failure(s) where agent prematurely declared completion.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      <div className="p-3 rounded-xl bg-[#161b22] border border-rose-500/20 space-y-1">
                        <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block font-mono">Before</span>
                        <pre className="text-[11px] text-gray-300 font-mono overflow-x-auto">
{JSON.stringify({
  type: "none",
  require_zero_failed_tests: true,
  enforce_before_complete: true,
  min_test_count: 1
}, null, 2)}
                        </pre>
                      </div>

                      <div className="p-3 rounded-xl bg-[#161b22] border border-emerald-500/20 space-y-1">
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block font-mono">After</span>
                        <pre className="text-[11px] text-gray-300 font-mono overflow-x-auto">
{JSON.stringify({
  type: "mandatory_tests",
  require_zero_failed_tests: true,
  enforce_before_complete: true,
  min_test_count: 1
}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Downward Connector 4 */}
                <div className="flex flex-col items-center justify-center my-1">
                  <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500/40 to-emerald-500/40"></div>
                  <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                    <ArrowDown className="w-3 h-3 text-emerald-400 animate-bounce" /> Evidence-linked cause
                  </div>
                  <div className="w-0.5 h-3 bg-gradient-to-b from-emerald-500/40 to-emerald-500/40"></div>
                </div>

                {/* 5. NEW GENERATION / RESULT */}
                <div className="rounded-2xl border border-emerald-500/30 bg-[#0d1117] p-5 shadow-lg relative overflow-hidden">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          NEW GENERATION
                        </span>
                        <span className="font-mono text-xs font-bold text-emerald-400">MEASURED RESULT</span>
                      </div>
                      <span className="text-xs font-mono text-gray-400">Benchmark Evaluated Comparison</span>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      Measured Change
                    </h3>

                    {/* Measured Change Scoreboard */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Before */}
                      <div className="p-4 rounded-xl bg-[#161b22] border border-rose-500/20 space-y-3">
                        <div className="flex items-center justify-between border-b border-[#30363d] pb-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
                            Before (Parent G0)
                          </span>
                          <span className="font-mono text-[10px] text-gray-500">Unmitigated Baseline</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">tool calls</span>
                            <span className="text-lg font-black text-white">3</span>
                            <span className="text-[10px] text-gray-500 block">per task</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">accuracy</span>
                            <span className="text-lg font-black text-white">33.3%</span>
                            <span className="text-[10px] text-gray-500 block">1 / 3 tasks</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">latency</span>
                            <span className="text-lg font-black text-white">3.16s</span>
                            <span className="text-[10px] text-gray-500 block">3,162 ms</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">cost</span>
                            <span className="text-lg font-black text-white">$0.000958</span>
                            <span className="text-[10px] text-gray-500 block">per task</span>
                          </div>
                        </div>
                      </div>

                      {/* After */}
                      <div className="p-4 rounded-xl bg-[#161b22] border border-emerald-500/30 space-y-3">
                        <div className="flex items-center justify-between border-b border-[#30363d] pb-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                            After (Candidate G1)
                          </span>
                          <span className="font-mono text-[10px] text-emerald-400 font-bold">Memory & Gate Active</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-emerald-500/20">
                            <span className="text-[10px] text-gray-500 block uppercase">tool calls</span>
                            <div className="flex items-baseline gap-1.5">
                              <span className="text-lg font-black text-emerald-400">2</span>
                              <span className="text-[10px] font-bold text-emerald-400">-33.3%</span>
                            </div>
                            <span className="text-[10px] text-gray-500 block">lower = improvement</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-emerald-500/20">
                            <span className="text-[10px] text-gray-500 block uppercase">accuracy</span>
                            <div className="flex items-baseline gap-1.5">
                              <span className="text-lg font-black text-emerald-400">50.0%</span>
                              <span className="text-[10px] font-bold text-emerald-400">+16.7%</span>
                            </div>
                            <span className="text-[10px] text-gray-500 block">higher = improvement</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">latency</span>
                            <div className="flex items-baseline gap-1.5">
                              <span className="text-lg font-black text-rose-400">3.82s</span>
                              <span className="text-[10px] font-bold text-rose-400">+20.7%</span>
                            </div>
                            <span className="text-[10px] text-gray-500 block">lower = improvement</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-[#0d1117] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">cost</span>
                            <div className="flex items-baseline gap-1.5">
                              <span className="text-lg font-black text-rose-400">$0.001081</span>
                              <span className="text-[10px] font-bold text-rose-400">+12.8%</span>
                            </div>
                            <span className="text-[10px] text-gray-500 block">lower = improvement</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* VIEW 2: DYNAMIC EXPERIMENT EVIDENCE CHAIN */}
            {causalViewMode === "experiment" && (
              <div className="space-y-4">
                {/* Generation selector if multiple generations */}
                {generations.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pb-2">
                    <span className="text-xs text-gray-400 font-semibold">Inspect Evidence for Generation:</span>
                    {generations.map((g) => (
                      <button
                        key={g.id}
                        onClick={() => handleSelectEvidenceGen(g.id)}
                        className={`px-3 py-1 rounded-lg border font-mono text-xs transition cursor-pointer ${
                          (selectedEvidenceGenId || evidenceData?.generation) === g.id
                            ? "bg-orange-500/20 border-orange-500 text-orange-300 font-bold"
                            : "bg-[#0d1117] border-[#30363d] text-gray-400 hover:text-white"
                        }`}
                      >
                        Gen {g.generation_number} ({g.status})
                      </button>
                    ))}
                  </div>
                )}

                {loadingEvidence ? (
                  <div className="p-8 text-center text-sm text-gray-400 animate-pulse bg-[#0d1117] rounded-xl border border-[#30363d]">
                    Loading generation evidence chain...
                  </div>
                ) : evidenceData ? (
                  <div className="space-y-4">
                    {/* 1. FAILURE */}
                    <div className="rounded-2xl border border-rose-500/30 bg-[#0d1117] p-5 shadow-lg">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              FAILURE
                            </span>
                            <span className="text-xs font-bold text-rose-400">
                              {evidenceData.failures.length > 0 ? `${evidenceData.failures.length} Failure Record(s)` : "No Active Failures"}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-gray-500">
                            Target Gen: {evidenceData.generation || "None"}
                          </span>
                        </div>

                        {evidenceData.failures.length === 0 ? (
                          <div className="text-xs text-gray-400 bg-[#161b22] p-3 rounded-lg border border-[#30363d]">
                            No failures recorded for this generation.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {evidenceData.failures.slice(0, 3).map((f, i) => (
                              <div key={i} className="bg-[#161b22] p-3 rounded-lg border border-rose-500/20 space-y-1">
                                <div className="flex items-center justify-between text-xs font-mono">
                                  <span className="font-bold text-rose-300">{f.failure_type || "UNKNOWN_FAILURE"}</span>
                                  <span className="text-gray-500">{f.task_id || "Task ID N/A"}</span>
                                </div>
                                <p className="text-xs text-gray-300 font-mono">{f.root_cause || "Execution failed"}</p>
                                {f.execution_id && (
                                  <div className="text-[10px] font-mono text-gray-500">Execution: {f.execution_id}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Downward Connector 1 */}
                    <div className="flex flex-col items-center justify-center my-1">
                      <div className="w-0.5 h-3 bg-gradient-to-b from-rose-500/40 to-purple-500/40"></div>
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                        <ArrowDown className="w-3 h-3 text-purple-400 animate-bounce" /> Evidence-linked cause
                      </div>
                      <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500/40 to-purple-500/40"></div>
                    </div>

                    {/* 2. REFLECTION */}
                    <div className="rounded-2xl border border-purple-500/30 bg-[#0d1117] p-5 shadow-lg">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                              REFLECTION
                            </span>
                            <span className="text-xs font-bold text-purple-300">
                              {evidenceData.memory.length > 0 ? `Category: ${evidenceData.memory[0].category}` : "Category: SCHEMA_QUIRK"}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-gray-500">ToolReflectionEngine</span>
                        </div>

                        {evidenceData.memory.length === 0 ? (
                          <div className="text-xs text-gray-400 bg-[#161b22] p-3 rounded-lg border border-[#30363d]">
                            No reflected rules recorded yet. Execute learning loop or evolution to synthesize playbooks.
                          </div>
                        ) : (
                          <div className="bg-[#161b22] p-3 rounded-lg border border-purple-500/20 space-y-1">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 block">Actual Learned Rule from Stored Evidence:</span>
                            <p className="text-xs text-white font-mono italic">
                              &ldquo;{evidenceData.memory[0].learned_rule}&rdquo;
                            </p>
                            {evidenceData.memory[0].evidence && (
                              <div className="text-[11px] text-gray-500 italic">Evidence: {evidenceData.memory[0].evidence}</div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Downward Connector 2 */}
                    <div className="flex flex-col items-center justify-center my-1">
                      <div className="w-0.5 h-3 bg-gradient-to-b from-purple-500/40 to-amber-500/40"></div>
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                        <ArrowDown className="w-3 h-3 text-amber-400 animate-bounce" /> Evidence-linked cause
                      </div>
                      <div className="w-0.5 h-3 bg-gradient-to-b from-amber-500/40 to-amber-500/40"></div>
                    </div>

                    {/* 3. MEMORY */}
                    <div className="rounded-2xl border border-amber-500/30 bg-[#0d1117] p-5 shadow-lg">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              MEMORY
                            </span>
                            <span className="text-xs font-bold text-amber-300">
                              {evidenceData.memory.length} Persistent Playbooks
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-gray-500">ToolMemoryStore</span>
                        </div>

                        {evidenceData.memory.length === 0 ? (
                          <div className="text-xs text-gray-400 bg-[#161b22] p-3 rounded-lg border border-[#30363d]">
                            No memory entries stored in database for this experiment.
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Stored Playbook</span>
                              <span className="font-mono text-xs font-bold text-white mt-1 block">{evidenceData.memory[0].tool_name}</span>
                              <span className="text-[11px] text-gray-400 mt-0.5 block font-mono">{evidenceData.memory[0].pattern_trigger}</span>
                            </div>
                            <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Confidence</span>
                              <span className="font-mono text-xs font-bold text-emerald-400 mt-1 block">{(evidenceData.memory[0].confidence * 100).toFixed(0)}%</span>
                              <span className="text-[11px] text-gray-400 mt-0.5 block">Observed {evidenceData.memory[0].observation_count}x</span>
                            </div>
                            <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 block">Source Execution</span>
                              <span className="font-mono text-xs font-bold text-cyan-400 mt-1 block truncate">
                                {evidenceData.memory[0].execution_id || "Tracked in provenance"}
                              </span>
                              <span className="text-[11px] text-gray-400 mt-0.5 block">Persisted foreign key link</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Downward Connector 3 */}
                    <div className="flex flex-col items-center justify-center my-1">
                      <div className="w-0.5 h-3 bg-gradient-to-b from-amber-500/40 to-blue-500/40"></div>
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                        <ArrowDown className="w-3 h-3 text-blue-400 animate-bounce" /> Evidence-linked cause
                      </div>
                      <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500/40 to-blue-500/40"></div>
                    </div>

                    {/* 4. MUTATION */}
                    <div className="rounded-2xl border border-blue-500/30 bg-[#0d1117] p-5 shadow-lg">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                              MUTATION
                            </span>
                            <span className="text-xs font-bold text-blue-400">
                              {evidenceData.mutations.length > 0 ? evidenceData.mutations[0].mutation_type : "Baseline (No mutation)"}
                            </span>
                          </div>
                          {evidenceData.mutations.length > 0 && (
                            <span className="text-xs font-mono text-gray-400">
                              Target: <strong className="text-white font-mono">{evidenceData.mutations[0].target}</strong>
                            </span>
                          )}
                        </div>

                        {evidenceData.mutations.length === 0 ? (
                          <div className="text-xs text-gray-400 bg-[#161b22] p-3 rounded-lg border border-[#30363d]">
                            Baseline generation G0: no mutations applied. Evolve agent to synthesize next candidate generation.
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">Reason:</span>
                              <p className="text-xs text-gray-200 font-mono">{evidenceData.mutations[0].reason}</p>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              <div className="p-3 rounded-xl bg-[#161b22] border border-rose-500/20 space-y-1">
                                <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block font-mono">Before</span>
                                <pre className="text-[11px] text-gray-300 font-mono overflow-x-auto">
                                  {JSON.stringify(evidenceData.mutations[0].before, null, 2)}
                                </pre>
                              </div>

                              <div className="p-3 rounded-xl bg-[#161b22] border border-emerald-500/20 space-y-1">
                                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block font-mono">After</span>
                                <pre className="text-[11px] text-gray-300 font-mono overflow-x-auto">
                                  {JSON.stringify(evidenceData.mutations[0].after, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Downward Connector 4 */}
                    <div className="flex flex-col items-center justify-center my-1">
                      <div className="w-0.5 h-3 bg-gradient-to-b from-blue-500/40 to-emerald-500/40"></div>
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#161b22] border border-[#30363d] text-[10px] font-mono text-gray-400 font-bold tracking-wide">
                        <ArrowDown className="w-3 h-3 text-emerald-400 animate-bounce" /> Evidence-linked cause
                      </div>
                      <div className="w-0.5 h-3 bg-gradient-to-b from-emerald-500/40 to-emerald-500/40"></div>
                    </div>

                    {/* 5. NEW GENERATION / RESULT */}
                    <div className="rounded-2xl border border-emerald-500/30 bg-[#0d1117] p-5 shadow-lg">
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              NEW GENERATION
                            </span>
                            <span className="font-mono text-xs font-bold text-emerald-400">MEASURED RESULT</span>
                          </div>
                          <span className="text-xs font-mono text-gray-400">
                            Decision: <strong className="text-white font-bold">{evidenceData.decision?.status || "COMPLETED"}</strong>
                          </span>
                        </div>

                        <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block mb-1">Decision Rationale:</span>
                          <p className="text-xs text-emerald-300 font-mono">
                            {evidenceData.decision?.reason || "Baseline generation evaluated against benchmark suite."}
                          </p>
                        </div>

                        {/* Metrics Breakdown */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                          <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">Accuracy</span>
                            <span className="text-lg font-black text-white">
                              {evidenceData.metrics?.accuracy !== undefined ? `${(evidenceData.metrics.accuracy * 100).toFixed(1)}%` : "Not available"}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">Reliability</span>
                            <span className="text-lg font-black text-cyan-400">
                              {evidenceData.metrics?.reliability !== undefined ? `${(evidenceData.metrics.reliability * 100).toFixed(1)}%` : "Not available"}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">Cost / task</span>
                            <span className="text-lg font-black text-amber-400">
                              {evidenceData.metrics?.avg_cost_per_task !== undefined ? `$${evidenceData.metrics.avg_cost_per_task.toFixed(4)}` : "Not available"}
                            </span>
                          </div>
                          <div className="p-3 rounded-xl bg-[#161b22] border border-[#30363d]">
                            <span className="text-[10px] text-gray-500 block uppercase">Latency / task</span>
                            <span className="text-lg font-black text-purple-400">
                              {evidenceData.metrics?.avg_latency_ms !== undefined ? `${(evidenceData.metrics.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-sm text-gray-500 bg-[#0d1117] rounded-xl border border-[#30363d]">
                    No evidence data available.
                  </div>
                )}
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
