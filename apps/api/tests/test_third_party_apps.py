import pytest
from pathlib import Path
from app.tools.third_party_apps import LinearIssueTool, SlackChannelTool, CustomerCRMTool


@pytest.mark.asyncio
async def test_linear_tool_validation_and_quirks(tmp_path: Path):
    tool = LinearIssueTool()

    # 1. Query teams
    res_teams = await tool.execute({"action": "list_teams"}, tmp_path)
    assert res_teams.success is True
    assert "550e8400-e29b-41d4-a716-446655440001" in res_teams.output

    # 2. Attempt invalid team slug (Linear Quirk 1)
    res_bad = await tool.execute(
        {"action": "create_issue", "team_id": "CORE", "title": "DB Bug", "priority": 1},
        tmp_path,
    )
    assert res_bad.success is False
    assert "Error 422 Unprocessable Entity" in res_bad.output

    # 3. Create issue with correct UUID
    res_good = await tool.execute(
        {"action": "create_issue", "team_id": "550e8400-e29b-41d4-a716-446655440001", "title": "DB Bug", "priority": 1},
        tmp_path,
    )
    assert res_good.success is True
    assert "CORE-102" in res_good.output

    # 4. Status update to 'In Progress' requires assignee (Linear Quirk 3)
    res_prog_fail = await tool.execute(
        {"action": "update_issue", "issue_id": "CORE-102", "status": "In Progress"},
        tmp_path,
    )
    assert res_prog_fail.success is False
    assert "Error 409 Conflict" in res_prog_fail.output

    res_prog_ok = await tool.execute(
        {"action": "update_issue", "issue_id": "CORE-102", "status": "In Progress", "assignee_id": "user_1"},
        tmp_path,
    )
    assert res_prog_ok.success is True


@pytest.mark.asyncio
async def test_slack_tool_enterprise_policy(tmp_path: Path):
    tool = SlackChannelTool()

    # Posting without SLA tag to #enterprise-escalations fails
    res_fail = await tool.execute(
        {"action": "post_message", "channel": "#enterprise-escalations", "text": "Customer is down"},
        tmp_path,
    )
    assert res_fail.success is False
    assert "Error 400 Bad Request" in res_fail.output

    # Posting with SLA tag and customer ID succeeds
    res_ok = await tool.execute(
        {"action": "post_message", "channel": "#enterprise-escalations", "text": "[SLA-ALERT] customer_id: cust_acme_corp latency spike"},
        tmp_path,
    )
    assert res_ok.success is True


@pytest.mark.asyncio
async def test_crm_tool_contextual_lookup(tmp_path: Path):
    tool = CustomerCRMTool()

    res = await tool.execute({"action": "get_customer", "customer_id": "cust_acme_corp"}, tmp_path)
    assert res.success is True
    assert "Enterprise" in res.output
    assert "sla_response_hours" in res.output
