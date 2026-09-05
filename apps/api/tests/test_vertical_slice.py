import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from app.schemas.agent_spec import AgentSpec
from app.providers.mock import DeterministicMockProvider
from app.agents.architect import AgentArchitect
from app.benchmarks.software_engineering import SoftwareEngineeringBenchmark
from app.evolution.engine import EvolutionEngine
from app.provenance.hasher import verify_event_chain


@pytest.mark.asyncio
async def test_vertical_slice():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # 1. Setup Provider & Architect
        provider = DeterministicMockProvider(mode="baseline")
        architect = AgentArchitect(provider)

        # 2. Design G0 AgentSpec
        g0_spec = await architect.design_agent(
            goal="Resolve software engineering issues in repositories",
            available_tools=["repository", "file_editor", "shell", "test_runner", "search"],
            benchmark_description="Software Engineering Benchmark v1",
            generation_number=0,
        )
        assert g0_spec is not None
        assert g0_spec.model == "glm-4-7-flash"
        assert g0_spec.verifier.type == "none"  # baseline starts naive

        # 3. Benchmark Task & Engine
        benchmark = SoftwareEngineeringBenchmark()
        tasks = benchmark.list_tasks()
        task_1 = tasks[0]  # Fix pagination boundary

        engine = EvolutionEngine(
            experiment_id="exp_test_vertical_slice",
            benchmark=benchmark,
            provider=provider,
            workspaces_root=temp_dir / "workspaces",
        )

        # 4. Run G0 on task 1
        g0_metrics, g0_task_metrics, g0_failures = await engine.run_generation(
            generation_id="gen_0",
            generation_number=0,
            spec=g0_spec,
            task_subset=[task_1],
        )

        # G0 should fail verification because it declared success without running tests
        assert len(g0_task_metrics) == 1
        assert len(g0_failures) >= 1
        assert g0_failures[0].failure_type.value == "VERIFICATION_FAILURE"

        # Switch mock provider to evolved mode for candidate G1
        provider.mode = "evolved"

        # 5. Evolve: Propose mutation & execute candidate G1
        g1_spec, mutation, g1_metrics, decision = await engine.evolve_step(
            current_generation_id="gen_0",
            current_generation_number=0,
            current_spec=g0_spec,
            current_metrics=g0_metrics,
            failures=g0_failures,
            task_subset=[task_1],
        )

        assert mutation.mutation_type.value == "VERIFIER_UPDATE"
        assert g1_spec.verifier.type == "mandatory_tests"

        # Candidate G1 should have higher reliability/accuracy
        assert decision.accepted is True
        assert decision.status == "ACCEPTED"

        # 6. Verify Cryptographic Provenance Chain
        events = engine.recorder.get_events()
        assert len(events) >= 10
        is_valid, broken_idx, msg = verify_event_chain(events)
        assert is_valid is True, f"Provenance chain invalid: {msg}"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
