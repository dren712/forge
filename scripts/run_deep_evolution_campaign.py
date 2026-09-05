#!/usr/bin/env python3
"""
FORGE — Deep Evolution & Token Burn Campaign
Executes continuous multi-generation agent evolution, failure taxonomy analysis,
Pareto acceptance gates, and live cross-domain SaaS tool learning loops.
Burns sponsor tokens across TensorMux (glm-4-7-flash), OpenAI (gpt-5-nano), and Smallest.ai.
"""

import sys
import os
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

API_BASE = os.getenv("FORGE_API_URL", "http://127.0.0.1:8000")


async def run_campaign():
    print("=" * 70)
    print("  FORGE — Deep Evolution & Token Burn Campaign")
    print("  Track 1: Automated Agent Engineering (Syndicate by Maximor)")
    print("=" * 70)

    total_tokens_burned = 0
    total_audio_bytes = 0
    start_time = time.perf_counter()

    async with httpx.AsyncClient(base_url=API_BASE, timeout=180.0) as client:
        # Step 0: Verify API connectivity
        print("\n[1/6] Verifying API & Benchmark Registry...")
        bench_res = await client.get("/api/benchmarks")
        if bench_res.status_code != 200:
            print(f"Error: API returned {bench_res.status_code}")
            return
        benchmarks = bench_res.json()
        print(f"Found {len(benchmarks)} benchmarks: {[b['name'] for b in benchmarks]}")

        # Step 1: Create Grand Enterprise DevOps Experiment
        print("\n[2/6] Creating Enterprise DevOps Experiment with All 5 SaaS Tools...")
        exp_payload = {
            "name": "Track 1: Grand Enterprise Multi-Generation Evolution & Learning Campaign",
            "goal": (
                "Autonomously investigate production APM errors (Sentry), check customer SLA contracts (CRM), "
                "file urgent engineering issues with team UUIDs (Linear), create hotfix PRs under branch protection (GitHub), "
                "and broadcast incident alerts (Slack) while learning cross-tool quirks and persistent contextual policies."
            ),
            "benchmark_id": "third_party_automation",
            "tools": ["linear_api", "slack_api", "crm_api", "github_api", "sentry_api"],
        }
        res = await client.post("/api/experiments", json=exp_payload)
        exp = res.json()
        exp_id = exp["id"]
        print(f"Created Experiment: {exp_id} ('{exp['name'][:50]}...')")

        # Step 2: Generate Generation 0 Baseline Agent
        print("\n[3/6] Generating Generation 0 Baseline Agent via Live Model...")
        gen0_res = await client.post(f"/api/experiments/{exp_id}/generate")
        gen0 = gen0_res.json()
        gen0_id = gen0["id"]
        spec0 = gen0["agent_spec"]
        print(f"-> G0 Agent Generated: {gen0_id}")
        print(f"   Model: {spec0['model']} | Planner: {spec0['planner']['type']} | Verifier: {spec0['verifier']['type']}")

        # Step 3: Evaluate Generation 0 on Benchmark Tasks
        print("\n[4/6] Evaluating Generation 0 on Multi-Domain Benchmark Tasks...")
        eval0_res = await client.post(f"/api/experiments/{exp_id}/run?task_limit=4")
        eval0 = eval0_res.json()
        m0 = eval0.get("metrics", {})
        tokens_g0 = m0.get("total_tokens", 0)
        total_tokens_burned += tokens_g0
        print(f"-> G0 Evaluated:")
        print(f"   Accuracy: {m0.get('accuracy', 0)*100:.1f}% | Reliability: {m0.get('reliability', 0)*100:.1f}%")
        print(f"   Composite Score: {m0.get('composite_score', 0):.4f} | Tokens Burned: {tokens_g0}")
        print(f"   Failures Observed: {m0.get('failure_breakdown', {})}")

        # Synthesize G0 Voice Debrief with Smallest.ai
        print("   Synthesizing G0 Voice Commentary with Smallest.ai...")
        try:
            v0_res = await client.get(f"/api/generations/{gen0_id}/narrate")
            if v0_res.status_code == 200:
                total_audio_bytes += len(v0_res.content)
                print(f"   -> G0 Audio Commentary Synthesized: {len(v0_res.content):,} bytes")
        except Exception as ve:
            print(f"   -> Voice notice: {ve}")

        # Step 4: Autonomous Evolution -> Generation 1
        print("\n[5/6] Triggering Evolutionary Engine: Failure Analysis & Mutation -> Generation 1...")
        evolve1_res = await client.post(f"/api/experiments/{exp_id}/evolve?task_limit=4")
        gen1 = evolve1_res.json()
        gen1_id = gen1["id"]
        m1 = gen1.get("metrics", {})
        tokens_g1 = m1.get("total_tokens", 0)
        total_tokens_burned += tokens_g1
        print(f"-> G1 Candidate Evaluated: {gen1_id}")
        print(f"   Status: {gen1.get('status')} | Reason: {gen1.get('rejection_reason')}")
        print(f"   Accuracy: {m1.get('accuracy', 0)*100:.1f}% | Composite Score: {m1.get('composite_score', 0):.4f}")
        print(f"   Tokens Burned: {tokens_g1}")

        # Step 5: Execute Track 1 Dual-Pass Learning Run (Cold vs Warm Tool Memory)
        print("\n[6/6] Executing Deep SaaS Learning Cycle (Run 1 Cold vs Run 2 Warm Memory)...")
        lr_res = await client.post(f"/api/experiments/{exp_id}/learning-run")
        lr = lr_res.json()
        print(f"-> Learning Loop Status: {lr['status']}")

        delta = lr.get("efficiency_delta", {})
        print(f"   Empirical Delta:")
        print(f"   - Tool Call Reduction: {delta.get('tool_call_reduction')} ({lr['run_1_cold']['tool_calls']} -> {lr['run_2_warm']['tool_calls']})")
        print(f"   - Latency Reduction:   {delta.get('latency_reduction')} ({lr['run_1_cold']['latency_ms']/1000:.1f}s -> {lr['run_2_warm']['latency_ms']/1000:.1f}s)")
        print(f"   - Cost Reduction:      {delta.get('cost_reduction')} (${lr['run_1_cold']['cost_usd']:.4f} -> ${lr['run_2_warm']['cost_usd']:.4f})")
        print(f"   - Errors Prevented:    {delta.get('errors_prevented')}")

        playbooks = lr.get("learned_playbooks", [])
        print(f"\n   Learned Tool Memory Ledger ({len(playbooks)} Persistent Heuristics):")
        for p in playbooks:
            print(f"   * [{p['category']}] ({p['tool_name']}) {p['learned_rule'][:80]}... (Confidence: {p['confidence']})")

        # Synthesize Grand Learning Narration with Smallest.ai
        print("\n   Synthesizing Grand Learning Audio Debrief with Smallest.ai...")
        try:
            v_learn = await client.get(f"/api/experiments/{exp_id}/learning-narrate")
            if v_learn.status_code == 200:
                total_audio_bytes += len(v_learn.content)
                print(f"   -> Grand Learning Audio Debrief: {len(v_learn.content):,} bytes WAV audio")
        except Exception as ve:
            print(f"   -> Voice notice: {ve}")

        # Provenance verification
        prov_res = await client.get(f"/api/experiments/{exp_id}/provenance")
        prov = prov_res.json()
        print(f"\n   Cryptographic Provenance Chain Valid: {prov['is_valid']} ({prov['total_events']} SHA-256 blocks)")

    elapsed = time.perf_counter() - start_time
    print("\n" + "=" * 70)
    print("  CAMPAIGN COMPLETE — SUMMARY OF RESULTS")
    print("=" * 70)
    print(f"  Experiment ID:           {exp_id}")
    print(f"  Total Runtime:           {elapsed:.1f} seconds")
    print(f"  Total Tokens Burned:     {total_tokens_burned:,} tokens")
    print(f"  Total Audio Synthesized: {total_audio_bytes:,} bytes")
    print(f"  Generations Evaluated:   2 (G0, G1)")
    print(f"  Learned Heuristics:      {len(playbooks)} active persistent rules")
    print(f"  Efficiency Boost:        {delta.get('tool_call_reduction')} tool calls, {delta.get('latency_reduction')} latency, {delta.get('cost_reduction')} cost")
    print(f"  Live UI Dashboard:       http://localhost:3000/experiments/{exp_id}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_campaign())
