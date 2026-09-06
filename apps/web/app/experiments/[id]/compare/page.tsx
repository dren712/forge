"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Generation } from "../../../../lib/api";
import { ArrowLeft, TrendingUp, TrendingDown, ArrowRight, GitBranch, CheckCircle2, XCircle, AlertCircle, Minus } from "lucide-react";

interface DeltaMetric {
  diff: number;
  pct: number;
  status: "improved" | "regressed" | "unchanged";
  text: string;
}

export default function CompareGenerationsPage() {
  const params = useParams();
  const expId = params?.id as string;

  const [generations, setGenerations] = useState<Generation[]>([]);
  const [genAId, setGenAId] = useState<string>("");
  const [genBId, setGenBId] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!expId) return;
    api.getGenerations(expId)
      .then((gens) => {
        setGenerations(gens);
        if (gens.length >= 2) {
          setGenAId(gens[0].id);
          setGenBId(gens[gens.length - 1].id);
        } else if (gens.length === 1) {
          setGenAId(gens[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [expId]);

  const genA = generations.find((g) => g.id === genAId) || generations[0];
  const genB = generations.find((g) => g.id === genBId) || (generations.length > 1 ? generations[generations.length - 1] : null);

  const mA = genA?.metrics;
  const mB = genB?.metrics;

  const calcDelta = (
    valA?: number | null,
    valB?: number | null,
    lowerIsBetter = false,
    unit = ""
  ): DeltaMetric | null => {
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

  // Accuracy (higher = improvement)
  const accDelta = calcDelta(mA?.accuracy, mB?.accuracy, false, "%");
  // Reliability (higher = improvement)
  const relDelta = calcDelta(mA?.reliability, mB?.reliability, false, "%");
  // Cost (lower = improvement)
  const costDelta = calcDelta(mA?.avg_cost_per_task, mB?.avg_cost_per_task, true, " USD");
  // Latency (lower = improvement)
  const latDelta = calcDelta(
    mA?.avg_latency_ms ? mA.avg_latency_ms / 1000 : null,
    mB?.avg_latency_ms ? mB.avg_latency_ms / 1000 : null,
    true,
    "s"
  );
  // Tool Calls / task (lower = improvement)
  const callsPerTaskA = mA?.total_tasks && mA.total_tasks > 0 ? mA.total_tool_calls / mA.total_tasks : null;
  const callsPerTaskB = mB?.total_tasks && mB.total_tasks > 0 ? mB.total_tool_calls / mB.total_tasks : null;
  const toolsDelta = calcDelta(callsPerTaskA, callsPerTaskB, true, " calls");
  // Composite score (higher = improvement)
  const compDelta = calcDelta(mA?.composite_score, mB?.composite_score, false);

  if (loading) {
    return <div className="py-20 text-center text-gray-400">Loading generation data...</div>;
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/experiments/${expId}`}
        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Experiment
      </Link>

      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-orange-400 block">
            Generational Performance Diff
          </span>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Generation Comparison
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Empirical delta comparison between agent generations based on benchmark evaluation metrics.
          </p>
        </div>

        {/* Empty State when generations <= 1 */}
        {generations.length <= 1 ? (
          <div className="p-12 text-center rounded-2xl bg-[#0d1117] border border-dashed border-[#30363d] space-y-3">
            <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 mx-auto">
              <GitBranch className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white">
              At Least Two Generations Required
            </h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto leading-relaxed">
              {generations.length === 0
                ? "No generations generated yet. Generate G0 and run benchmark tasks to begin."
                : `Only Generation 0 has been evaluated. At least two generations are needed to compute mathematical deltas. Return to the Command Center and click 'Evolve Agent' to produce candidate Generation 1.`}
            </p>
            <Link
              href={`/experiments/${expId}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold shadow-md shadow-orange-500/20 transition-all mt-2"
            >
              Back to Command Center
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Generation Selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2">
                <label className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">
                  Baseline Generation (A)
                </label>
                <select
                  value={genAId}
                  onChange={(e) => setGenAId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none"
                >
                  {generations.map((g) => (
                    <option key={g.id} value={g.id}>
                      Generation {g.generation_number} ({g.status}) — Accuracy: {g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-gray-500 font-mono truncate">ID: {genA?.id}</p>
              </div>

              <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-2">
                <label className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">
                  Candidate / Target Generation (B)
                </label>
                <select
                  value={genBId}
                  onChange={(e) => setGenBId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none"
                >
                  {generations.map((g) => (
                    <option key={g.id} value={g.id}>
                      Generation {g.generation_number} ({g.status}) — Accuracy: {g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-gray-500 font-mono truncate">ID: {genB?.id}</p>
              </div>
            </div>

            {/* Metrics Comparison Table */}
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
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {mA ? `${(mA.accuracy * 100).toFixed(1)}%` : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-emerald-400">
                      {mB ? `${(mB.accuracy * 100).toFixed(1)}%` : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {accDelta ? (
                        <span className={`font-bold ${
                          accDelta.status === "improved"
                            ? "text-emerald-400"
                            : accDelta.status === "regressed"
                            ? "text-rose-400"
                            : "text-gray-400"
                        }`}>
                          {accDelta.diff >= 0 ? `+${(accDelta.diff * 100).toFixed(1)}%` : `${(accDelta.diff * 100).toFixed(1)}%`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {accDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          accDelta.status === "improved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : accDelta.status === "regressed"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {accDelta.status === "improved" ? "Improved" : accDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Reliability */}
                  <tr className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-6 py-4 font-sans font-semibold text-white">Reliability</td>
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {mA ? `${(mA.reliability * 100).toFixed(1)}%` : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-cyan-400">
                      {mB ? `${(mB.reliability * 100).toFixed(1)}%` : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {relDelta ? (
                        <span className={`font-bold ${
                          relDelta.status === "improved"
                            ? "text-cyan-400"
                            : relDelta.status === "regressed"
                            ? "text-rose-400"
                            : "text-gray-400"
                        }`}>
                          {relDelta.diff >= 0 ? `+${(relDelta.diff * 100).toFixed(1)}%` : `${(relDelta.diff * 100).toFixed(1)}%`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {relDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          relDelta.status === "improved"
                            ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                            : relDelta.status === "regressed"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {relDelta.status === "improved" ? "Improved" : relDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Cost / task */}
                  <tr className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-6 py-4 font-sans font-semibold text-white">Cost / task</td>
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {mA ? `$${mA.avg_cost_per_task.toFixed(4)}` : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-amber-400">
                      {mB ? `$${mB.avg_cost_per_task.toFixed(4)}` : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {costDelta ? (
                        <span className={`font-bold ${
                          costDelta.status === "improved"
                            ? "text-emerald-400"
                            : costDelta.status === "regressed"
                            ? "text-amber-400"
                            : "text-gray-400"
                        }`}>
                          {costDelta.diff >= 0 ? `+$${costDelta.diff.toFixed(4)}` : `-$${Math.abs(costDelta.diff).toFixed(4)}`}
                          {costDelta.pct !== 0 && ` (${costDelta.pct > 0 ? `+${costDelta.pct.toFixed(1)}%` : `${costDelta.pct.toFixed(1)}%`})`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {costDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          costDelta.status === "improved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : costDelta.status === "regressed"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {costDelta.status === "improved" ? "Improved" : costDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Latency / task */}
                  <tr className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-6 py-4 font-sans font-semibold text-white">Latency / task</td>
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {mA ? `${(mA.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-purple-400">
                      {mB ? `${(mB.avg_latency_ms / 1000).toFixed(2)}s` : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {latDelta ? (
                        <span className={`font-bold ${
                          latDelta.status === "improved"
                            ? "text-emerald-400"
                            : latDelta.status === "regressed"
                            ? "text-purple-400"
                            : "text-gray-400"
                        }`}>
                          {latDelta.diff >= 0 ? `+${latDelta.diff.toFixed(2)}s` : `${latDelta.diff.toFixed(2)}s`}
                          {latDelta.pct !== 0 && ` (${latDelta.pct > 0 ? `+${latDelta.pct.toFixed(1)}%` : `${latDelta.pct.toFixed(1)}%`})`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {latDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          latDelta.status === "improved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : latDelta.status === "regressed"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {latDelta.status === "improved" ? "Improved" : latDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Tool calls / task */}
                  <tr className="hover:bg-[#161b22]/50 transition-colors">
                    <td className="px-6 py-4 font-sans font-semibold text-white">Tool calls / task</td>
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Lower is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {callsPerTaskA !== null ? callsPerTaskA.toFixed(1) : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-white">
                      {callsPerTaskB !== null ? callsPerTaskB.toFixed(1) : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {toolsDelta ? (
                        <span className={`font-bold ${
                          toolsDelta.status === "improved"
                            ? "text-emerald-400"
                            : toolsDelta.status === "regressed"
                            ? "text-rose-400"
                            : "text-gray-400"
                        }`}>
                          {toolsDelta.diff >= 0 ? `+${toolsDelta.diff.toFixed(1)}` : `${toolsDelta.diff.toFixed(1)}`}
                          {toolsDelta.pct !== 0 && ` (${toolsDelta.pct > 0 ? `+${toolsDelta.pct.toFixed(1)}%` : `${toolsDelta.pct.toFixed(1)}%`})`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {toolsDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          toolsDelta.status === "improved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : toolsDelta.status === "regressed"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {toolsDelta.status === "improved" ? "Improved" : toolsDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Composite score */}
                  <tr className="hover:bg-[#161b22]/50 transition-colors bg-[#12151d]/40">
                    <td className="px-6 py-4 font-sans font-semibold text-white">Composite Score</td>
                    <td className="px-6 py-4 font-sans text-xs text-gray-500">Higher is better</td>
                    <td className="px-6 py-4 text-gray-300">
                      {mA ? mA.composite_score.toFixed(3) : "Not available"}
                    </td>
                    <td className="px-6 py-4 font-bold text-orange-400">
                      {mB ? mB.composite_score.toFixed(3) : "Not available"}
                    </td>
                    <td className="px-6 py-4">
                      {compDelta ? (
                        <span className={`font-bold ${
                          compDelta.status === "improved"
                            ? "text-emerald-400"
                            : compDelta.status === "regressed"
                            ? "text-rose-400"
                            : "text-gray-400"
                        }`}>
                          {compDelta.diff >= 0 ? `+${compDelta.diff.toFixed(3)}` : `${compDelta.diff.toFixed(3)}`}
                        </span>
                      ) : (
                        <span className="text-gray-500">Not available</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {compDelta && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-sans font-semibold ${
                          compDelta.status === "improved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : compDelta.status === "regressed"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                        }`}>
                          {compDelta.status === "improved" ? "Improved" : compDelta.status === "regressed" ? "Regressed" : "Unchanged"}
                        </span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
