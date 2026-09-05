"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Flame, Plus, ShieldCheck, Activity } from "lucide-react";
import { api } from "../lib/api";

export default function Navbar() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

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

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#1c2128] border border-[#30363d] text-xs">
            <span className={`w-2 h-2 rounded-full ${online ? "bg-emerald-400 animate-pulse" : "bg-rose-400"}`} />
            <span className="text-gray-300 font-mono">{online ? "API Online" : "API Offline"}</span>
          </div>

          <Link
            href="/experiments/new"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white text-sm font-semibold shadow-md shadow-orange-500/20 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Experiment</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
