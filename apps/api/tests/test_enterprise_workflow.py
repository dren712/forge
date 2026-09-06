import pytest
import json
from pathlib import Path

from app.tools.third_party_apps import LinearIssueTool, SlackChannelTool, CustomerCRMTool
from app.tools.devops_tools import GitHubTool, SentryObservabilityTool
from app.agents.verifier import AgentVerifier, VerificationResult


@pytest.mark.asyncio
async def test_enterprise_cross_tool_workflow(tmp_path: Path):
    """
    Tests the complete 5-tool enterprise incident escalation and resolution workflow:
    CRM -> Sentry -> Linear -> Slack -> GitHub -> Sentry -> Verification
    """
    crm = CustomerCRMTool()
    sentry = SentryObservabilityTool()
    linear = LinearIssueTool()
    slack = SlackChannelTool()
    github = GitHubTool()

    # Step 1: Query CRM for customer contract & SLA
    res_crm = await crm.execute({"action": "get_customer", "customer_id": "cust_acme_corp"}, tmp_path)
    assert res_crm.success is True
    assert res_crm.status_code == 200
    crm_data = json.loads(res_crm.output)["customer"]
    assert crm_data["tier"] == "Enterprise"
    assert crm_data["sla_response_hours"] == 1

    # Step 2: Sentry investigation of active incident
    res_trace = await sentry.execute({"action": "fetch_error_trace", "service_slug": "billing-api"}, tmp_path)
    assert res_trace.success is True
    assert res_trace.status_code == 200
    assert "PoolAcquireTimeoutError" in res_trace.output

    # Step 3: Create Linear incident ticket for this customer
    # Test UUID enforcement (Quirk 1: team slugs reject with 422)
    res_lin_bad_team = await linear.execute(
        {"action": "create_issue", "team_id": "CORE", "title": "DB Connection pool timeout", "priority": 1},
        tmp_path,
    )
    assert res_lin_bad_team.success is False
    assert res_lin_bad_team.status_code == 422
    assert res_lin_bad_team.error_type == "invalid_team_uuid"

    # Create unassigned issue with valid team UUID
    res_lin_created = await linear.execute(
        {
            "action": "create_issue",
            "team_id": "550e8400-e29b-41d4-a716-446655440001",
            "title": "[P1 Incident] Database pool exhaustion in billing-api",
            "priority": 1,
        },
        tmp_path,
    )
    assert res_lin_created.success is True
    assert res_lin_created.status_code == 201
    created_issue_id = json.loads(res_lin_created.output)["created_issue"]["id"]

    # Quirk 3: Updating unassigned issue to 'In Progress' requires assignee_id (fails with 409)
    res_lin_fail = await linear.execute(
        {"action": "update_issue", "issue_id": created_issue_id, "status": "In Progress"},
        tmp_path,
    )
    assert res_lin_fail.success is False
    assert res_lin_fail.status_code == 409
    assert res_lin_fail.error_type == "missing_assignee_for_in_progress"

    # Valid update providing assignee_id
    res_lin_ok = await linear.execute(
        {
            "action": "update_issue",
            "issue_id": created_issue_id,
            "status": "In Progress",
            "priority": 1,
            "assignee_id": "user_alex",
        },
        tmp_path,
    )
    assert res_lin_ok.success is True
    assert res_lin_ok.status_code == 200

    # Step 4: Broadcast urgent escalation to Slack #enterprise-escalations
    # Verify post without [SLA-ALERT] fails policy check with 400
    res_slack_fail = await slack.execute(
        {
            "action": "post_message",
            "channel": "#enterprise-escalations",
            "text": "Database pool exhausted on billing api",
        },
        tmp_path,
    )
    assert res_slack_fail.success is False
    assert res_slack_fail.status_code == 400
    assert res_slack_fail.error_type == "policy_violation_enterprise_channel"

    # Valid message satisfying channel policy
    res_slack_ok = await slack.execute(
        {
            "action": "post_message",
            "channel": "#enterprise-escalations",
            "text": f"[SLA-ALERT] customer_id: cust_acme_corp P1 incident: DB connection pool timeout ({created_issue_id})",
        },
        tmp_path,
    )
    assert res_slack_ok.success is True
    assert res_slack_ok.status_code == 200

    # Step 5: GitHub pull request and merge
    # Test branch policy rejection
    res_gh_bad = await github.execute(
        {
            "action": "create_pull_request",
            "title": f"[{created_issue_id}] Fix DB pool",
            "head_branch": "patch-pool",
        },
        tmp_path,
    )
    assert res_gh_bad.success is False
    assert res_gh_bad.status_code == 403
    assert res_gh_bad.error_type == "branch_naming_policy_violation"

    # Valid hotfix PR creation (hotfix prefix gets 2 approvals by policy)
    res_gh_pr = await github.execute(
        {
            "action": "create_pull_request",
            "title": f"[{created_issue_id}] Increase connection pool size and timeout backoff",
            "head_branch": "hotfix/db-pool-increase",
            "base_branch": "main",
            "body": "Fixes connection exhaustion under spike load",
        },
        tmp_path,
    )
    assert res_gh_pr.success is True
    assert res_gh_pr.status_code == 201
    pr_num = json.loads(res_gh_pr.output)["pr"]["number"]

    # Merge hotfix PR
    res_gh_merge = await github.execute(
        {"action": "merge_pull_request", "pr_number": pr_num},
        tmp_path,
    )
    assert res_gh_merge.success is True
    assert res_gh_merge.status_code == 200

    # Step 6: Sentry incident resolution
    # Short note fails with 422
    res_sentry_fail = await sentry.execute(
        {"action": "resolve_incident", "issue_id": "SENTRY-891", "resolution_note": "fixed"},
        tmp_path,
    )
    assert res_sentry_fail.success is False
    assert res_sentry_fail.status_code == 422
    assert res_sentry_fail.error_type == "invalid_resolution_note"

    # Valid resolution note >= 15 chars
    res_sentry_ok = await sentry.execute(
        {
            "action": "resolve_incident",
            "issue_id": "SENTRY-891",
            "resolution_note": f"Merged hotfix PR #{pr_num} resolving ticket {created_issue_id}.",
        },
        tmp_path,
    )
    assert res_sentry_ok.success is True
    assert res_sentry_ok.status_code == 200

    # Step 7: Objective verifier inspects workspace enterprise state
    v_res = AgentVerifier.verify_enterprise_state(
        tmp_path,
        require_linear_update=True,
        require_slack_escalation=True,
        require_github_merge=True,
        require_sentry_resolution=True,
    )
    assert v_res.passed is True
    assert len(v_res.checks) == 4
    for check in v_res.checks:
        assert check.passed is True
