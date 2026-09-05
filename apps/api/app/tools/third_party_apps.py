import time
import json
from pathlib import Path
from typing import Any
from app.tools.base import Tool, ToolResult


class LinearIssueTool:
    name: str = "linear_api"
    description: str = (
        "Interact with Linear issue tracking API. "
        "Actions: 'list_teams', 'list_issues', 'create_issue', 'update_issue'. "
        "Use this tool to track software engineering tasks, assignees, and issue priorities."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_teams", "list_issues", "create_issue", "update_issue"],
                "description": "API action to perform",
            },
            "team_id": {"type": "string", "description": "36-char Team UUID (e.g. from list_teams)"},
            "title": {"type": "string", "description": "Title of the issue"},
            "description": {"type": "string", "description": "Issue description/markdown body"},
            "priority": {"type": "integer", "description": "Priority integer: 1 (Urgent), 2 (High), 3 (Normal), 4 (Low)"},
            "issue_id": {"type": "string", "description": "Issue ID for updates (e.g. LIN-101)"},
            "status": {"type": "string", "enum": ["Backlog", "Todo", "In Progress", "Done", "Canceled"]},
            "assignee_id": {"type": "string", "description": "User ID of assignee"},
        },
        "required": ["action"],
    }

    # Pre-seeded teams and state
    TEAMS = [
        {"id": "550e8400-e29b-41d4-a716-446655440001", "name": "Core Platform", "key": "CORE"},
        {"id": "550e8400-e29b-41d4-a716-446655440002", "name": "Security & Infra", "key": "SEC"},
        {"id": "550e8400-e29b-41d4-a716-446655440003", "name": "Customer Solutions", "key": "CS"},
    ]

    def _get_storage_path(self, workspace: Path) -> Path:
        p = workspace / ".linear_state.json"
        if not p.exists():
            default_state = {
                "issues": [
                    {
                        "id": "CORE-101",
                        "team_id": "550e8400-e29b-41d4-a716-446655440001",
                        "title": "Database connection pool exhaustion on spike",
                        "priority": 2,
                        "status": "Todo",
                        "assignee_id": "user_alex",
                    }
                ],
                "counter": 102,
            }
            p.write_text(json.dumps(default_state, indent=2))
        return p

    def _read_state(self, workspace: Path) -> dict[str, Any]:
        p = self._get_storage_path(workspace)
        try:
            return json.loads(p.read_text())
        except Exception:
            return {"issues": [], "counter": 100}

    def _write_state(self, workspace: Path, state: dict[str, Any]):
        p = self._get_storage_path(workspace)
        p.write_text(json.dumps(state, indent=2))

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start = time.perf_counter()
        action = input_data.get("action")

        if action == "list_teams":
            latency = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                output=json.dumps({"teams": self.TEAMS}, indent=2),
                latency_ms=latency,
                metadata={"teams_count": len(self.TEAMS)},
            )

        state = self._read_state(workspace)

        if action == "list_issues":
            latency = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                output=json.dumps({"issues": state.get("issues", [])}, indent=2),
                latency_ms=latency,
            )

        if action == "create_issue":
            team_id = input_data.get("team_id")
            title = input_data.get("title")
            priority = input_data.get("priority", 3)

            # Realistic API Quirk 1: team_id validation
            if not team_id:
                return ToolResult(
                    success=False,
                    output="Error 400 Bad Request: 'team_id' is required to create an issue.",
                    error="missing_team_id",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            valid_uuids = {t["id"] for t in self.TEAMS}
            if team_id not in valid_uuids:
                return ToolResult(
                    success=False,
                    output=(
                        f"Error 422 Unprocessable Entity: team_id '{team_id}' is invalid. "
                        f"Linear requires a 36-character team UUID (e.g. '550e8400-e29b-41d4-a716-446655440001'). "
                        f"Team slugs or names are not supported. Use action='list_teams' to query valid UUIDs."
                    ),
                    error="invalid_team_uuid",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            # Realistic API Quirk 2: priority must be integer 1-4
            if not isinstance(priority, int) or priority not in [1, 2, 3, 4]:
                return ToolResult(
                    success=False,
                    output=f"Error 400 Bad Request: priority must be integer 1 (Urgent), 2 (High), 3 (Normal), or 4 (Low). Received: {priority}",
                    error="invalid_priority_type",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            if not title:
                return ToolResult(
                    success=False,
                    output="Error 400 Bad Request: 'title' cannot be empty.",
                    error="missing_title",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            team_obj = next(t for t in self.TEAMS if t["id"] == team_id)
            counter = state.get("counter", 100)
            issue_id = f"{team_obj['key']}-{counter}"
            state["counter"] = counter + 1

            new_issue = {
                "id": issue_id,
                "team_id": team_id,
                "team_key": team_obj["key"],
                "title": title,
                "description": input_data.get("description", ""),
                "priority": priority,
                "status": input_data.get("status", "Todo"),
                "assignee_id": input_data.get("assignee_id"),
            }
            state.setdefault("issues", []).append(new_issue)
            self._write_state(workspace, state)

            return ToolResult(
                success=True,
                output=json.dumps({"success": True, "created_issue": new_issue}, indent=2),
                latency_ms=(time.perf_counter() - start) * 1000,
                metadata={"issue_id": issue_id},
            )

        if action == "update_issue":
            issue_id = input_data.get("issue_id")
            if not issue_id:
                return ToolResult(
                    success=False,
                    output="Error 400 Bad Request: 'issue_id' is required for update_issue.",
                    error="missing_issue_id",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            issues = state.get("issues", [])
            target = next((i for i in issues if i["id"] == issue_id), None)
            if not target:
                return ToolResult(
                    success=False,
                    output=f"Error 404 Not Found: Issue '{issue_id}' does not exist.",
                    error="issue_not_found",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            new_status = input_data.get("status")
            # Realistic Quirk 3: State transition to 'In Progress' requires an assignee
            if new_status == "In Progress":
                assignee = input_data.get("assignee_id") or target.get("assignee_id")
                if not assignee:
                    return ToolResult(
                        success=False,
                        output=(
                            "Error 409 Conflict: Workflow constraint violation. "
                            "An issue cannot be transitioned to 'In Progress' without an 'assignee_id'. "
                            "Please provide 'assignee_id' with update_issue."
                        ),
                        error="missing_assignee_for_in_progress",
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )

            if new_status:
                target["status"] = new_status
            if "priority" in input_data:
                target["priority"] = input_data["priority"]
            if "assignee_id" in input_data:
                target["assignee_id"] = input_data["assignee_id"]

            self._write_state(workspace, state)
            return ToolResult(
                success=True,
                output=json.dumps({"success": True, "updated_issue": target}, indent=2),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        return ToolResult(
            success=False,
            output=f"Error 400 Bad Request: Unknown action '{action}'",
            error="unknown_action",
            latency_ms=(time.perf_counter() - start) * 1000,
        )


class SlackChannelTool:
    name: str = "slack_api"
    description: str = (
        "Interact with Slack workspace API. "
        "Actions: 'list_channels', 'post_message'. "
        "Use this tool to communicate with engineering, security, and customer response channels."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list_channels", "post_message"]},
            "channel": {"type": "string", "description": "Channel name (e.g. #general, #sec-ops, #enterprise-escalations)"},
            "text": {"type": "string", "description": "Message content to post"},
            "metadata": {"type": "object", "description": "Optional payload metadata"},
        },
        "required": ["action"],
    }

    CHANNELS = [
        {"name": "#general", "topic": "Company-wide general discussions"},
        {"name": "#eng-backlog", "topic": "Engineering backlog notifications & standard bug tracking"},
        {"name": "#sec-ops", "topic": "Security and infrastructure incident alerts"},
        {"name": "#enterprise-escalations", "topic": "Urgent Tier-1 Enterprise customer SLA escalations"},
    ]

    def _get_storage_path(self, workspace: Path) -> Path:
        p = workspace / ".slack_messages.json"
        if not p.exists():
            p.write_text(json.dumps([], indent=2))
        return p

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start = time.perf_counter()
        action = input_data.get("action")

        if action == "list_channels":
            return ToolResult(
                success=True,
                output=json.dumps({"channels": self.CHANNELS}, indent=2),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        if action == "post_message":
            channel = input_data.get("channel")
            text = input_data.get("text", "")

            if not channel:
                return ToolResult(
                    success=False,
                    output="Error 400 Bad Request: 'channel' parameter is required.",
                    error="missing_channel",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            valid_names = {c["name"] for c in self.CHANNELS}
            if channel not in valid_names:
                return ToolResult(
                    success=False,
                    output=f"Error 404 Not Found: Channel '{channel}' does not exist. Available: {list(valid_names)}",
                    error="channel_not_found",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            # Realistic API Quirk 4: #enterprise-escalations policy validation
            if channel == "#enterprise-escalations":
                if "[SLA-ALERT]" not in text or "customer_id" not in text.lower():
                    return ToolResult(
                        success=False,
                        output=(
                            "Error 400 Bad Request: Enterprise channel policy violation. "
                            "Messages posted to #enterprise-escalations must contain the tag '[SLA-ALERT]' "
                            "and cite the customer identifier (e.g. 'customer_id: cust_...')."
                        ),
                        error="policy_violation_enterprise_channel",
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )

            # Save message
            p = self._get_storage_path(workspace)
            try:
                msgs = json.loads(p.read_text())
            except Exception:
                msgs = []
            msg_record = {"channel": channel, "text": text, "timestamp": time.time()}
            msgs.append(msg_record)
            p.write_text(json.dumps(msgs, indent=2))

            return ToolResult(
                success=True,
                output=json.dumps({"status": "ok", "delivered_to": channel, "message": text}),
                latency_ms=(time.perf_counter() - start) * 1000,
                metadata={"channel": channel},
            )

        return ToolResult(
            success=False,
            output=f"Error 400: Unknown action '{action}'",
            error="unknown_action",
            latency_ms=(time.perf_counter() - start) * 1000,
        )


class CustomerCRMTool:
    name: str = "crm_api"
    description: str = (
        "Interact with Customer Relationship Management (CRM) API. "
        "Actions: 'get_customer', 'list_customers'. "
        "Use this tool to look up customer tier, SLA agreements, and support contracts."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["get_customer", "list_customers"]},
            "customer_id": {"type": "string", "description": "Customer ID (e.g. cust_acme_corp)"},
        },
        "required": ["action"],
    }

    CUSTOMERS = {
        "cust_acme_corp": {
            "customer_id": "cust_acme_corp",
            "name": "Acme Global Enterprise",
            "tier": "Enterprise",
            "sla_response_hours": 1,
            "account_manager": "sarah@forgecorp.internal",
            "support_routing_rule": "Urgent enterprise incidents must be broadcast to #enterprise-escalations with [SLA-ALERT] and assigned Linear priority 1.",
        },
        "cust_globex": {
            "customer_id": "cust_globex",
            "name": "Globex Retailers",
            "tier": "Growth",
            "sla_response_hours": 8,
            "account_manager": "mike@forgecorp.internal",
            "support_routing_rule": "Standard bugs should be queued into #eng-backlog with priority 3.",
        },
        "cust_initech": {
            "customer_id": "cust_initech",
            "name": "Initech Systems",
            "tier": "Free",
            "sla_response_hours": 48,
            "account_manager": None,
            "support_routing_rule": "Community tier bugs queued into #eng-backlog with priority 4.",
        },
    }

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        start = time.perf_counter()
        action = input_data.get("action")

        if action == "list_customers":
            return ToolResult(
                success=True,
                output=json.dumps({"customers": list(self.CUSTOMERS.values())}, indent=2),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        if action == "get_customer":
            cid = input_data.get("customer_id")
            if not cid:
                return ToolResult(
                    success=False,
                    output="Error 400 Bad Request: 'customer_id' is required.",
                    error="missing_customer_id",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            data = self.CUSTOMERS.get(cid)
            if not data:
                return ToolResult(
                    success=False,
                    output=f"Error 404 Not Found: Customer '{cid}' not found in CRM.",
                    error="customer_not_found",
                    latency_ms=(time.perf_counter() - start) * 1000,
                )

            return ToolResult(
                success=True,
                output=json.dumps({"customer": data}, indent=2),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        return ToolResult(
            success=False,
            output=f"Error 400: Unknown action '{action}'",
            error="unknown_action",
            latency_ms=(time.perf_counter() - start) * 1000,
        )
