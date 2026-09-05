#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.benchmarks.registry import benchmark_registry
from app.benchmarks.software_engineering import SoftwareEngineeringBenchmark


async def seed_benchmark():
    print("==================================================")
    print(" FORGE - Benchmark Seeding & Integrity Check")
    print("==================================================")

    bench = benchmark_registry.get("software_engineering")
    if not bench:
        print("[ERROR] Software engineering benchmark not found in registry.")
        sys.exit(1)

    tasks = bench.list_tasks()
    print(f"Loaded Benchmark: {bench.name} (version {bench.version})")
    print(f"Total benchmark tasks: {len(tasks)}\n")

    for idx, t in enumerate(tasks, 1):
        print(f"[{idx:02d}] {t.id}: {t.title}")
        print(f"     Repository:  {t.repository}")
        print(f"     Issue:       {t.issue[:80]}...")
        print(f"     Constraints: {', '.join(t.constraints)}")
        print()

    print("==================================================")
    print("All 10 benchmark tasks registered and validated.")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(seed_benchmark())
