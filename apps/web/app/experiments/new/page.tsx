"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../../lib/api";
import { ArrowLeft, Sparkles, Check, Flame } from "lucide-react";
import Link from "next/link";

const AVAILABLE_TOOLS = [
  { id: "repository", name: "Repository Inspector", desc: "List, explore, and read repo files sandboxed to workspace" },
  { id: "file_editor", name: "File Editor", desc: "Create, patch, and replace code files with diff tracing" },
  { id: "shell", name: "Restricted Shell", desc: "Execute build and analysis commands inside workspace" },
  { id: "test_runner", name: "Automated Test Runner", desc: "Execute pytest suites and extract structured failure diagnostics" },
  { id: "search", name: "Code Search", desc: "Grep and regex search codebase for symbol references" },
];

export default function NewExperimentPage() {
  const router = useRouter();
  const [name, setName] = useState("GitHub Issue Resolver");
  const [goal, setGoal] = useState("Build an agent capable of inspecting repositories, resolving software engineering issues, and verifying solutions with automated tests.");
  const [benchmarkId, setBenchmarkId] = useState("software_engineering");
  const [selectedTools, setSelectedTools] = useState<string[]>([
    "repository",
    "file_editor",
    "shell",
    "test_runner",
    "search",
  ]);
  const [maxGenerations, setMaxGenerations] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleTool = (id: string) => {
    if (selectedTools.includes(id)) {
      if (selectedTools.length > 1) {
        setSelectedTools(selectedTools.filter((t) => t !== id));
      }
    } else {
      setSelectedTools([...selectedTools, id]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const exp = await api.createExperiment({
        name,
        goal,
        benchmark_id: benchmarkId,
        tools: selectedTools,
        max_generations: maxGenerations,
      });
      router.push(`/experiments/${exp.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create experiment");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-8 shadow-xl">
        <div className="flex items-center gap-3 pb-6 border-b border-[#30363d]">
          <div className="w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Create Evolution Experiment</h1>
            <p className="text-xs text-gray-400">Define agent goal, capabilities, and target benchmark</p>
          </div>
        </div>

        {error && (
          <div className="mt-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
              Experiment Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-white focus:outline-none focus:border-orange-500 text-sm font-medium"
              placeholder="e.g. GitHub Issue Resolver"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
              High-Level Agent Goal
            </label>
            <textarea
              required
              rows={3}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-white focus:outline-none focus:border-orange-500 text-sm"
              placeholder="Describe the problem domain and expected operational behavior..."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
              Benchmark Target
            </label>
            <select
              value={benchmarkId}
              onChange={(e) => setBenchmarkId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[#0d1117] border border-[#30363d] text-white focus:outline-none focus:border-orange-500 text-sm font-mono"
            >
              <option value="software_engineering">Software Engineering v1 (10 Tasks, Local Repos, Deterministic Tests)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
              Available Tools
            </label>
            <div className="grid grid-cols-1 gap-2.5">
              {AVAILABLE_TOOLS.map((tool) => {
                const isSelected = selectedTools.includes(tool.id);
                return (
                  <div
                    key={tool.id}
                    onClick={() => toggleTool(tool.id)}
                    className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? "bg-[#1c2128] border-orange-500/40 text-white shadow-sm"
                        : "bg-[#0d1117] border-[#30363d] text-gray-400 hover:border-gray-600"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center mt-0.5 transition-colors ${
                        isSelected ? "bg-orange-500 text-white" : "border border-gray-600"
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold">{tool.name}</div>
                      <div className="text-xs text-gray-500">{tool.desc}</div>
                    </div>
                    <span className="font-mono text-[11px] text-gray-400 bg-[#12151d] px-2 py-0.5 rounded border border-[#30363d]">
                      {tool.id}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
              Max Generations Cap
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={maxGenerations}
              onChange={(e) => setMaxGenerations(parseInt(e.target.value) || 5)}
              className="w-32 px-4 py-2 rounded-lg bg-[#0d1117] border border-[#30363d] text-white text-sm font-mono"
            />
          </div>

          <div className="pt-4 border-t border-[#30363d] flex items-center justify-end gap-3">
            <Link
              href="/"
              className="px-5 py-2.5 rounded-lg border border-[#30363d] text-gray-300 hover:text-white text-sm font-semibold transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold transition-all disabled:opacity-50 shadow-lg shadow-orange-500/25"
            >
              <Sparkles className="w-4 h-4" />
              {loading ? "Creating..." : "Create Experiment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
