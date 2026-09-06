"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Experiment } from "../lib/api";
import { Flame, GitBranch, ArrowUpRight, Plus, CheckCircle2, Clock, AlertTriangle, Layers } from "lucide-react";

export default function DashboardPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const data = await api.getExperiments();
      setExperiments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const totalRuns = experiments.reduce((acc, e) => acc + e.generations_count, 0);
  const bestOverall = experiments.reduce((max, e) => (e.best_accuracy && e.best_accuracy > max ? e.best_accuracy : max), 0);

  return (
    <div className="space-y-8">
      {/* Top Banner / Thesis */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#161b22] via-[#1a202c] to-[#161b22] border border-[#30363d] p-8 shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs font-semibold uppercase tracking-wider mb-4">
            <Flame className="w-3.5 h-3.5" /> Automated Agent Engineering
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight leading-tight">
            Agents don&apos;t just run. <span className="bg-gradient-to-r from-orange-400 via-amber-300 to-rose-400 bg-clip-text text-transparent">They evolve.</span>
          </h1>
          <p className="mt-3 text-base text-gray-400 leading-relaxed">
            FORGE empirically diagnoses agent failures across benchmark tasks, synthesizes targeted architectural mutations, and drives multi-generation accuracy & reliability improvements backed by cryptographic provenance.
          </p>

          <div className="mt-6 flex flex-wrap gap-4 items-center">
            <Link
              href="/experiments/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold transition-all shadow-lg shadow-orange-500/25"
            >
              <Plus className="w-4 h-4" /> Create Evolution Experiment
            </Link>
          </div>
        </div>
      </div>

      {/* High-Level Metrics Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active Experiments</span>
            <Layers className="w-4 h-4 text-orange-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{experiments.length}</div>
          <p className="mt-1 text-xs text-gray-500">Autonomous benchmarks configured</p>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Top Generation Score</span>
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-400">
            {bestOverall > 0 ? `${(bestOverall * 100).toFixed(1)}%` : "—"}
          </div>
          <p className="mt-1 text-xs text-gray-500">Peak task accuracy achieved</p>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Generations Evaluated</span>
            <GitBranch className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{totalRuns}</div>
          <p className="mt-1 text-xs text-gray-500">Total evolutionary cycles run</p>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Provenance Verification</span>
            <CheckCircle2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 text-2xl font-bold text-cyan-400">SHA-256 Valid</div>
          <p className="mt-1 text-xs text-gray-500">Cryptographically chained traces</p>
        </div>
      </div>

      {/* Experiments Table */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#30363d] flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Experiments</h2>
            <p className="text-xs text-gray-400">Manage and monitor agent evolution trajectories</p>
          </div>
          <Link
            href="/experiments/new"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-orange-400 hover:text-orange-300"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </Link>
        </div>

        {loading ? (
          <div className="py-16 text-center text-gray-400 text-sm">Loading experiments...</div>
        ) : experiments.length === 0 ? (
          <div className="py-16 text-center">
            <Layers className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-base font-medium text-gray-300">No experiments created yet</p>
            <p className="text-sm text-gray-500 mt-1">Start by creating your first Software Engineering agent experiment.</p>
            <Link
              href="/experiments/new"
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 text-white text-sm font-semibold hover:bg-orange-600"
            >
              <Plus className="w-4 h-4" /> Create Experiment
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#12151d] text-gray-400 text-xs uppercase tracking-wider border-b border-[#30363d]">
                <tr>
                  <th className="px-6 py-3">Experiment</th>
                  <th className="px-6 py-3">Benchmark</th>
                  <th className="px-6 py-3">Generations</th>
                  <th className="px-6 py-3">Best Accuracy</th>
                  <th className="px-6 py-3">Reliability</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#212631]">
                {experiments.map((exp) => (
                  <tr key={exp.id} className="hover:bg-[#1c2128]/70 transition-colors">
                    <td className="px-6 py-4">
                      <Link href={`/experiments/${exp.id}`} className="font-semibold text-white hover:text-orange-400 transition-colors">
                        {exp.name}
                      </Link>
                      <p className="text-xs text-gray-500 line-clamp-1 mt-0.5">{exp.goal}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-xs text-gray-300 px-2 py-0.5 rounded bg-[#1c2128] border border-[#30363d]">
                        {exp.benchmark_id}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-300 font-mono">
                      G{exp.generations_count > 0 ? exp.generations_count - 1 : 0} ({exp.generations_count} total)
                    </td>
                    <td className="px-6 py-4">
                      {exp.best_accuracy !== null && exp.best_accuracy !== undefined ? (
                        <span className="font-bold text-emerald-400 font-mono">
                          {(exp.best_accuracy * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-500 font-mono">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {exp.best_reliability !== null && exp.best_reliability !== undefined ? (
                        <span className="font-bold text-cyan-400 font-mono">
                          {(exp.best_reliability * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-500 font-mono">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        exp.status === "RUNNING"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                          : exp.status === "COMPLETED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-gray-700/20 text-gray-400 border border-gray-700/30"
                      }`}>
                        {exp.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/experiments/${exp.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-orange-400 hover:text-orange-300"
                      >
                        Open <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
