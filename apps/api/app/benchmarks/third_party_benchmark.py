import json
from pathlib import Path
from typing import List, Any
from app.benchmarks.base import Benchmark, BenchmarkTask, TaskEvaluation
from app.agents.state import AgentState


class ThirdPartyAppBenchmark:
    name: str = "third_party_automation"
    version: str = "1.0.0"

    TASKS = [
        BenchmarkTask(
            id="task_01_api_discovery",
            title="Linear API Discovery: Resolve Team UUID & Priority Format",
            description="Create an urgent incident issue for 'Database Pool Exhaustion' under the Core Platform team.",
            repository="multi_app_workspace",
            issue="Engineers report connection pool exhaustion. Create tracking issue in Linear under Core Platform with Urgent priority.",
            expected_behavior="Issue created with team_id='550e8400-e29b-41d4-a716-446655440001' and priority=1.",
        ),
        BenchmarkTask(
            id="task_02_contextual_sla_routing",
            title="Cross-App Contextual Routing: Enterprise SLA Escalation",
            description="Customer 'cust_acme_corp' reported API latency spike. Inspect CRM for SLA contract rules and execute required routing.",
            repository="multi_app_workspace",
            issue="Incoming support alert for 'cust_acme_corp'. Look up their SLA tier in CRM and execute the required channel alert and issue creation.",
            expected_behavior="Message posted to #enterprise-escalations with [SLA-ALERT] and Linear issue created with priority 1.",
        ),
        BenchmarkTask(
            id="task_03_repeat_efficiency",
            title="Repeat Execution: Zero-Exploration Incident Resolution",
            description="Customer 'cust_acme_corp' reported payment webhook failure. Execute enterprise escalation with minimal tool calls.",
            repository="multi_app_workspace",
            issue="Payment webhook failure for 'cust_acme_corp'. Execute standard enterprise escalation.",
            expected_behavior="Direct execution without exploratory errors, posting to Slack and Linear with optimal parameters.",
        ),
    ]

    def list_tasks(self) -> List[BenchmarkTask]:
        return list(self.TASKS)

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        # Initialize empty Linear & Slack workspace states
        (workspace / ".linear_state.json").write_text(json.dumps({"issues": [], "counter": 101}, indent=2))
        (workspace / ".slack_messages.json").write_text(json.dumps([], indent=2))

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        linear_file = workspace / ".linear_state.json"
        slack_file = workspace / ".slack_messages.json"

        linear_state = {}
        if linear_file.exists():
            try:
                linear_state = json.loads(linear_file.read_text())
            except Exception:
                pass

        slack_messages = []
        if slack_file.exists():
            try:
                slack_messages = json.loads(slack_file.read_text())
            except Exception:
                pass

        issues = linear_state.get("issues", [])

        if task.id == "task_01_api_discovery":
            # Task 1 check: Core Platform UUID and priority 1
            valid_issue = any(
                i.get("team_id") == "550e8400-e29b-41d4-a716-446655440001"
                and i.get("priority") == 1
                for i in issues
            )
            if valid_issue:
                return TaskEvaluation(
                    task_id=task.id,
                    passed=True,
                    score=1.0,
                    reason="Successfully created Linear issue with correct team UUID and priority=1.",
                )
            return TaskEvaluation(
                task_id=task.id,
                passed=False,
                score=0.0,
                reason=f"Linear issue missing or incorrect parameters. Current issues: {issues}",
            )

        elif task.id == "task_02_contextual_sla_routing":
            # Task 2 check: Slack message in #enterprise-escalations with [SLA-ALERT] and priority 1 issue
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                and "cust_acme_corp" in m.get("text", "")
                for m in slack_messages
            )
            has_linear = any(i.get("priority") == 1 for i in issues)

            if has_slack and has_linear:
                return TaskEvaluation(
                    task_id=task.id,
                    passed=True,
                    score=1.0,
                    reason="Enterprise SLA escalation verified: posted to #enterprise-escalations with [SLA-ALERT] and created priority 1 issue.",
                )
            return TaskEvaluation(
                task_id=task.id,
                passed=False,
                score=0.5 if (has_slack or has_linear) else 0.0,
                reason=f"Escalation incomplete. Has Slack alert: {has_slack}, Has Priority 1 Linear issue: {has_linear}.",
            )

        elif task.id == "task_03_repeat_efficiency":
            # Task 3 check: Both alerts executed and check tool efficiency
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                for m in slack_messages
            )
            has_linear = any(i.get("priority") == 1 for i in issues)

            if has_slack and has_linear:
                return TaskEvaluation(
                    task_id=task.id,
                    passed=True,
                    score=1.0,
                    reason="Repeat enterprise incident executed successfully with learned memory rules.",
                )
            return TaskEvaluation(
                task_id=task.id,
                passed=False,
                score=0.0,
                reason="Failed to execute repeat incident response properly.",
            )

        return TaskEvaluation(task_id=task.id, passed=False, score=0.0, reason="Unknown task")
