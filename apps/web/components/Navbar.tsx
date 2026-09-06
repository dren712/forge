"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Flame, Plus, ShieldCheck, Activity, Cpu, X, RefreshCw, Terminal, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";

export default function Navbar() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [aoModalOpen, setAoModalOpen] = useState(false);
  const [aoStatus, setAoStatus] = useState<any>(null);
  const [aoDoctor, setAoDoctor] = useState<any>(null);
  const [loadingAO, setLoadingAO] = useState(false);

  const fetchAOData = async () => {
    setLoadingAO(true);
    try {
      const [status, doctor] = await Promise.all([
        api.getAOStatus().catch((e) => ({ running: false, error: e.message })),
        api.getAODoctor().catch((e) => ({ available: false, error: e.message })),
      ]);
      setAoStatus(status);
      setAoDoctor(doctor);
    } catch (e: any) {
      setAoStatus({ running: false, error: e.message });
    } finally {
      setLoadingAO(false);
    }
  };

  useEffect(() => {
    api.getHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));

    // Initial background check of AO status
    api.getAOStatus()
      .then((s) => setAoStatus(s))
      .catch(() => setAoStatus({ running: false }));
  }, []);

  const handleOpenAO = () => {
    setAoModalOpen(true);
    fetchAOData();
  };

  return (
    <header className="border-b border-[#212631] bg-[#12151d]/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-amber-600 via-orange-500 to-rose-500 flex items-center justify-center shadow-lg shadow-orange-500/20 group-hover:scale-105 transition-transform">
              <Flame className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-black tracking-wider text-white">FORGE</span>
              <p className="text-[11px] font-medium text-gray-400 tracking-tight">Agents don&apos;t just run. They evolve.</p>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-gray-300 ml-4">
            <Link href="/" className="px-3 py-1.5 rounded-md hover:text-white hover:bg-[#212631] transition-colors">
              Experiments
            </Link>
            <span className="text-gray-600 px-1">•</span>
            <span className="text-xs px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 font-mono">
              Inference: TensorMux (GLM-4.7-Flash)
            </span>
          </nav>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          {/* AO Development Orchestration Status Button (FORGE S8-G/H/I Task C) */}
          <button
            onClick={handleOpenAO}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#1c2128] hover:bg-[#262c36] border border-[#30363d] text-xs transition cursor-pointer font-mono"
            title="Inspect Agent Orchestrator (AO) developer harness status"
          >
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-gray-300 hidden sm:inline">AO Dev Orchestration</span>
            <span className="text-gray-300 sm:hidden">AO</span>
            {aoStatus?.running ? (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-zinc-500" />
            )}
          </button>

          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#1c2128] border border-[#30363d] text-xs">
            <span className={`w-2 h-2 rounded-full ${online ? "bg-emerald-400 animate-pulse" : "bg-rose-400"}`} />
            <span className="text-gray-300 font-mono">{online ? "API Online" : "API Offline"}</span>
          </div>

          <Link
            href="/experiments/new"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white text-sm font-semibold shadow-md shadow-orange-500/20 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Experiment</span>
          </Link>
        </div>
      </div>

      {/* AO Development Orchestration Modal / Panel */}
      {aoModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            {/* Header */}
            <div className="px-6 py-4 border-b border-[#30363d] flex items-center justify-between bg-[#12151d]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-wide">
                    AO Development Orchestration
                  </h3>
                  <p className="text-[11px] text-gray-400 font-mono">
                    Developer process harness • <span className="text-amber-400 font-semibold">NOT FORGE runtime</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={fetchAOData}
                  disabled={loadingAO}
                  className="p-1.5 rounded-lg bg-[#21262d] hover:bg-[#30363d] text-gray-300 transition cursor-pointer disabled:opacity-50"
                  title="Refresh AO status"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingAO ? "animate-spin text-purple-400" : ""}`} />
                </button>
                <button
                  onClick={() => setAoModalOpen(false)}
                  className="p-1.5 rounded-lg bg-[#21262d] hover:bg-[#30363d] text-gray-300 transition cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 space-y-5 overflow-y-auto text-xs font-mono">
              {/* Architecture Boundary Callout */}
              <div className="p-3.5 rounded-xl bg-[#0d1117] border border-purple-500/30 text-gray-300 space-y-1">
                <div className="font-bold text-purple-300 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-purple-400" />
                  Development Process Isolation Notice
                </div>
                <p className="text-[11px] text-gray-400">
                  Agent Orchestrator (AO) represents the meta-agent development orchestration harness used during FORGE's design.
                  FORGE runtime execution, benchmark evaluations, mutations, and cryptographic provenance operate independently.
                </p>
              </div>

              {/* Status Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase block">Daemon Status</span>
                  <div className="font-bold text-xs">
                    {aoStatus?.running ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Running
                      </span>
                    ) : (
                      <span className="text-gray-400 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Standby
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase block">Port / PID</span>
                  <div className="font-bold text-xs text-white">
                    {aoStatus?.port ? `Port ${aoStatus.port}` : (aoStatus?.pid ? `PID ${aoStatus.pid}` : "None")}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase block">AO Binary</span>
                  <div className="font-bold text-xs text-cyan-400">
                    {aoDoctor?.available ? "Installed" : "Not Found"}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#0d1117] border border-[#30363d] space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase block">SQLite Store</span>
                  <div className="font-bold text-xs">
                    {aoDoctor?.sqlite_ok ? (
                      <span className="text-emerald-400">Ready</span>
                    ) : (
                      <span className="text-gray-400">Unchecked</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Real Doctor Output from Backend */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-gray-400 text-[11px]">
                  <span>Live CLI Diagnostics (`ao doctor` output)</span>
                  <span className="text-[10px] text-gray-500">Source: GET /api/ao/doctor</span>
                </div>
                <pre className="p-3.5 rounded-xl bg-[#0d1117] border border-[#30363d] text-gray-300 text-[11px] leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap">
                  {aoDoctor?.output || aoStatus?.error || (loadingAO ? "Executing diagnostics query..." : "No diagnostic logs available.")}
                </pre>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-[#30363d] bg-[#12151d] flex items-center justify-between text-[11px] text-gray-500 font-mono">
              <span>Truthful backend data • Zero fabricated sessions or worker counts</span>
              <button
                onClick={() => setAoModalOpen(false)}
                className="px-3 py-1 rounded-lg bg-[#21262d] hover:bg-[#30363d] text-gray-300 text-xs transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
