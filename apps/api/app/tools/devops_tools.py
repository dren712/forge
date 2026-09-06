import time
import json
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult


class GitHubTool:
    """
    Simulates GitHub API v3/v4 with realistic enterprise branch protection,
    pull request policies, and CI/CD status checks.
    """
    name: str = "github_api"
    description: str = (
        "Interact with GitHub repository API. "
        "Actions: 'list_branches', 'create_pull_request', 'check_pr_status', 'merge_pull_request'. "
        "Use this tool to manage pull requests, verify CI/CD checks, and merge hotfixes."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_branches", "create_pull_request", "check_pr_status", "merge_pull_request"],
                "description": "API action to perform",
            },
            "repo": {"type": "string", "description": "Repository in owner/name format e.g. 'acme/core-platform'"},
            "title": {"type": "string", "description": "PR title (must include issue tag e.g. '[LIN-101] Fix DB pool')"},
            "head_branch": {"type": "string", "description": "Source branch (e.g. 'fix/db-pool-leak')"},
            "base_branch": {"type": "string", "description": "Target branch (e.g. 'main')"},
            "body": {"type": "string", "description": "PR description markdown"},
            "pr_number": {"type": "integer", "description": "PR number for status or merge"},
        },
        "required": ["action"],
    }

    BRANCHES = [
        {"name": "main", "protected": True, "required_approvals": 2},
        {"name": "staging", "protected": False, "required_approvals": 0},
    ]

    def _get_storage_path(self, workspace: Path) -> Path:
        p = workspace / ".github_state.json"
        if not p.exists():
            default_state = {
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
            }
            p.write_text(json.dumps(default_state, indent=2))
        return p

    def _read_state(self, workspace: Path) -> dict[str, Any]:
        p = self._get_storage_path(workspace)
        try:
            return json.loads(p.read_text())
        except Exception:
            return {"pull_requests": [], "counter": 40}

    def _write_state(self, workspace: Path, state: dict[str, Any]):
        p = self._get_storage_path(workspace)
        p.write_text(json.dumps(state, indent=2))

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        action = input_data.get("action")

        if not action:
            return ToolResult(
                success=False,
                output="HTTP 400 Bad Request: 'action' parameter is required.",
                error="missing_action",
                error_type="missing_action",
                status_code=400,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        state = self._read_state(workspace)

        # ---------------- LIST BRANCHES ----------------
        if action == "list_branches":
            return ToolResult(
                success=True,
                output=json.dumps({"branches": self.BRANCHES, "total": len(self.BRANCHES)}, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- CREATE PULL REQUEST ----------------
        elif action == "create_pull_request":
            title = input_data.get("title")
            head = input_data.get("head_branch")
            base = input_data.get("base_branch", "main")
            body = input_data.get("body", "")

            if not title or not head:
                return ToolResult(
                    success=False,
                    output="HTTP 400 Bad Request: 'title' and 'head_branch' are required fields.",
                    error="missing_required_fields",
                    error_type="missing_required_fields",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            # Quirk 1: Branch naming policy
            valid_prefixes = ("fix/", "feat/", "hotfix/", "chore/")
            if not any(head.startswith(p) for p in valid_prefixes):
                return ToolResult(
                    success=False,
                    output=(
                        f"HTTP 403 Forbidden: Protected branch policy violation. "
                        f"Head branch '{head}' must start with one of: {list(valid_prefixes)}."
                    ),
                    error="branch_naming_policy_violation",
                    error_type="branch_naming_policy_violation",
                    status_code=403,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            # Quirk 2: PR Title must reference an issue or hotfix tag
            if not (title.startswith("[") and "]" in title):
                return ToolResult(
                    success=False,
                    output=(
                        "HTTP 422 Unprocessable Entity: PR title policy violation. "
                        "PR title must include issue ticket tag in brackets, e.g. '[LIN-101] Fix DB pool' or '[HOTFIX] Patch'."
                    ),
                    error="pr_title_policy_violation",
                    error_type="pr_title_policy_violation",
                    status_code=422,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            pr_num = state.get("counter", 43)
            new_pr = {
                "number": pr_num,
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "state": "open",
                "ci_status": "success",
                "approvals": 2 if "hotfix" in head else 1,
            }
            state.setdefault("pull_requests", []).append(new_pr)
            state["counter"] = pr_num + 1
            self._write_state(workspace, state)

            return ToolResult(
                success=True,
                output=json.dumps({"status": "created", "pr": new_pr}, indent=2),
                status_code=201,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- CHECK PR STATUS ----------------
        elif action == "check_pr_status":
            pr_number = input_data.get("pr_number")
            if not pr_number:
                return ToolResult(
                    success=False,
                    output="HTTP 400 Bad Request: 'pr_number' integer is required.",
                    error="missing_pr_number",
                    error_type="missing_pr_number",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            prs = state.get("pull_requests", [])
            matched = next((p for p in prs if p["number"] == pr_number), None)
            if not matched:
                return ToolResult(
                    success=False,
                    output=f"HTTP 404 Not Found: Pull request #{pr_number} not found.",
                    error="pr_not_found",
                    error_type="pr_not_found",
                    status_code=404,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            return ToolResult(
                success=True,
                output=json.dumps({
                    "pr_number": pr_number,
                    "title": matched["title"],
                    "state": matched["state"],
                    "ci_status": matched["ci_status"],
                    "approvals_count": matched["approvals"],
                    "mergeable": matched["ci_status"] == "success" and matched["approvals"] >= 2,
                }, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- MERGE PULL REQUEST ----------------
        elif action == "merge_pull_request":
            pr_number = input_data.get("pr_number")
            if not pr_number:
                return ToolResult(
                    success=False,
                    output="HTTP 400 Bad Request: 'pr_number' integer is required.",
                    error="missing_pr_number",
                    error_type="missing_pr_number",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            prs = state.get("pull_requests", [])
            matched = next((p for p in prs if p["number"] == pr_number), None)
            if not matched:
                return ToolResult(
                    success=False,
                    output=f"HTTP 404 Not Found: Pull request #{pr_number} not found.",
                    error="pr_not_found",
                    error_type="pr_not_found",
                    status_code=404,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            if matched["state"] == "merged":
                return ToolResult(
                    success=True,
                    output=json.dumps({"status": "already_merged", "pr_number": pr_number}),
                    status_code=200,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            if matched["approvals"] < 2:
                return ToolResult(
                    success=False,
                    output=(
                        f"HTTP 400 Bad Request: Pull request #{pr_number} cannot be merged. "
                        f"Branch protection requires at least 2 approvals (currently {matched['approvals']})."
                    ),
                    error="insufficient_approvals",
                    error_type="insufficient_approvals",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            matched["state"] = "merged"
            self._write_state(workspace, state)
            return ToolResult(
                success=True,
                output=json.dumps({"status": "merged", "pr_number": pr_number, "merged_at": time.time()}, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        return ToolResult(
            success=False,
            output=f"HTTP 400 Bad Request: Unknown action '{action}'.",
            error="unknown_action",
            error_type="unknown_action",
            status_code=400,
            latency_ms=(time.perf_counter() - start_time) * 1000.0,
        )


class SentryObservabilityTool:
    """
    Simulates Sentry / Datadog observability API with error traces,
    P99 latency spikes, service health metrics, and incident resolution policies.
    """
    name: str = "sentry_api"
    description: str = (
        "Interact with Sentry Observability and APM API. "
        "Actions: 'list_services', 'fetch_error_trace', 'query_alert_thresholds', 'resolve_incident'. "
        "Use this tool to investigate production error spikes, inspect stack traces, and manage alerts."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_services", "fetch_error_trace", "query_alert_thresholds", "resolve_incident"],
                "description": "API action to perform",
            },
            "service_slug": {"type": "string", "description": "Service slug e.g. 'billing-api', 'gateway'"},
            "incident_level": {"type": "string", "enum": ["P1", "P2", "P3"], "description": "Severity level"},
            "issue_id": {"type": "string", "description": "Sentry issue ID e.g. 'SENTRY-891'"},
            "resolution_note": {"type": "string", "description": "Detailed resolution summary (min 15 chars)"},
        },
        "required": ["action"],
    }

    SERVICES = [
        {"slug": "gateway", "uptime": 99.98, "p99_latency_ms": 42.0, "error_rate_pct": 0.02},
        {"slug": "billing-api", "uptime": 98.40, "p99_latency_ms": 2840.0, "error_rate_pct": 8.45},
        {"slug": "auth-service", "uptime": 99.95, "p99_latency_ms": 68.0, "error_rate_pct": 0.12},
    ]

    def _get_storage_path(self, workspace: Path) -> Path:
        p = workspace / ".sentry_state.json"
        if not p.exists():
            default_state = {
                "incidents": [
                    {
                        "id": "SENTRY-891",
                        "service": "billing-api",
                        "error_title": "TimeoutError: connection pool exhausted (stripe webhook retry)",
                        "error_rate_pct": 8.45,
                        "p99_latency_ms": 2840.0,
                        "status": "unresolved",
                        "level": "P1",
                    }
                ]
            }
            p.write_text(json.dumps(default_state, indent=2))
        return p

    def _read_state(self, workspace: Path) -> dict[str, Any]:
        p = self._get_storage_path(workspace)
        try:
            return json.loads(p.read_text())
        except Exception:
            return {"incidents": []}

    def _write_state(self, workspace: Path, state: dict[str, Any]):
        p = self._get_storage_path(workspace)
        p.write_text(json.dumps(state, indent=2))

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start_time = time.perf_counter()
        action = input_data.get("action")

        if not action:
            return ToolResult(
                success=False,
                output="HTTP 400 Bad Request: 'action' parameter is required.",
                error="missing_action",
                error_type="missing_action",
                status_code=400,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        state = self._read_state(workspace)

        # ---------------- LIST SERVICES ----------------
        if action == "list_services":
            return ToolResult(
                success=True,
                output=json.dumps({"services": self.SERVICES}, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- FETCH ERROR TRACE ----------------
        elif action == "fetch_error_trace":
            service_slug = input_data.get("service_slug")
            if not service_slug:
                return ToolResult(
                    success=False,
                    output="HTTP 400 Bad Request: 'service_slug' is required.",
                    error="missing_service_slug",
                    error_type="missing_service_slug",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            svc = next((s for s in self.SERVICES if s["slug"] == service_slug), None)
            if not svc:
                return ToolResult(
                    success=False,
                    output=f"HTTP 404 Not Found: Service '{service_slug}' not found.",
                    error="service_not_found",
                    error_type="service_not_found",
                    status_code=404,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            incidents = [inc for inc in state.get("incidents", []) if inc["service"] == service_slug]
            return ToolResult(
                success=True,
                output=json.dumps({
                    "service": service_slug,
                    "metrics": svc,
                    "active_incidents": incidents,
                    "stack_trace": (
                        "File '/app/billing/webhook.py', line 142 in handle_stripe\n"
                        "  conn = await db_pool.acquire(timeout=5.0)\n"
                        "asyncpg.exceptions.PoolAcquireTimeoutError: Pool exhausted (max 50 connections)."
                    ) if svc["error_rate_pct"] > 1.0 else "None",
                }, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- QUERY ALERT THRESHOLDS ----------------
        elif action == "query_alert_thresholds":
            thresholds = {
                "P1": {"error_rate_pct_gt": 5.0, "p99_latency_ms_gt": 2000, "escalation": "Immediate page to on-call & #enterprise-escalations"},
                "P2": {"error_rate_pct_gt": 1.0, "p99_latency_ms_gt": 500, "escalation": "Alert to #eng-backlog"},
                "P3": {"error_rate_pct_gt": 0.1, "p99_latency_ms_gt": 200, "escalation": "Daily report"},
            }
            return ToolResult(
                success=True,
                output=json.dumps({"alert_policy": thresholds}, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # ---------------- RESOLVE INCIDENT ----------------
        elif action == "resolve_incident":
            issue_id = input_data.get("issue_id")
            note = input_data.get("resolution_note")

            if not issue_id:
                return ToolResult(
                    success=False,
                    output="HTTP 400 Bad Request: 'issue_id' is required.",
                    error="missing_issue_id",
                    error_type="missing_issue_id",
                    status_code=400,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            if not note or len(note.strip()) < 15:
                return ToolResult(
                    success=False,
                    output="HTTP 422 Unprocessable Entity: 'resolution_note' must be detailed (min 15 characters).",
                    error="invalid_resolution_note",
                    error_type="invalid_resolution_note",
                    status_code=422,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            incidents = state.get("incidents", [])
            inc = next((i for i in incidents if i["id"] == issue_id), None)
            if not inc:
                return ToolResult(
                    success=False,
                    output=f"HTTP 404 Not Found: Incident '{issue_id}' not found.",
                    error="incident_not_found",
                    error_type="incident_not_found",
                    status_code=404,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            inc["status"] = "resolved"
            inc["resolution_note"] = note.strip()
            self._write_state(workspace, state)

            return ToolResult(
                success=True,
                output=json.dumps({"status": "resolved", "incident": inc}, indent=2),
                status_code=200,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        return ToolResult(
            success=False,
            output=f"HTTP 400 Bad Request: Unknown action '{action}'.",
            error="unknown_action",
            error_type="unknown_action",
            status_code=400,
            latency_ms=(time.perf_counter() - start_time) * 1000.0,
        )
