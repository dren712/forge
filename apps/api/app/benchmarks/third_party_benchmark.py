import json
from pathlib import Path
from typing import List, Any
from app.benchmarks.base import BenchmarkTask, TaskEvaluation, TaskCheck
from app.agents.state import AgentState


class ThirdPartyAppBenchmark:
    benchmark_id: str = "third_party_automation"
    name: str = "third_party_automation"
    version: str = "2.0.0"
    evaluator_version: str = "2.0.0"
    created_at: str = "2026-03-01T00:00:00Z"

    TASKS = [
        BenchmarkTask(
            id="task_01_api_discovery",
            title="Linear API Discovery: Resolve Team UUID & Priority Format",
            description="Create an urgent incident issue for 'Database Pool Exhaustion' under the Core Platform team.",
            goal="Engineers report connection pool exhaustion. Create tracking issue in Linear under Core Platform with Urgent priority.",
            repository="multi_app_workspace",
            issue="Engineers report connection pool exhaustion. Create tracking issue in Linear under Core Platform with Urgent priority.",
            expected_behavior="Issue created with team_id='550e8400-e29b-41d4-a716-446655440001' and priority=1.",
            allowed_tools=["linear_api"],
            constraints=["Must target Core Platform team", "Must set priority to Urgent (1)"],
            hidden_constraints=["Linear rejects team slugs like 'CORE'; requires UUID '550e8400-e29b-41d4-a716-446655440001'"],
            primary_skill="API discovery & UUID schema resolution",
            main_failure_mode="TOOL_EXECUTION_FAILURE / Schema rejection",
            starting_state={"issues": [], "counter": 101},
        ),
        BenchmarkTask(
            id="task_02_contextual_sla_routing",
            title="Cross-App Contextual Routing: Enterprise SLA Escalation",
            description="Customer 'cust_acme_corp' reported API latency spike. Inspect CRM for SLA contract rules and execute required routing.",
            goal="Incoming support alert for 'cust_acme_corp'. Look up their SLA tier in CRM and execute the required channel alert and issue creation.",
            repository="multi_app_workspace",
            issue="Incoming support alert for 'cust_acme_corp'. Look up their SLA tier in CRM and execute the required channel alert and issue creation.",
            expected_behavior="Message posted to #enterprise-escalations with [SLA-ALERT] and Linear issue created with priority 1.",
            allowed_tools=["crm_api", "slack_api", "linear_api"],
            constraints=["Look up customer tier in CRM before routing", "Create tracking issue"],
            hidden_constraints=["Enterprise customers must alert #enterprise-escalations with '[SLA-ALERT]' and customer_id in text"],
            primary_skill="Contextual SLA routing & policy enforcement",
            main_failure_mode="CONTEXT_FAILURE / Hidden policy violation",
            starting_state={"issues": [], "messages": []},
        ),
        BenchmarkTask(
            id="task_03_repeat_efficiency",
            title="Repeat Execution: Zero-Exploration Incident Resolution",
            description="Customer 'cust_acme_corp' reported payment webhook failure. Execute enterprise escalation with minimal tool calls.",
            goal="Payment webhook failure for 'cust_acme_corp'. Execute standard enterprise escalation with zero exploratory errors.",
            repository="multi_app_workspace",
            issue="Payment webhook failure for 'cust_acme_corp'. Execute standard enterprise escalation.",
            expected_behavior="Direct execution without exploratory errors, posting to Slack and Linear with optimal parameters.",
            allowed_tools=["crm_api", "slack_api", "linear_api"],
            constraints=["Must alert #enterprise-escalations with [SLA-ALERT]", "Must create Linear priority 1 issue"],
            hidden_constraints=["Optimal path requires exact UUID and correct Slack format without trial-and-error discovery"],
            primary_skill="Repeat execution efficiency & parameter precision",
            main_failure_mode="TOOL_SELECTION_FAILURE / Exploration redundancy",
            starting_state={"issues": [], "messages": []},
        ),
        BenchmarkTask(
            id="task_04_github_protected_branch_hotfix",
            title="GitHub PR Policy: Protected Branch Hotfix",
            description="Create a hotfix pull request for '[LIN-101] Fix DB pool' from branch 'fix/db-pool-leak' to 'main'.",
            goal="Hotfix ready for DB pool. Create PR on GitHub targeting main following branch naming and title conventions.",
            repository="multi_app_workspace",
            issue="Hotfix ready for DB pool. Create PR on GitHub targeting main following branch naming and title conventions.",
            expected_behavior="PR created with head branch prefix 'fix/' and title containing bracketed issue tag '[LIN-101]'.",
            allowed_tools=["github_api"],
            constraints=["Must target base branch main", "Must link tracking issue in title"],
            hidden_constraints=["Protected branch policy requires head branch prefix 'fix/' or 'hotfix/' and title with '[LIN-...] '"],
            primary_skill="GitHub protected branch policy enforcement",
            main_failure_mode="TOOL_EXECUTION_FAILURE / Policy violation",
            starting_state={"pull_requests": [{"number": 42, "state": "open"}], "counter": 43},
        ),
        BenchmarkTask(
            id="task_05_sentry_p99_latency_investigation",
            title="Sentry APM: Latency Spike Investigation & Resolution",
            description="Investigate high error rate on 'billing-api' and resolve incident 'SENTRY-891'.",
            goal="Billing API alerts are firing. Query Sentry for error traces on billing-api and resolve incident SENTRY-891 with a detailed note.",
            repository="multi_app_workspace",
            issue="Billing API alerts are firing. Query Sentry for error traces on billing-api and resolve incident SENTRY-891 with a detailed note.",
            expected_behavior="Fetched error trace and resolved SENTRY-891 with resolution_note >= 15 characters.",
            allowed_tools=["sentry_api"],
            constraints=["Target service billing-api", "Provide comprehensive resolution documentation"],
            hidden_constraints=["Resolution API requires resolution_note >= 15 characters; shorter notes are rejected"],
            primary_skill="APM triage & verified state resolution",
            main_failure_mode="VERIFICATION_FAILURE / Resolution constraint error",
            starting_state={"incidents": [{"id": "SENTRY-891", "service": "billing-api", "status": "unresolved"}]},
        ),
        BenchmarkTask(
            id="task_06_cross_platform_enterprise_outage",
            title="Cross-Platform Orchestration: P1 Outage Incident Response",
            description="Handle P1 outage: Investigate Sentry, file Linear issue under Core Platform, and alert #enterprise-escalations.",
            goal="Critical outage reported. Check Sentry billing-api, create priority 1 Linear issue with UUID, and notify Slack #enterprise-escalations with [SLA-ALERT].",
            repository="multi_app_workspace",
            issue="Critical outage reported. Check Sentry billing-api, create priority 1 Linear issue with UUID, and notify Slack #enterprise-escalations with [SLA-ALERT].",
            expected_behavior="Linear priority 1 issue created and Slack message posted to #enterprise-escalations with [SLA-ALERT].",
            allowed_tools=["sentry_api", "linear_api", "slack_api"],
            constraints=["Coordinate cross-platform triage across APM, issue tracker, and communications"],
            hidden_constraints=["Must connect Sentry incident context to Linear issue description and Slack escalation"],
            primary_skill="Multi-tool planning & cross-platform sequencing",
            main_failure_mode="PLANNING_FAILURE / Incomplete workflow",
            starting_state={"issues": [], "messages": [], "incidents": [{"id": "SENTRY-891", "status": "unresolved"}]},
        ),
        BenchmarkTask(
            id="task_07_growth_tier_routing",
            title="SLA Tier Differentiation: Growth Customer Routing",
            description="Customer 'cust_growth_start' reported minor UI bug. Check CRM tier and route appropriately.",
            goal="Ticket from 'cust_growth_start'. Check CRM tier. Do NOT post to #enterprise-escalations. Post to #eng-backlog with standard priority.",
            repository="multi_app_workspace",
            issue="Ticket from 'cust_growth_start'. Check CRM tier. Do NOT post to #enterprise-escalations. Post to #eng-backlog with standard priority.",
            expected_behavior="CRM checked and notification sent to #eng-backlog without enterprise alert tag.",
            allowed_tools=["crm_api", "slack_api"],
            constraints=["Check CRM tier first", "Route appropriately without escalating to executive channels"],
            hidden_constraints=["Growth tier customers must NEVER route to #enterprise-escalations; violation incurs penalty"],
            primary_skill="Policy-aware routing & negative constraint adherence",
            main_failure_mode="REASONING_FAILURE / Policy violation (over-escalation)",
            starting_state={"messages": []},
        ),
        BenchmarkTask(
            id="task_08_github_ci_status_merge",
            title="GitHub Status Gate: Verify & Merge PR",
            description="Check status of Pull Request #42 and merge it if CI checks pass.",
            goal="Verify CI/CD status of PR #42 and execute merge once passing.",
            repository="multi_app_workspace",
            issue="Verify CI/CD status of PR #42 and execute merge once passing.",
            expected_behavior="Status checked and PR #42 merged successfully.",
            allowed_tools=["github_api"],
            constraints=["Verify CI checks and approval count before merging"],
            hidden_constraints=["Merge gate requires ci_status=='success' and approvals>=2; both are satisfied by PR #42"],
            primary_skill="State verification gate & release promotion",
            main_failure_mode="VERIFICATION_FAILURE / Premature or missing merge",
            starting_state={"pull_requests": [{"number": 42, "state": "open", "ci_status": "success", "approvals": 2}]},
        ),
        BenchmarkTask(
            id="task_09_security_incident_triage",
            title="Security Policy Routing: Security & Infra Team UUID",
            description="File urgent security patch issue under 'Security & Infra' team and notify #sec-ops.",
            goal="Vulnerability report in gateway auth. Create Linear issue under Security & Infra (UUID) with priority 1 and post to #sec-ops.",
            repository="multi_app_workspace",
            issue="Vulnerability report in gateway auth. Create Linear issue under Security & Infra (UUID) with priority 1 and post to #sec-ops.",
            expected_behavior="Linear issue created with SEC UUID '550e8400-e29b-41d4-a716-446655440002' and Slack posted to #sec-ops.",
            allowed_tools=["linear_api", "slack_api"],
            constraints=["Route to Security & Infra team", "Post notification to #sec-ops channel"],
            hidden_constraints=["Security & Infra team UUID is '550e8400-e29b-41d4-a716-446655440002', distinct from Core Platform"],
            primary_skill="Domain-specific team resolution & channel isolation",
            main_failure_mode="TOOL_SELECTION_FAILURE / Wrong team UUID",
            starting_state={"issues": [], "messages": []},
        ),
        BenchmarkTask(
            id="task_10_end_to_end_resilience",
            title="End-to-End Enterprise Resolution: From Sentry to GitHub to Slack",
            description="Complete full DevOps workflow: Sentry trace -> Linear issue -> GitHub Hotfix PR -> Slack debrief.",
            goal="Full incident mitigation: Trace billing error in Sentry, file Linear issue, create GitHub PR '[LIN-102] Hotfix' from 'fix/stripe-webhook', and post debrief to Slack.",
            repository="multi_app_workspace",
            issue="Full incident mitigation: Trace billing error in Sentry, file Linear issue, create GitHub PR '[LIN-102] Hotfix' from 'fix/stripe-webhook', and post debrief to Slack.",
            expected_behavior="GitHub PR created, Linear issue created, and Slack notification delivered.",
            allowed_tools=["sentry_api", "linear_api", "github_api", "slack_api"],
            constraints=["Execute entire lifecycle from alert triage to release preparation and team communication"],
            hidden_constraints=["Requires chaining context: Sentry error title -> Linear issue title -> PR title & branch -> Slack message"],
            primary_skill="End-to-end multi-agent orchestration & resilience",
            main_failure_mode="RECOVERY_FAILURE / Premature task termination",
            starting_state={"issues": [], "messages": [], "pull_requests": [{"number": 42, "state": "open"}], "incidents": [{"id": "SENTRY-891", "status": "unresolved"}]},
        ),
    ]

    def list_tasks(self) -> List[BenchmarkTask]:
        return list(self.TASKS)

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Sets up pristine enterprise state files in the task workspace."""
        workspace.mkdir(parents=True, exist_ok=True)
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

    async def reset_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Wipes any mutations and restores baseline task state."""
        state_files = [
            ".linear_state.json",
            ".slack_messages.json",
            ".github_state.json",
            ".sentry_state.json",
        ]
        for fname in state_files:
            fpath = workspace / fname
            if fpath.exists():
                fpath.unlink()
        await self.setup_task(task, workspace)

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        """
        Deterministically inspects real state files in the workspace.
        Does NOT rely solely on agent natural language claims.
        Returns structured checks with explicit evidence.
        """
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

        checks: list[TaskCheck] = []
        failures: list[str] = []

        if task.id == "task_01_api_discovery":
            chk_issue = TaskCheck(
                name="linear_issue_created",
                passed=len(issues) > 0,
                evidence=f"Found {len(issues)} issue(s) in Linear state file",
            )
            checks.append(chk_issue)

            correct_team = any(i.get("team_id") == "550e8400-e29b-41d4-a716-446655440001" for i in issues)
            chk_team = TaskCheck(
                name="correct_team_uuid",
                passed=correct_team,
                evidence=f"Core Platform UUID matched: {correct_team} (issues: {[i.get('team_id') for i in issues]})",
            )
            checks.append(chk_team)

            correct_prio = any(i.get("priority") == 1 for i in issues)
            chk_prio = TaskCheck(
                name="urgent_priority_one",
                passed=correct_prio,
                evidence=f"Priority 1 matched: {correct_prio} (priorities: {[i.get('priority') for i in issues]})",
            )
            checks.append(chk_prio)

            all_passed = chk_issue.passed and chk_team.passed and chk_prio.passed
            if not all_passed:
                failures.append("Missing valid Linear issue with team UUID 550e8400-e29b-41d4-a716-446655440001 and priority 1")

            score = 1.0 if all_passed else (0.5 if chk_issue.passed else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Linear issue created with correct team UUID and priority=1." if all_passed else "Failed Linear UUID or priority check.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_02_contextual_sla_routing":
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                and "cust_acme_corp" in m.get("text", "")
                for m in slack_messages
            )
            chk_slack = TaskCheck(
                name="slack_enterprise_sla_alert",
                passed=has_slack,
                evidence=f"Alert in #enterprise-escalations with [SLA-ALERT] and customer: {has_slack}",
            )
            checks.append(chk_slack)

            has_linear = any(i.get("priority") == 1 for i in issues)
            chk_linear = TaskCheck(
                name="linear_urgent_issue",
                passed=has_linear,
                evidence=f"Linear issue with priority 1 exists: {has_linear}",
            )
            checks.append(chk_linear)

            all_passed = has_slack and has_linear
            if not has_slack:
                failures.append("Slack message missing from #enterprise-escalations or missing [SLA-ALERT]")
            if not has_linear:
                failures.append("Linear priority 1 issue missing")

            score = 1.0 if all_passed else (0.5 if (has_slack or has_linear) else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Enterprise SLA escalation complete (Slack + Linear)." if all_passed else "Missing Slack SLA tag or Linear priority 1 issue.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_03_repeat_efficiency":
            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                for m in slack_messages
            )
            chk_slack = TaskCheck(
                name="slack_escalation_delivered",
                passed=has_slack,
                evidence=f"Message delivered to #enterprise-escalations: {has_slack}",
            )
            checks.append(chk_slack)

            has_linear = any(i.get("priority") == 1 for i in issues)
            chk_linear = TaskCheck(
                name="linear_issue_created",
                passed=has_linear,
                evidence=f"Linear priority 1 issue exists: {has_linear}",
            )
            checks.append(chk_linear)

            tool_errors = len([tr for tr in state.tool_results if not tr.get("success", False)])
            chk_errors = TaskCheck(
                name="zero_or_low_tool_errors",
                passed=(tool_errors <= 1),
                evidence=f"Recorded {tool_errors} tool execution error(s)",
            )
            checks.append(chk_errors)

            all_passed = has_slack and has_linear
            score = 1.0 if all_passed else 0.0
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Repeat incident triage completed successfully." if all_passed else "Repeat incident triage failed.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_04_github_protected_branch_hotfix":
            new_prs = [p for p in prs if p.get("number") != 42]
            chk_exists = TaskCheck(
                name="new_pr_created",
                passed=len(new_prs) > 0,
                evidence=f"Created {len(new_prs)} new PR(s) in GitHub state",
            )
            checks.append(chk_exists)

            valid_branch = any(p.get("head", "").startswith(("fix/", "hotfix/")) for p in new_prs)
            chk_branch = TaskCheck(
                name="valid_head_branch_prefix",
                passed=valid_branch,
                evidence=f"Branch prefix fix/ or hotfix/ matched: {valid_branch}",
            )
            checks.append(chk_branch)

            bracketed_title = any("[" in p.get("title", "") and "]" in p.get("title", "") for p in new_prs)
            chk_title = TaskCheck(
                name="bracketed_issue_tag_in_title",
                passed=bracketed_title,
                evidence=f"Bracketed title tag matched: {bracketed_title}",
            )
            checks.append(chk_title)

            all_passed = chk_exists.passed and chk_branch.passed and chk_title.passed
            if not all_passed:
                failures.append("GitHub PR missing or violated branch naming/title convention")

            score = 1.0 if all_passed else (0.5 if chk_exists.passed else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="GitHub PR created respecting branch naming and bracketed title tag." if all_passed else "PR missing or violated branch protection policies.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_05_sentry_p99_latency_investigation":
            sentry_891 = next((inc for inc in incidents if inc.get("id") == "SENTRY-891"), None)
            is_resolved = (sentry_891 is not None and sentry_891.get("status") == "resolved")
            chk_resolved = TaskCheck(
                name="incident_sentry_891_resolved",
                passed=is_resolved,
                evidence=f"SENTRY-891 status is '{sentry_891.get('status') if sentry_891 else 'missing'}'",
            )
            checks.append(chk_resolved)

            note_len = len(sentry_891.get("resolution_note", "")) if sentry_891 else 0
            chk_note = TaskCheck(
                name="resolution_note_adequate_length",
                passed=(note_len >= 15),
                evidence=f"Resolution note length: {note_len} characters (minimum: 15)",
            )
            checks.append(chk_note)

            all_passed = chk_resolved.passed and chk_note.passed
            if not is_resolved:
                failures.append("Incident SENTRY-891 remains unresolved")
            if note_len < 15:
                failures.append(f"Resolution note is too short ({note_len} < 15 chars)")

            score = 1.0 if all_passed else 0.0
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Sentry incident SENTRY-891 resolved with detailed resolution note." if all_passed else "Sentry incident unresolved or note too short (<15 chars).",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_06_cross_platform_enterprise_outage":
            has_linear = any(i.get("priority") == 1 for i in issues)
            chk_linear = TaskCheck(
                name="linear_urgent_issue_created",
                passed=has_linear,
                evidence=f"Linear priority 1 issue found: {has_linear}",
            )
            checks.append(chk_linear)

            has_slack = any(
                m.get("channel") == "#enterprise-escalations"
                and "[SLA-ALERT]" in m.get("text", "")
                for m in slack_messages
            )
            chk_slack = TaskCheck(
                name="slack_enterprise_escalation",
                passed=has_slack,
                evidence=f"Slack alert in #enterprise-escalations with [SLA-ALERT]: {has_slack}",
            )
            checks.append(chk_slack)

            all_passed = has_linear and has_slack
            if not all_passed:
                failures.append("Incomplete cross-platform response (requires both Linear P1 and Slack SLA alert)")

            score = 1.0 if all_passed else (0.5 if (has_linear or has_slack) else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="P1 outage cross-platform response completed." if all_passed else "Incomplete cross-platform response.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_07_growth_tier_routing":
            has_backlog = any(m.get("channel") == "#eng-backlog" for m in slack_messages)
            chk_backlog = TaskCheck(
                name="routed_to_eng_backlog",
                passed=has_backlog,
                evidence=f"Message routed to #eng-backlog: {has_backlog}",
            )
            checks.append(chk_backlog)

            has_enterprise = any(m.get("channel") == "#enterprise-escalations" for m in slack_messages)
            chk_no_escalation = TaskCheck(
                name="no_improper_enterprise_escalation",
                passed=(not has_enterprise),
                evidence=f"Avoided improper #enterprise-escalations alert: {not has_enterprise}",
            )
            checks.append(chk_no_escalation)

            all_passed = has_backlog and not has_enterprise
            if not has_backlog:
                failures.append("Failed to route customer issue to #eng-backlog")
            if has_enterprise:
                failures.append("Negative constraint violated: posted to #enterprise-escalations for Growth customer")

            score = 1.0 if all_passed else 0.0
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Growth tier properly routed to #eng-backlog without SLA-ALERT." if all_passed else "Incorrect channel routing for Growth customer.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_08_github_ci_status_merge":
            pr_42 = next((p for p in prs if p.get("number") == 42), None)
            merged = (pr_42 is not None and pr_42.get("state") == "merged")
            chk_merged = TaskCheck(
                name="pr_42_status_merged",
                passed=merged,
                evidence=f"PR #42 state: '{pr_42.get('state') if pr_42 else 'missing'}'",
            )
            checks.append(chk_merged)

            if not merged:
                failures.append("PR #42 not merged after CI status verification")

            score = 1.0 if merged else 0.0
            return TaskEvaluation(
                task_id=task.id,
                passed=merged,
                score=score,
                reason="PR #42 status verified and merged." if merged else "PR #42 not merged.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_09_security_incident_triage":
            sec_uuid = "550e8400-e29b-41d4-a716-446655440002"
            has_sec_linear = any(i.get("team_id") == sec_uuid and i.get("priority") == 1 for i in issues)
            chk_sec_linear = TaskCheck(
                name="security_team_uuid_priority_one",
                passed=has_sec_linear,
                evidence=f"Linear issue with Security UUID {sec_uuid} and priority 1: {has_sec_linear}",
            )
            checks.append(chk_sec_linear)

            has_sec_slack = any(m.get("channel") == "#sec-ops" for m in slack_messages)
            chk_sec_slack = TaskCheck(
                name="sec_ops_slack_notification",
                passed=has_sec_slack,
                evidence=f"Notification posted to #sec-ops: {has_sec_slack}",
            )
            checks.append(chk_sec_slack)

            all_passed = has_sec_linear and has_sec_slack
            if not has_sec_linear:
                failures.append("Missing Linear issue with Security & Infra UUID and priority 1")
            if not has_sec_slack:
                failures.append("Missing Slack alert to #sec-ops channel")

            score = 1.0 if all_passed else (0.5 if (has_sec_linear or has_sec_slack) else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Security issue routed to SEC team UUID and #sec-ops." if all_passed else "Missing SEC issue or #sec-ops message.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        elif task.id == "task_10_end_to_end_resilience":
            has_linear = len(issues) > 0
            chk_linear = TaskCheck(
                name="linear_issue_created",
                passed=has_linear,
                evidence=f"Created {len(issues)} issue(s) in Linear",
            )
            checks.append(chk_linear)

            has_pr = any(p.get("number") != 42 for p in prs)
            chk_pr = TaskCheck(
                name="github_hotfix_pr_created",
                passed=has_pr,
                evidence=f"Created hotfix PR in GitHub: {has_pr}",
            )
            checks.append(chk_pr)

            has_slack = len(slack_messages) > 0
            chk_slack = TaskCheck(
                name="slack_notification_delivered",
                passed=has_slack,
                evidence=f"Delivered {len(slack_messages)} message(s) to Slack",
            )
            checks.append(chk_slack)

            all_passed = has_linear and has_pr and has_slack
            if not all_passed:
                failures.append("Incomplete end-to-end DevOps chain")

            score = 1.0 if all_passed else (0.5 if (has_linear or has_pr or has_slack) else 0.0)
            return TaskEvaluation(
                task_id=task.id,
                passed=all_passed,
                score=score,
                reason="Full DevOps chain executed (Linear + GitHub + Slack)." if all_passed else "Incomplete end-to-end chain.",
                checks=checks,
                tool_calls=state.tool_call_count,
                failures=failures,
                verification_passed=state.verification_passed,
            )

        return TaskEvaluation(
            task_id=task.id,
            passed=False,
            score=0.0,
            reason="Unknown task ID",
            checks=[TaskCheck(name="task_recognized", passed=False, evidence="Task ID not recognized")],
            failures=["Unknown task ID"],
        )
