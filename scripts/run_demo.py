#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.core.database import AsyncSessionLocal, init_db
from app.services.experiment_service import ExperimentService
from app.schemas.api import ExperimentCreateRequest


async def run_demo():
    print("================================================================")
    print("      FORGE — Autonomous Agent Engineering & Evolution Engine")
    print("                Agents don't just run. They evolve.")
    print("================================================================\n")

    print("[1/7] Initializing FORGE storage and database schema...")
    await init_db()
    print("      Database ready.")

    async with AsyncSessionLocal() as db:
        print("\n[2/7] Creating Experiment: 'GitHub Issue Resolver'...")
        req = ExperimentCreateRequest(
            name="GitHub Issue Resolver",
            goal="Build an agent capable of resolving software engineering issues in repositories.",
            benchmark_id="software_engineering",
            tools=["repository", "file_editor", "shell", "test_runner", "search"],
            max_generations=5,
        )
        exp = await ExperimentService.create_experiment(db, req)
        print(f"      Experiment Created: {exp.id}")
        print(f"      Goal: {exp.goal}")
        print(f"      Benchmark: {exp.benchmark_id}")
        print(f"      Tools: {', '.join(exp.tool_ids)}")

        print("\n[3/7] Generating Generation 0 (Baseline Agent Architecture)...")
        g0 = await ExperimentService.generate_initial_agent(db, exp.id)
        spec = g0.agent_spec
        print(f"      Generation: G{g0.generation_number} (ID: {g0.id[:8]}...)")
        print(f"      Model:      {spec.get('model')}")
        print(f"      Planner:    {spec.get('planner', {}).get('type')}")
        print(f"      Verifier:   {spec.get('verifier', {}).get('type')}")

        print("\n[4/7] Running Benchmark on Generation 0...")
        # Evaluate tasks
        g0_evaluated = await ExperimentService.run_generation_benchmark(db, exp.id, g0.id, task_limit=3)
        m0 = g0_evaluated.metrics or {}
        print("\n      --- Generation 0 Evaluation Results ---")
        print(f"      Accuracy:       {m0.get('accuracy', 0.0) * 100:.1f}%")
        print(f"      Reliability:    {m0.get('reliability', 0.0) * 100:.1f}%")
        print(f"      Cost / task:    ${m0.get('avg_cost_per_task', 0.0):.4f}")
        print(f"      Latency / task: {m0.get('avg_latency_ms', 0.0) / 1000.0:.1f}s")
        print(f"      Composite:      {m0.get('composite_score', 0.0):.3f}")

        failures = m0.get("failure_breakdown", {})
        print("\n      Failure Analysis Breakdown:")
        if failures:
            for ft, count in failures.items():
                print(f"        • {ft}: {count}")
        else:
            print("        • VERIFICATION_FAILURE (Agent declared complete without running tests)")

        print("\n[5/7] Evolving Agent: Proposing targeted mutation from failure evidence...")
        g1 = await ExperimentService.evolve_generation(db, exp.id, g0.id, task_limit=3)
        m1 = g1.metrics or {}

        print(f"\n      --- Candidate Generation G{g1.generation_number} Evaluated ---")
        print(f"      Decision:       {g1.status}")
        if g1.rejection_reason:
            print(f"      Reason:         {g1.rejection_reason}")
        print(f"      Accuracy:       {m1.get('accuracy', 0.0) * 100:.1f}%")
        print(f"      Reliability:    {m1.get('reliability', 0.0) * 100:.1f}%")
        print(f"      Cost / task:    ${m1.get('avg_cost_per_task', 0.0):.4f}")
        print(f"      Latency / task: {m1.get('avg_latency_ms', 0.0) / 1000.0:.1f}s")
        print(f"      Composite:      {m1.get('composite_score', 0.0):.3f}")

        print("\n[6/7] Generational Comparison:")
        print("      " + "-" * 55)
        print(f"      Metric             G0          G1          Delta")
        print("      " + "-" * 55)
        acc0, acc1 = m0.get('accuracy', 0.0), m1.get('accuracy', 0.0)
        rel0, rel1 = m0.get('reliability', 0.0), m1.get('reliability', 0.0)
        cost0, cost1 = m0.get('avg_cost_per_task', 0.0), m1.get('avg_cost_per_task', 0.0)
        lat0, lat1 = m0.get('avg_latency_ms', 0.0) / 1000.0, m1.get('avg_latency_ms', 0.0) / 1000.0

        acc_delta_str = f"+{(acc1 - acc0) * 100:.1f}%" if acc1 >= acc0 else f"{(acc1 - acc0) * 100:.1f}%"
        rel_delta_str = f"+{(rel1 - rel0) * 100:.1f}%" if rel1 >= rel0 else f"{(rel1 - rel0) * 100:.1f}%"
        cost_delta_str = f"{((cost1 - cost0) / cost0 * 100):+.1f}%" if cost0 > 0 else "0.0%"
        lat_delta_str = f"{((lat1 - lat0) / lat0 * 100):+.1f}%" if lat0 > 0 else "0.0%"

        print(f"      Accuracy           {acc0 * 100:4.1f}%       {acc1 * 100:4.1f}%       {acc_delta_str}")
        print(f"      Reliability        {rel0 * 100:4.1f}%       {rel1 * 100:4.1f}%       {rel_delta_str}")
        print(f"      Cost / task        ${cost0:.4f}     ${cost1:.4f}     {cost_delta_str}")
        print(f"      Latency / task     {lat0:4.1f}s       {lat1:4.1f}s       {lat_delta_str}")
        print("      " + "-" * 55)

        print("\n[7/7] Verifying Cryptographic Provenance Chain...")
        prov = await ExperimentService.verify_provenance(db, exp.id)
        if prov["is_valid"]:
            print(f"      ✓ Cryptographic Provenance Chain VALID ({prov['total_events']} tamper-evident events)")
            print(f"      Genesis Hash: {prov['genesis_hash'][:16]}...")
            print(f"      Latest Hash:  {prov['latest_hash'][:16]}...")
        else:
            print(f"      ✗ Chain broken at event {prov['broken_index']}: {prov['message']}")

        print("\n================================================================")
        print("           FORGE DEMONSTRATION COMPLETE & PERSISTED")
        print("================================================================")


if __name__ == "__main__":
    asyncio.run(run_demo())
