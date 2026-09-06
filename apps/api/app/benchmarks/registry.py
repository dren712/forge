from typing import Dict
from app.benchmarks.base import Benchmark
from app.benchmarks.software_engineering import SoftwareEngineeringBenchmark
from app.benchmarks.third_party_benchmark import ThirdPartyAppBenchmark


class BenchmarkRegistry:
    def __init__(self):
        self._benchmarks: Dict[str, Benchmark] = {}
        self.register(SoftwareEngineeringBenchmark())
        self.register(ThirdPartyAppBenchmark())

    def register(self, bench: Benchmark) -> None:
        self._benchmarks[bench.name] = bench

    def get(self, name: str) -> Benchmark | None:
        return self._benchmarks.get(name)

    def list_benchmarks(self) -> list[dict]:
        return [
            {
                "benchmark_id": getattr(b, "benchmark_id", b.name),
                "name": b.name,
                "version": b.version,
                "evaluator_version": getattr(b, "evaluator_version", b.version),
                "created_at": getattr(b, "created_at", "2026-03-01T00:00:00Z"),
                "tasks_count": len(b.list_tasks()),
                "task_ids": [t.id for t in b.list_tasks()],
            }
            for b in self._benchmarks.values()
        ]


benchmark_registry = BenchmarkRegistry()
