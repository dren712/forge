import json
from pathlib import Path
from typing import List, Any
from app.benchmarks.base import Benchmark, BenchmarkTask, TaskEvaluation
from app.agents.state import AgentState


class ThirdPartyAppBenchmark:
    name: str = "third_party_automation"
    version: str = "2.0.0"

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
        BenchmarkTask(
            id="task_04_github_protected_branch_hotfix",
            title="GitHub PR Policy: Protected Branch Hotfix",
            description="Create a hotfix pull request for '[LIN-101] Fix DB pool' from branch 'fix/db-pool-leak' to 'main'.",
            repository="multi_app_workspace",
            issue="Hotfix ready for DB pool. Create PR on GitHub targeting main following branch naming and title conventions.",
            expected_behavior="PR created with head branch prefix 'fix/' and title containing bracketed issue tag '[LIN-101]'.",
        ),
        BenchmarkTask(
            id="task_05_sentry_p99_latency_investigation",
            title="Sentry APM: Latency Spike Investigation & Resolution",
            description="Investigate high error rate on 'billing-api' and resolve incident 'SENTRY-891'.",
            repository="multi_app_workspace",
            issue="Billing API alerts are firing. Query Sentry for error traces on billing-api and resolve incident SENTRY-891 with a detailed note.",
            expected_behavior="Fetched error trace and resolved SENTRY-891 with resolution_note >= 15 characters.",
        ),
        BenchmarkTask(
            id="task_06_cross_platform_enterprise_outage",
            title="Cross-Platform Orchestration: P1 Outage Incident Response",
            description="Handle P1 outage: Investigate Sentry, file Linear issue under Core Platform, and alert #enterprise-escalations.",
            repository="multi_app_workspace",
            issue="Critical outage reported. Check Sentry billing-api, create priority 1 Linear issue with UUID, and notify Slack #enterprise-escalations with [SLA-ALERT].",
            expected_behavior="Linear priority 1 issue created and Slack message posted to #enterprise-escalations with [SLA-ALERT].",
        ),
        BenchmarkTask(
            id="task_07_growth_tier_routing",
            title="SLA Tier Differentiation: Growth Customer Routing",
            description="Customer 'cust_growth_start' reported minor UI bug. Check CRM tier and route appropriately.",
            repository="multi_app_workspace",
            issue="Ticket from 'cust_growth_start'. Check CRM tier. Do NOT post to #enterprise-escalations. Post to #eng-backlog with standard priority.",
            expected_behavior="CRM checked and notification sent to #eng-backlog without enterprise alert tag.",
        ),
        BenchmarkTask(
            id="task_08_github_ci_status_merge",
            title="GitHub Status Gate: Verify & Merge PR",
            description="Check status of Pull Request #42 and merge it if CI checks pass.",
            repository="multi_app_workspace",
            issue="Verify CI/CD status of PR #42 and execute merge once passing.",
            expected_behavior="Status checked and PR #42 merged successfully.",
        ),
        BenchmarkTask(
            id="task_09_security_incident_triage",
            title="Security Policy Routing: Security & Infra Team UUID",
            description="File urgent security patch issue under 'Security & Infra' team and notify #sec-ops.",
            repository="multi_app_workspace",
            issue="Vulnerability report in gateway auth. Create Linear issue under Security & Infra (UUID) with priority 1 and post to #sec-ops.",
            expected_behavior="Linear issue created with SEC UUID '550e8400-e29b-41d4-a716-446655440002' and Slack posted to #sec-ops.",
        ),
        BenchmarkTask(
            id="task_10_end_to_end_resilience",
            title="End-to-End Enterprise Resolution: From Sentry to GitHub to Slack",
            description="Complete full DevOps workflow: Sentry trace -> Linear issue -> GitHub Hotfix PR -> Slack debrief.",
            repository="multi_app_workspace",
            issue="Full incident mitigation: Trace billing error in Sentry, file Linear issue, create GitHub PR '[LIN-102] Hotfix' from 'fix/stripe-webhook', and post debrief to Slack.",
            expected_behavior="GitHub PR created, Linear issue created, and Slack notification delivered.",
        ),
    ]

    def list_tasks(self) -> List[BenchmarkTask]:
        return list(self.TASKS)

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        # Initialize default state files
        (workspace / ".linear_state.json").write_text(json.dumps({"issues": [], "counter": 101}, indent=2))
        (workspace / ".slack_messages.json").write_text(json.dumps([], indent=2))
        (workspace / ".github_state.json").write_text(json.dumps({
            "pull_requests": [
                {
                    "number": 42,
                    "title": "[LIN-101] Fix DB connection pool timeout",
                    "head": "fix/db-pool-leak",
                    "base": "main",
                    "state": "open",
                    "ci_status": "success",
                    "approvals": 2,
                }
            ],
            "counter": 43,
        }, indent=2))
        (workspace / ".sentry_state.json").write_text(json.dumps({
            "incidents": [
                {
                    "id": "SENTRY-891",
                    "service": "billing-api",
                    "error_title": "TimeoutError: connection pool exhausted",
                    "error_rate_pct": 8.45,
                    "p99_latency_ms": 2840.0,
                    "status": "unresolved",
                    "level": "P1",
                }
            ]
        }, indent=2))

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        linear_file = workspace / ".linear_state.json"
        slack_file = workspace / ".slack_messages.json"
        github_file = workspace / ".github_state.json"
        sentry_file = workspace / ".sentry_state.json"

        def read_json(p: Path, default: Any):
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except Exception:
                    pass
            return default

        linear_state = read_json(linear_file, {})
        slack_messages = read_json(slack_file, [])
        github_state = read_json(github_file, {})
        sentry_state = read_json(sentry_file, {})

        issues = linear_state.get("issues", [])
        prs = github_state.get("pull_requests", [])
        incidents = sentry_state.get("incidents", [])

        # TASK 01
        if task.id == "task_01_api_discovery":
            valid = any(
                i.get("team_id") == "550e8400-e29b-41d4-a716-446655440001"
                and i.get("priority") == 1
                for i in issues
            )
            return TaskEvaluation(
                task_id=task.id,
                passed=valid,
                score=1.0 if valid else 0.0,
                reason="Linear issue created with correct team UUID and priority=1." if valid else "Missing valid Linear issue.",
            )

        # TASK 02
        elif task.id == "task_02_contextual_sla_routing":
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                and "cust_acme_corp" in m.get("text", "")
                for m in slack_messages
            )
            has_linear = any(i.get("priority") == 1 for i in issues)
            passed = has_slack and has_linear
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else (0.5 if (has_slack or has_linear) else 0.0),
                reason="Enterprise SLA escalation complete." if passed else "Missing Slack SLA tag or Linear priority 1 issue.",
            )

        # TASK 03
        elif task.id == "task_03_repeat_efficiency":
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                for m in slack_messages
            )
            has_linear = any(i.get("priority") == 1 for i in issues)
            passed = has_slack and has_linear
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else 0.0,
                reason="Repeat incident triage completed successfully." if passed else "Repeat incident triage failed.",
            )

        # TASK 04: GitHub Protected Branch Hotfix
        elif task.id == "task_04_github_protected_branch_hotfix":
            valid_pr = any(
                p.get("head", "").startswith(("fix/", "hotfix/"))
                and "[" in p.get("title", "")
                for p in prs
                if p.get("number") != 42
            )
            return TaskEvaluation(
                task_id=task.id,
                passed=valid_pr,
                score=1.0 if valid_pr else 0.0,
                reason="GitHub PR created respecting branch naming and bracketed title tag." if valid_pr else "PR missing or violated branch protection policies.",
            )

        # TASK 05: Sentry APM Latency & Resolution
        elif task.id == "task_05_sentry_p99_latency_investigation":
            resolved = any(
                inc.get("id") == "SENTRY-891"
                and inc.get("status") == "resolved"
                and len(inc.get("resolution_note", "")) >= 15
                for inc in incidents
            )
            return TaskEvaluation(
                task_id=task.id,
                passed=resolved,
                score=1.0 if resolved else 0.0,
                reason="Sentry incident SENTRY-891 resolved with detailed resolution note." if resolved else "Sentry incident unresolved or note too short (<15 chars).",
            )

        # TASK 06: Cross-Platform Enterprise Outage
        elif task.id == "task_06_cross_platform_enterprise_outage":
            has_linear = any(i.get("priority") == 1 for i in issues)
            has_slack = any(m.get("channel") == "#enterprise-escalations" and "[SLA-ALERT]" in m.get("text", "") for m in slack_messages)
            passed = has_linear and has_slack
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else 0.0,
                reason="P1 outage cross-platform response completed." if passed else "Incomplete cross-platform response.",
            )

        # TASK 07: Growth Tier Routing
        elif task.id == "task_07_growth_tier_routing":
            has_backlog = any(m.get("channel") == "#eng-backlog" for m in slack_messages)
            has_enterprise = any(m.get("channel") == "#enterprise-escalations" for m in slack_messages)
            passed = has_backlog and not has_enterprise
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else 0.0,
                reason="Growth tier properly routed to #eng-backlog without SLA-ALERT." if passed else "Incorrect channel routing for Growth customer.",
            )

        # TASK 08: GitHub CI Status & Merge
        elif task.id == "task_08_github_ci_status_merge":
            merged = any(p.get("number") == 42 and p.get("state") == "merged" for p in prs)
            return TaskEvaluation(
                task_id=task.id,
                passed=merged,
                score=1.0 if merged else 0.0,
                reason="PR #42 status verified and merged." if merged else "PR #42 not merged.",
            )

        # TASK 09: Security Incident Triage
        elif task.id == "task_09_security_incident_triage":
            sec_uuid = "550e8400-e29b-41d4-a716-446655440002"
            has_sec_linear = any(i.get("team_id") == sec_uuid and i.get("priority") == 1 for i in issues)
            has_sec_slack = any(m.get("channel") == "#sec-ops" for m in slack_messages)
            passed = has_sec_linear and has_sec_slack
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else 0.0,
                reason="Security issue routed to SEC team UUID and #sec-ops." if passed else "Missing SEC issue or #sec-ops message.",
            )

        # TASK 10: End-to-End DevOps Resilience
        elif task.id == "task_10_end_to_end_resilience":
            has_linear = len(issues) > 0
            has_pr = any(p.get("number") != 42 for p in prs)
            has_slack = len(slack_messages) > 0
            passed = has_linear and has_pr and has_slack
            return TaskEvaluation(
                task_id=task.id,
                passed=passed,
                score=1.0 if passed else 0.5,
                reason="Full DevOps chain executed (Linear + GitHub + Slack)." if passed else "Incomplete end-to-end chain.",
            )

        return TaskEvaluation(task_id=task.id, passed=False, score=0.0, reason="Unknown task")
