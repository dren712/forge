#!/usr/bin/env python3
import sys
import os
import argparse
import asyncio
import json
import time
import uuid
import shutil
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.benchmarks.registry import benchmark_registry
from app.benchmarks.base import BenchmarkTask, TaskEvaluation
from app.schemas.agent_spec import (
    AgentSpec,
    PlannerConfig,
    MemoryConfig,
    VerifierConfig,
    OrchestrationConfig,
)
from app.agents.runtime import AgentRuntime
from app.agents.state import AgentState
from app.providers.base import LLMProvider, LLMResponse, ToolCallItem
from app.providers.factory import get_llm_provider
from app.providers.mock import DeterministicMockProvider
from app.evaluation.scoring import (
    compute_cost,
    compute_reliability,
    compute_composite_score,
    aggregate_generation_metrics,
)
from app.evaluation.metrics import ExecutionMetrics


class BenchmarkMockProvider(LLMProvider):
    """
    Deterministic mock provider simulating realistic agent tool interactions
    against benchmark enterprise tasks when running in mock mode.
    """
    def __init__(self, mode: str = "baseline"):
        self.mode = mode
        self.step_tracker: dict[str, int] = {}

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        response_format: dict = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        full_text = " ".join([m.get("content", "") for m in messages if isinstance(m.get("content"), str)])

        # Determine task
        task_id = "unknown"
        for candidate in [
            "task_01_api_discovery", "task_02_contextual_sla_routing", "task_03_repeat_efficiency",
            "task_04_github_protected_branch_hotfix", "task_05_sentry_p99_latency_investigation",
            "task_06_cross_platform_enterprise_outage", "task_07_growth_tier_routing",
            "task_08_github_ci_status_merge", "task_09_security_incident_triage",
            "task_10_end_to_end_resilience"
        ]:
            if candidate in full_text:
                task_id = candidate
                break

        current_step = self.step_tracker.get(task_id, 0)
        self.step_tracker[task_id] = current_step + 1

        # Check last tool results
        last_tool_res = ""
        for m in reversed(messages):
            if m.get("role") == "tool":
                last_tool_res = m.get("content", "")
                break

        # Task 01: Linear discovery
        if "task_01" in task_id or "Database Pool Exhaustion" in full_text:
            if current_step > 0:
                return LLMResponse(content="Linear discovery complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            if self.mode == "baseline":
                return LLMResponse(
                    content="Creating issue under CORE team.",
                    tool_calls=[
                        ToolCallItem(id="tc_1", name="linear_api", arguments={"action": "create_issue", "team_id": "CORE", "title": "DB Pool Exhaustion", "priority": 1})
                    ],
                    input_tokens=150, output_tokens=30, total_tokens=180
                )
            else:
                return LLMResponse(
                    content="Creating issue with verified Core Platform UUID.",
                    tool_calls=[
                        ToolCallItem(id="tc_1", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "DB Pool Exhaustion", "priority": 1})
                    ],
                    input_tokens=180, output_tokens=40, total_tokens=220
                )

        # Task 02: Contextual SLA routing
        if "task_02" in task_id or "cust_acme_corp" in full_text:
            if self.mode == "baseline":
                if current_step > 0:
                    return LLMResponse(content="Baseline SLA routing complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
                return LLMResponse(
                    content="Posting standard alert to #general.",
                    tool_calls=[
                        ToolCallItem(id="tc_slack_bad", name="slack_api", arguments={"action": "post_message", "channel": "#general", "text": "Customer latency issue"}),
                    ],
                    input_tokens=140, output_tokens=30, total_tokens=170
                )
            else:
                if current_step == 0:
                    return LLMResponse(
                        content="Inspecting CRM for Acme Corp SLA terms.",
                        tool_calls=[ToolCallItem(id="tc_crm", name="crm_api", arguments={"action": "get_customer", "customer_id": "cust_acme_corp"})],
                        input_tokens=150, output_tokens=25, total_tokens=175
                    )
                elif current_step == 1:
                    return LLMResponse(
                        content="Posting SLA alert to #enterprise-escalations and filing Linear P1.",
                        tool_calls=[
                            ToolCallItem(id="tc_slack", name="slack_api", arguments={"action": "post_message", "channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_acme_corp latency spike"}),
                            ToolCallItem(id="tc_linear", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "cust_acme_corp Latency", "priority": 1}),
                        ],
                        input_tokens=250, output_tokens=50, total_tokens=300
                    )
                else:
                    return LLMResponse(content="Evolved SLA routing complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)

        # Task 03: Repeat efficiency
        if "task_03" in task_id or "payment webhook failure" in full_text:
            if current_step > 0:
                return LLMResponse(content="Repeat incident complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            if self.mode == "baseline":
                return LLMResponse(
                    content="Exploratory search across channels.",
                    tool_calls=[
                        ToolCallItem(id="tc_disc", name="linear_api", arguments={"action": "list_teams"}),
                    ],
                    input_tokens=120, output_tokens=20, total_tokens=140
                )
            else:
                return LLMResponse(
                    content="Executing direct enterprise escalation.",
                    tool_calls=[
                        ToolCallItem(id="tc_slack", name="slack_api", arguments={"action": "post_message", "channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_acme_corp payment webhook failure"}),
                        ToolCallItem(id="tc_linear", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "Webhook Failure", "priority": 1}),
                    ],
                    input_tokens=190, output_tokens=40, total_tokens=230
                )

        # Task 04: GitHub PR policy
        if "task_04" in task_id or "Fix DB pool" in full_text:
            if current_step > 0:
                return LLMResponse(content="GitHub PR complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            if self.mode == "baseline":
                return LLMResponse(
                    content="Creating PR with arbitrary branch name.",
                    tool_calls=[
                        ToolCallItem(id="tc_gh_bad", name="github_api", arguments={"action": "create_pull_request", "title": "Fix DB pool", "head_branch": "my-branch", "base_branch": "main"})
                    ],
                    input_tokens=130, output_tokens=25, total_tokens=155
                )
            else:
                return LLMResponse(
                    content="Creating PR with compliant branch and bracketed tag.",
                    tool_calls=[
                        ToolCallItem(id="tc_gh", name="github_api", arguments={"action": "create_pull_request", "title": "[LIN-101] Fix DB connection pool", "head_branch": "fix/db-pool-leak", "base_branch": "main"})
                    ],
                    input_tokens=160, output_tokens=35, total_tokens=195
                )

        # Task 05: Sentry APM resolution
        if "task_05" in task_id or "SENTRY-891" in full_text:
            if current_step > 0:
                return LLMResponse(content="Sentry resolution complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            if self.mode == "baseline":
                return LLMResponse(
                    content="Resolving Sentry incident with short note.",
                    tool_calls=[
                        ToolCallItem(id="tc_sen_bad", name="sentry_api", arguments={"action": "resolve_incident", "issue_id": "SENTRY-891", "resolution_note": "fixed"})
                    ],
                    input_tokens=140, output_tokens=20, total_tokens=160
                )
            else:
                return LLMResponse(
                    content="Resolving Sentry incident with detailed diagnosis.",
                    tool_calls=[
                        ToolCallItem(id="tc_sen", name="sentry_api", arguments={"action": "resolve_incident", "issue_id": "SENTRY-891", "resolution_note": "Identified connection leak and patched connection pool max size."})
                    ],
                    input_tokens=170, output_tokens=40, total_tokens=210
                )

        # Task 06: Cross-platform enterprise outage
        if "task_06" in task_id or "Critical outage reported" in full_text:
            if current_step > 0:
                return LLMResponse(content="Cross-platform outage response complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            return LLMResponse(
                content="Orchestrating cross-platform response.",
                tool_calls=[
                    ToolCallItem(id="tc_l6", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "P1 Billing Outage", "priority": 1}),
                    ToolCallItem(id="tc_s6", name="slack_api", arguments={"action": "post_message", "channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_acme_corp critical outage"}),
                ],
                input_tokens=220, output_tokens=45, total_tokens=265
            )

        # Task 07: Growth tier routing
        if "task_07" in task_id or "cust_growth_start" in full_text:
            if current_step > 0:
                return LLMResponse(content="Growth routing complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            if self.mode == "baseline":
                return LLMResponse(
                    content="Escalating customer alert to executive channel.",
                    tool_calls=[
                        ToolCallItem(id="tc_bad_g", name="slack_api", arguments={"action": "post_message", "channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_growth_start UI bug"})
                    ],
                    input_tokens=130, output_tokens=25, total_tokens=155
                )
            else:
                return LLMResponse(
                    content="Routing growth customer to engineering backlog.",
                    tool_calls=[
                        ToolCallItem(id="tc_growth", name="slack_api", arguments={"action": "post_message", "channel": "#eng-backlog", "text": "Customer cust_growth_start reported UI bug"})
                    ],
                    input_tokens=140, output_tokens=30, total_tokens=170
                )

        # Task 08: GitHub CI status & merge
        if "task_08" in task_id or "PR #42" in full_text:
            if current_step == 0:
                return LLMResponse(
                    content="Checking PR #42 status.",
                    tool_calls=[ToolCallItem(id="tc_chk", name="github_api", arguments={"action": "check_pr_status", "pr_number": 42})],
                    input_tokens=130, output_tokens=25, total_tokens=155
                )
            elif current_step == 1:
                return LLMResponse(
                    content="Merging PR #42.",
                    tool_calls=[ToolCallItem(id="tc_mrg", name="github_api", arguments={"action": "merge_pull_request", "pr_number": 42})],
                    input_tokens=180, output_tokens=30, total_tokens=210
                )
            else:
                return LLMResponse(content="PR #42 verified and merged.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)

        # Task 09: Security triage
        if "task_09" in task_id or "gateway auth" in full_text:
            if current_step > 0:
                return LLMResponse(content="Security triage complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            return LLMResponse(
                content="Triaging security vulnerability under Security UUID.",
                tool_calls=[
                    ToolCallItem(id="tc_sec_lin", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440002", "title": "Auth Bypass Fix", "priority": 1}),
                    ToolCallItem(id="tc_sec_slk", name="slack_api", arguments={"action": "post_message", "channel": "#sec-ops", "text": "Urgent security vulnerability registered"}),
                ],
                input_tokens=220, output_tokens=45, total_tokens=265
            )

        # Task 10: End-to-end resilience
        if "task_10" in task_id or "Full incident mitigation" in full_text:
            if current_step > 0:
                return LLMResponse(content="End-to-end resilience complete.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)
            return LLMResponse(
                content="Executing complete DevOps mitigation cycle.",
                tool_calls=[
                    ToolCallItem(id="tc_e2e_lin", name="linear_api", arguments={"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "DB Leak", "priority": 1}),
                    ToolCallItem(id="tc_e2e_gh", name="github_api", arguments={"action": "create_pull_request", "title": "[LIN-102] Hotfix", "head_branch": "fix/stripe-webhook", "base_branch": "main"}),
                    ToolCallItem(id="tc_e2e_slk", name="slack_api", arguments={"action": "post_message", "channel": "#general", "text": "Incident resolved and PR deployed."}),
                ],
                input_tokens=300, output_tokens=60, total_tokens=360
            )

        # Default fallback
        return LLMResponse(content="Action completed successfully.", tool_calls=[], input_tokens=80, output_tokens=15, total_tokens=95)


def build_spec(mode: str, provider_name: str) -> AgentSpec:
    tools = ["linear_api", "slack_api", "crm_api", "github_api", "sentry_api"]
    model_name = "glm-4.7-flash" if provider_name == "tensormux" else ("gpt-4o-mini" if provider_name == "openai" else "mock-llm")

    if mode == "baseline":
        return AgentSpec(
            model=model_name,
            system_prompt=(
                "You are an enterprise operations agent. Execute requested tasks across Linear, Slack, CRM, GitHub, and Sentry. "
                "Inspect errors carefully and achieve task goals."
            ),
            planner=PlannerConfig(type="none"),
            tools=tools,
            memory=MemoryConfig(type="stateless"),
            verifier=VerifierConfig(type="none"),
            orchestration=OrchestrationConfig(type="direct"),
        )
    else:
        return AgentSpec(
            model=model_name,
            system_prompt=(
                "You are an advanced enterprise operations agent equipped with verified API schemas and policy rules. "
                "Core Platform UUID: 550e8400-e29b-41d4-a716-446655440001. "
                "Security & Infra UUID: 550e8400-e29b-41d4-a716-446655440002. "
                "Enterprise SLA alert: channel '#enterprise-escalations' with tag '[SLA-ALERT]'. "
                "Growth customers must route to '#eng-backlog'. "
                "GitHub hotfix PRs must use head prefix 'fix/' and bracketed issue tag '[LIN-...]'. "
                "Sentry incident resolution notes must exceed 15 characters."
            ),
            planner=PlannerConfig(type="structured_plan", max_subgoals=5),
            tools=tools,
            memory=MemoryConfig(type="working_context"),
            verifier=VerifierConfig(type="self_check"),
            orchestration=OrchestrationConfig(type="plan_execute_verify"),
        )


async def run_benchmark(args):
    bench = benchmark_registry.get(args.benchmark)
    if not bench:
        print(f"ERROR: Benchmark '{args.benchmark}' not found in registry.", file=sys.stderr)
        print(f"Available benchmarks: {[b['name'] for b in benchmark_registry.list_benchmarks()]}", file=sys.stderr)
        sys.exit(1)

    all_tasks = bench.list_tasks()
    if args.tasks:
        requested_ids = [t.strip() for t in args.tasks.split(",") if t.strip()]
        tasks = [t for t in all_tasks if t.id in requested_ids]
        if not tasks:
            print(f"ERROR: No matching tasks found for filter: {args.tasks}", file=sys.stderr)
            sys.exit(1)
    else:
        tasks = all_tasks

    # Provider setup
    if args.provider == "mock":
        provider = BenchmarkMockProvider(mode=args.mode)
    elif args.provider == "tensormux":
        from app.providers.tensormux import TensorMuxProvider
        from app.core.config import settings
        provider = TensorMuxProvider(api_key=settings.tensormux_api_key, base_url=settings.tensormux_base_url, model=settings.tensormux_model)
    elif args.provider == "openai":
        from app.providers.aigrants import AIGrantsIndiaProvider
        from app.core.config import settings
        provider = AIGrantsIndiaProvider(api_key=settings.aigrants_api_key, base_url=settings.aigrants_base_url, model=settings.aigrants_model)
    else:
        provider = get_llm_provider()

    spec = build_spec(args.mode, args.provider)
    generation_label = "G0" if args.mode == "baseline" else "G1"

    run_id = f"bench_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    base_workspace = Path(f"/tmp/forge_benchmarks/{run_id}")
    base_workspace.mkdir(parents=True, exist_ok=True)

    task_results = []
    task_metrics = []

    for task in tasks:
        task_ws = base_workspace / task.id
        await bench.reset_task(task, task_ws)

        runtime = AgentRuntime(spec=spec, provider=provider)
        start_t = time.perf_counter()

        constraints_str = ", ".join(task.constraints)
        goal_text = (
            f"Task: {task.id}\n"
            f"Issue: {task.issue}\n"
            f"Expected: {task.expected_behavior}\n"
            f"Constraints: {constraints_str}"
        )
        agent_state = await runtime.run(
            goal=goal_text,
            workspace=task_ws,
            generation_id=generation_label,
            execution_id=str(uuid.uuid4()),
        )
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        eval_res = await bench.evaluate_task(agent_state, task, task_ws)

        cost = compute_cost(agent_state.input_tokens, agent_state.output_tokens)
        rel = compute_reliability(agent_state, eval_res)
        tool_errs = len([tr for tr in agent_state.tool_results if not tr.get("success", False)])

        metric = ExecutionMetrics(
            task_id=task.id,
            task_success=eval_res.passed,
            accuracy=1.0 if eval_res.passed else 0.0,
            reliability=rel,
            cost_usd=cost,
            latency_ms=elapsed_ms,
            input_tokens=agent_state.input_tokens,
            output_tokens=agent_state.output_tokens,
            total_tokens=agent_state.total_tokens,
            model_calls=agent_state.model_call_count,
            tool_calls=agent_state.tool_call_count,
            tool_errors=tool_errs,
            verification_passed=agent_state.verification_passed,
            clean_exit=(agent_state.status == "COMPLETED"),
            recovered_from_error=(tool_errs > 0 and eval_res.passed),
        )
        task_metrics.append(metric)

        task_results.append({
            "task_id": task.id,
            "title": task.title,
            "passed": eval_res.passed,
            "score": eval_res.score,
            "reason": eval_res.reason,
            "checks": [{"name": c.name, "passed": c.passed, "evidence": c.evidence} for c in eval_res.checks],
            "duration_ms": round(elapsed_ms, 1),
            "tool_calls": agent_state.tool_call_count,
            "failures": eval_res.failures,
        })

    # Cleanup temporary workspace
    try:
        shutil.rmtree(base_workspace)
    except Exception:
        pass

    gen_metrics = aggregate_generation_metrics(
        generation_number=0 if args.mode == "baseline" else 1,
        task_metrics=task_metrics,
    )

    passed_count = sum(1 for tm in task_metrics if tm.task_success)
    total_count = len(task_metrics)

    summary = {
        "benchmark": bench.name,
        "version": bench.version,
        "generation": generation_label,
        "mode": args.mode,
        "provider": args.provider,
        "tasks": total_count,
        "passed": passed_count,
        "failed": total_count - passed_count,
        "accuracy": gen_metrics.accuracy,
        "reliability": gen_metrics.reliability,
        "avg_tool_calls": round(gen_metrics.total_tool_calls / max(total_count, 1), 2),
        "avg_latency_ms": gen_metrics.avg_latency_ms,
        "avg_cost": gen_metrics.avg_cost_per_task,
        "composite_score": gen_metrics.composite_score,
        "task_results": task_results,
    }

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(summary, indent=2))

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    # Print formatted human-readable report
    print("\n" + "═" * 60)
    print(f"  FORGE Benchmark Report: {bench.name} (v{bench.version})")
    print("═" * 60)
    print(f"  Agent Generation:   {generation_label} ({args.mode})")
    print(f"  Model / Provider:   {args.provider}")
    print(f"  Total Tasks:        {total_count}")
    print(f"  Passed:             {passed_count}")
    print(f"  Failed:             {total_count - passed_count}")
    print(f"  Accuracy:           {gen_metrics.accuracy * 100:.1f}%")
    print(f"  Reliability:        {gen_metrics.reliability * 100:.1f}%")
    print(f"  Avg Tool Calls:     {summary['avg_tool_calls']}")
    print(f"  Avg Latency:        {gen_metrics.avg_latency_ms / 1000.0:.2f}s")
    print(f"  Avg Cost / Task:    ${gen_metrics.avg_cost_per_task:.6f}")
    print(f"  Composite Score:    {gen_metrics.composite_score:.3f}")
    print("─" * 60)
    print(f"  {'TASK ID':<34} | {'STATUS':<6} | {'SCORE':<5} | {'CHECKS'}")
    print("─" * 60)
    for tr in task_results:
        status_str = "PASS" if tr["passed"] else "FAIL"
        passed_chk = sum(1 for c in tr["checks"] if c["passed"])
        tot_chk = len(tr["checks"])
        chk_summary = f"{passed_chk}/{tot_chk} checks"
        print(f"  {tr['task_id']:<34} | {status_str:<6} | {tr['score']:<5.1f} | {chk_summary}")
    print("═" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="FORGE Canonical Benchmark Runner")
    parser.add_argument("--benchmark", default="third_party_automation", help="Benchmark name")
    parser.add_argument("--version", default="2.0.0", help="Benchmark version")
    parser.add_argument("--tasks", default=None, help="Comma-separated list of task IDs to run")
    parser.add_argument("--mode", choices=["baseline", "evolved", "mock"], default="baseline", help="Agent architecture mode")
    parser.add_argument("--provider", choices=["mock", "tensormux", "openai"], default="mock", help="LLM provider")
    parser.add_argument("--repeat", type=int, default=1, help="Repetitions per task")
    parser.add_argument("--output", default=None, help="Path to write JSON benchmark results")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")

    args = parser.parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
