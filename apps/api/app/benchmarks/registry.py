from typing import Dict
from app.benchmarks.base import Benchmark
from app.benchmarks.software_engineering import SoftwareEngineeringBenchmark


class BenchmarkRegistry:
    def __init__(self):
        self._benchmarks: Dict[str, Benchmark] = {}
        self.register(SoftwareEngineeringBenchmark())

    def register(self, bench: Benchmark) -> None:
        self._benchmarks[bench.name] = bench

    def get(self, name: str) -> Benchmark | None:
        return self._benchmarks.get(name)

    def list_benchmarks(self) -> list[dict]:
        return [
            {
                "name": b.name,
                "version": b.version,
                "tasks_count": len(b.list_tasks()),
                "task_ids": [t.id for t in b.list_tasks()],
            }
            for b in self._benchmarks.values()
        ]


benchmark_registry = BenchmarkRegistry()
