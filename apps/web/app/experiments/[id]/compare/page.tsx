"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Generation } from "../../../../lib/api";
import { ArrowLeft, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";

export default function CompareGenerationsPage() {
  const params = useParams();
  const expId = params?.id as string;

  const [generations, setGenerations] = useState<Generation[]>([]);
  const [genAId, setGenAId] = useState<string>("");
  const [genBId, setGenBId] = useState<string>("");

  useEffect(() => {
    if (!expId) return;
    api.getGenerations(expId).then((gens) => {
      setGenerations(gens);
      if (gens.length >= 2) {
        setGenAId(gens[0].id);
        setGenBId(gens[gens.length - 1].id);
      }
    });
  }, [expId]);

  const genA = generations.find((g) => g.id === genAId) || generations[0];
  const genB = generations.find((g) => g.id === genBId) || generations[generations.length - 1];

  const mA = genA?.metrics;
  const mB = genB?.metrics;

  const calcDelta = (valA?: number, valB?: number, isCostOrLat = false) => {
    if (valA === undefined || valB === undefined || valA === null || valB === null) return null;
    const diff = valB - valA;
    const pct = valA !== 0 ? (diff / valA) * 100 : 0;
    const improved = isCostOrLat ? diff < 0 : diff > 0;
    return { diff, pct, improved };
  };

  const accDelta = calcDelta(mA?.accuracy, mB?.accuracy);
  const relDelta = calcDelta(mA?.reliability, mB?.reliability);
  const costDelta = calcDelta(mA?.avg_cost_per_task, mB?.avg_cost_per_task, true);
  const latDelta = calcDelta(mA?.avg_latency_ms, mB?.avg_latency_ms, true);
  const compDelta = calcDelta(mA?.composite_score, mB?.composite_score);

  return (
    <div className="space-y-6">
      <Link
        href={`/experiments/${expId}`}
        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Experiment
      </Link>

      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6 shadow-xl">
        <h1 className="text-2xl font-bold text-white tracking-tight">Generational Comparison</h1>
        <p className="text-xs text-gray-400 mt-1">Direct empirical performance diff between agent generations</p>

        {/* Generation Selectors */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <label className="text-xs text-gray-400 block mb-1.5 font-semibold uppercase">Baseline Generation (A)</label>
            <select
              value={genAId}
              onChange={(e) => setGenAId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none"
            >
              {generations.map((g) => (
                <option key={g.id} value={g.id}>
                  Generation {g.generation_number} ({g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"})
                </option>
              ))}
            </select>
          </div>

          <div className="p-4 rounded-xl bg-[#0d1117] border border-[#30363d]">
            <label className="text-xs text-gray-400 block mb-1.5 font-semibold uppercase">Candidate / Evolved Generation (B)</label>
            <select
              value={genBId}
              onChange={(e) => setGenBId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-white font-mono text-sm focus:outline-none"
            >
              {generations.map((g) => (
                <option key={g.id} value={g.id}>
                  Generation {g.generation_number} ({g.metrics ? `${(g.metrics.accuracy * 100).toFixed(1)}%` : "no metrics"})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Side-by-side Table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left text-sm font-mono">
            <thead className="bg-[#12151d] text-gray-400 text-xs uppercase tracking-wider border-b border-[#30363d]">
              <tr>
                <th className="px-6 py-3 font-sans">Metric</th>
                <th className="px-6 py-3">Gen {genA?.generation_number}</th>
                <th className="px-6 py-3">Gen {genB?.generation_number}</th>
                <th className="px-6 py-3">Delta / Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#212631]">
              <tr>
                <td className="px-6 py-4 font-sans font-semibold text-white">Accuracy</td>
                <td className="px-6 py-4 text-gray-300">{mA ? `${(mA.accuracy * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-6 py-4 font-bold text-emerald-400">{mB ? `${(mB.accuracy * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-6 py-4">
                  {accDelta && (
                    <span className={`inline-flex items-center gap-1 font-bold ${accDelta.improved ? "text-emerald-400" : "text-rose-400"}`}>
                      {accDelta.diff >= 0 ? `+${(accDelta.diff * 100).toFixed(1)}%` : `${(accDelta.diff * 100).toFixed(1)}%`}
                    </span>
                  )}
                </td>
              </tr>

              <tr>
                <td className="px-6 py-4 font-sans font-semibold text-white">Reliability</td>
                <td className="px-6 py-4 text-gray-300">{mA ? `${(mA.reliability * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-6 py-4 font-bold text-cyan-400">{mB ? `${(mB.reliability * 100).toFixed(1)}%` : "—"}</td>
                <td className="px-6 py-4">
                  {relDelta && (
                    <span className={`inline-flex items-center gap-1 font-bold ${relDelta.improved ? "text-cyan-400" : "text-rose-400"}`}>
                      {relDelta.diff >= 0 ? `+${(relDelta.diff * 100).toFixed(1)}%` : `${(relDelta.diff * 100).toFixed(1)}%`}
                    </span>
                  )}
                </td>
              </tr>

              <tr>
                <td className="px-6 py-4 font-sans font-semibold text-white">Cost / task</td>
                <td className="px-6 py-4 text-gray-300">{mA ? `$${mA.avg_cost_per_task.toFixed(4)}` : "—"}</td>
                <td className="px-6 py-4 font-bold text-amber-400">{mB ? `$${mB.avg_cost_per_task.toFixed(4)}` : "—"}</td>
                <td className="px-6 py-4">
                  {costDelta && (
                    <span className={`inline-flex items-center gap-1 font-bold ${costDelta.improved ? "text-emerald-400" : "text-amber-400"}`}>
                      {costDelta.pct >= 0 ? `+${costDelta.pct.toFixed(1)}%` : `${costDelta.pct.toFixed(1)}%`}
                    </span>
                  )}
                </td>
              </tr>

              <tr>
                <td className="px-6 py-4 font-sans font-semibold text-white">Latency / task</td>
                <td className="px-6 py-4 text-gray-300">{mA ? `${(mA.avg_latency_ms / 1000).toFixed(1)}s` : "—"}</td>
                <td className="px-6 py-4 font-bold text-purple-400">{mB ? `${(mB.avg_latency_ms / 1000).toFixed(1)}s` : "—"}</td>
                <td className="px-6 py-4">
                  {latDelta && (
                    <span className={`inline-flex items-center gap-1 font-bold ${latDelta.improved ? "text-emerald-400" : "text-purple-400"}`}>
                      {latDelta.pct >= 0 ? `+${latDelta.pct.toFixed(1)}%` : `${latDelta.pct.toFixed(1)}%`}
                    </span>
                  )}
                </td>
              </tr>

              <tr>
                <td className="px-6 py-4 font-sans font-semibold text-white">Composite Score</td>
                <td className="px-6 py-4 text-gray-300">{mA ? mA.composite_score.toFixed(3) : "—"}</td>
                <td className="px-6 py-4 font-bold text-orange-400">{mB ? mB.composite_score.toFixed(3) : "—"}</td>
                <td className="px-6 py-4">
                  {compDelta && (
                    <span className={`inline-flex items-center gap-1 font-bold ${compDelta.improved ? "text-emerald-400" : "text-rose-400"}`}>
                      {compDelta.diff >= 0 ? `+${compDelta.diff.toFixed(3)}` : `${compDelta.diff.toFixed(3)}`}
                    </span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
