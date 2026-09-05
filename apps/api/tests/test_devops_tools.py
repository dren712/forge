import pytest
from pathlib import Path
from app.tools.devops_tools import GitHubTool, SentryObservabilityTool


@pytest.mark.asyncio
async def test_github_tool_branch_protection_and_pr_policies(tmp_path: Path):
    tool = GitHubTool()

    # 1. List branches
    res_b = await tool.execute({"action": "list_branches"}, tmp_path)
    assert res_b.success is True
    assert "main" in res_b.output

    # 2. Branch naming policy violation
    res_bad_branch = await tool.execute(
        {"action": "create_pull_request", "title": "[LIN-101] Fix DB pool", "head_branch": "my-patch"},
        tmp_path,
    )
    assert res_bad_branch.success is False
    assert "HTTP 403 Forbidden" in res_bad_branch.output

    # 3. PR title tag policy violation
    res_bad_title = await tool.execute(
        {"action": "create_pull_request", "title": "Fix DB pool without brackets", "head_branch": "fix/db-pool"},
        tmp_path,
    )
    assert res_bad_title.success is False
    assert "HTTP 422 Unprocessable Entity" in res_bad_title.output

    # 4. Valid PR creation
    res_ok = await tool.execute(
        {"action": "create_pull_request", "title": "[LIN-101] Fix DB pool", "head_branch": "fix/db-pool"},
        tmp_path,
    )
    assert res_ok.success is True
    assert "status" in res_ok.output

    # 5. Merge pre-existing PR #42 with approvals
    res_merge = await tool.execute({"action": "merge_pull_request", "pr_number": 42}, tmp_path)
    assert res_merge.success is True
    assert "merged" in res_merge.output


@pytest.mark.asyncio
async def test_sentry_tool_traces_and_resolutions(tmp_path: Path):
    tool = SentryObservabilityTool()

    # 1. Query alert thresholds
    res_t = await tool.execute({"action": "query_alert_thresholds"}, tmp_path)
    assert res_t.success is True
    assert "P1" in res_t.output

    # 2. Fetch error trace for billing-api
    res_trace = await tool.execute({"action": "fetch_error_trace", "service_slug": "billing-api"}, tmp_path)
    assert res_trace.success is True
    assert "PoolAcquireTimeoutError" in res_trace.output

    # 3. Resolve incident with short note fails
    res_res_fail = await tool.execute(
        {"action": "resolve_incident", "issue_id": "SENTRY-891", "resolution_note": "fixed"},
        tmp_path,
    )
    assert res_res_fail.success is False
    assert "HTTP 422 Unprocessable Entity" in res_res_fail.output

    # 4. Resolve incident with valid note succeeds
    res_res_ok = await tool.execute(
        {
            "action": "resolve_incident",
            "issue_id": "SENTRY-891",
            "resolution_note": "Scaled max pool size to 100 connections and added exponential retry backoff.",
        },
        tmp_path,
    )
    assert res_res_ok.success is True
    assert "resolved" in res_res_ok.output
