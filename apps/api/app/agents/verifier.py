import json
from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field
from app.schemas.agent_spec import VerifierConfig
from app.tools.test_runner import TestRunnerTool


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    evidence: str


class VerificationResult(BaseModel):
    passed: bool
    checks: list[VerificationCheck] = Field(default_factory=list)
    failure_reason: str | None = None

    def __iter__(self):
        feedback = self.failure_reason if not self.passed else (
            self.checks[0].evidence if self.checks else "Verification passed."
        )
        return iter((self.passed, feedback or "Verification passed."))

    def __getitem__(self, item: int):
        feedback = self.failure_reason if not self.passed else (
            self.checks[0].evidence if self.checks else "Verification passed."
        )
        return (self.passed, feedback or "Verification passed.")[item]


class AgentVerifier:
    def __init__(self, config: VerifierConfig):
        self.config = config

    async def verify(self, state: Any, workspace: Path) -> VerificationResult:
        """
        Evaluates whether the agent has satisfied completion criteria according to VerifierConfig.
        Returns a structured VerificationResult with individual VerificationChecks.
        """
        verifier_type = self.config.type

        # Case 1: No verifier configured (Baseline naive behavior)
        if verifier_type == "none":
            check = VerificationCheck(
                name="declaration_gate",
                passed=True,
                evidence="No verifier configured; agent declared completion directly.",
            )
            return VerificationResult(passed=True, checks=[check])

        # Case 2: Self-check (Prompt level, minimal checks)
        if verifier_type == "self_check":
            errors = getattr(state, "errors", [])
            if errors and len(errors) > 2:
                msg = f"Self-check failed: {len(errors)} unhandled errors present in state."
                check = VerificationCheck(name="error_threshold_check", passed=False, evidence=msg)
                return VerificationResult(passed=False, checks=[check], failure_reason=msg)
            check = VerificationCheck(
                name="error_threshold_check",
                passed=True,
                evidence="Self-check passed based on conversational assessment.",
            )
            return VerificationResult(passed=True, checks=[check])

        # Case 3: Mandatory tests (Enforces test runner invocation and pass)
        if verifier_type in ("mandatory_tests", "strict_test_gate"):
            checks: list[VerificationCheck] = []
            tool_results = getattr(state, "tool_results", [])
            test_runs = [tr for tr in tool_results if tr.get("tool") == "test_runner"]

            if not test_runs:
                msg = (
                    "Verification Failed: You have not executed the test runner. "
                    "You must run tests using the 'test_runner' tool and verify they pass before declaring completion."
                )
                checks.append(VerificationCheck(name="test_runner_executed", passed=False, evidence=msg))
                return VerificationResult(passed=False, checks=checks, failure_reason=msg)

            checks.append(
                VerificationCheck(
                    name="test_runner_executed",
                    passed=True,
                    evidence=f"Test runner was executed {len(test_runs)} time(s).",
                )
            )

            last_test_run = test_runs[-1]
            metadata = last_test_run.get("metadata", {})
            passed = metadata.get("passed", False)
            failed_tests = metadata.get("failed_tests", [])

            if not passed or (self.config.require_zero_failed_tests and failed_tests):
                msg = (
                    f"Verification Failed: Tests failed ({len(failed_tests)} failures: {failed_tests}). "
                    "You must fix the implementation so all tests pass."
                )
                checks.append(VerificationCheck(name="test_suite_passed", passed=False, evidence=msg))
                return VerificationResult(passed=False, checks=checks, failure_reason=msg)

            checks.append(
                VerificationCheck(
                    name="test_suite_passed",
                    passed=True,
                    evidence="All executed tests passed successfully.",
                )
            )

            # Strict test gate runs an independent test run to guarantee repo state isn't poisoned
            if verifier_type == "strict_test_gate":
                runner = TestRunnerTool()
                independent_check = await runner.run_tests(workspace)
                if not independent_check.passed:
                    msg = f"Strict Verification Failed: Independent test check failed: {independent_check.failed_tests}."
                    checks.append(VerificationCheck(name="independent_test_gate", passed=False, evidence=msg))
                    return VerificationResult(passed=False, checks=checks, failure_reason=msg)
                checks.append(
                    VerificationCheck(
                        name="independent_test_gate",
                        passed=True,
                        evidence="Independent test run passed with 0 failures.",
                    )
                )

            return VerificationResult(passed=True, checks=checks)

        return VerificationResult(
            passed=True,
            checks=[VerificationCheck(name="default_verification", passed=True, evidence="Default verification pass.")],
        )

    @classmethod
    def verify_enterprise_state(
        cls,
        workspace: Path,
        require_linear_update: bool = False,
        require_slack_escalation: bool = False,
        require_github_merge: bool = False,
        require_sentry_resolution: bool = False,
    ) -> VerificationResult:
        """
        Inspects underlying enterprise tool storage in the workspace to verify real state mutations.
        """
        checks: list[VerificationCheck] = []
        overall_passed = True
        failure_reasons = []

        # 1. Linear state check
        if require_linear_update:
            p = workspace / ".linear_state.json"
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                    issues = data.get("issues", [])
                    has_update = any(i.get("status") in ("In Progress", "Done") or i.get("priority") == 1 for i in issues)
                    if has_update:
                        checks.append(VerificationCheck(name="Linear issue updated", passed=True, evidence="Linear issue updated to active/escalated state."))
                    else:
                        overall_passed = False
                        checks.append(VerificationCheck(name="Linear issue updated", passed=False, evidence="Linear issue exists but was not updated or escalated."))
                        failure_reasons.append("Linear issue was not updated")
                except Exception as e:
                    overall_passed = False
                    checks.append(VerificationCheck(name="Linear issue updated", passed=False, evidence=f"Error reading Linear state: {e}"))
                    failure_reasons.append("Linear state unreadable")
            else:
                overall_passed = False
                checks.append(VerificationCheck(name="Linear issue updated", passed=False, evidence="No Linear state found in workspace."))
                failure_reasons.append("Missing Linear state")

        # 2. Slack escalation check
        if require_slack_escalation:
            p = workspace / ".slack_messages.json"
            if p.exists():
                try:
                    msgs = json.loads(p.read_text())
                    has_sla_msg = any(
                        m.get("channel") == "#enterprise-escalations" and "[SLA-ALERT]" in m.get("text", "")
                        for m in msgs
                    )
                    if has_sla_msg:
                        checks.append(VerificationCheck(name="Slack escalation sent", passed=True, evidence="Message with [SLA-ALERT] delivered to #enterprise-escalations."))
                    else:
                        overall_passed = False
                        checks.append(VerificationCheck(name="Slack escalation sent", passed=False, evidence="No [SLA-ALERT] message found in #enterprise-escalations."))
                        failure_reasons.append("Slack escalation missing [SLA-ALERT]")
                except Exception as e:
                    overall_passed = False
                    checks.append(VerificationCheck(name="Slack escalation sent", passed=False, evidence=f"Error reading Slack state: {e}"))
                    failure_reasons.append("Slack state unreadable")
            else:
                overall_passed = False
                checks.append(VerificationCheck(name="Slack escalation sent", passed=False, evidence="No Slack state found in workspace."))
                failure_reasons.append("Missing Slack state")

        # 3. GitHub PR merge check
        if require_github_merge:
            p = workspace / ".github_state.json"
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                    prs = data.get("pull_requests", [])
                    has_merged = any(pr.get("state") == "merged" for pr in prs)
                    if has_merged:
                        checks.append(VerificationCheck(name="GitHub PR merged", passed=True, evidence="Hotfix pull request successfully merged."))
                    else:
                        overall_passed = False
                        checks.append(VerificationCheck(name="GitHub PR merged", passed=False, evidence="No pull request with state='merged' found."))
                        failure_reasons.append("GitHub PR was not merged")
                except Exception as e:
                    overall_passed = False
                    checks.append(VerificationCheck(name="GitHub PR merged", passed=False, evidence=f"Error reading GitHub state: {e}"))
                    failure_reasons.append("GitHub state unreadable")
            else:
                overall_passed = False
                checks.append(VerificationCheck(name="GitHub PR merged", passed=False, evidence="No GitHub state found in workspace."))
                failure_reasons.append("Missing GitHub state")

        # 4. Sentry resolution check
        if require_sentry_resolution:
            p = workspace / ".sentry_state.json"
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                    incidents = data.get("incidents", [])
                    has_resolved = any(
                        inc.get("status") == "resolved" and len(inc.get("resolution_note", "")) >= 15
                        for inc in incidents
                    )
                    if has_resolved:
                        checks.append(VerificationCheck(name="Sentry incident resolved", passed=True, evidence="Incident marked resolved with detailed resolution note."))
                    else:
                        overall_passed = False
                        checks.append(VerificationCheck(name="Sentry incident resolved", passed=False, evidence="Incident is unresolved or resolution note is under 15 characters."))
                        failure_reasons.append("Sentry incident unresolved or note too short")
                except Exception as e:
                    overall_passed = False
                    checks.append(VerificationCheck(name="Sentry incident resolved", passed=False, evidence=f"Error reading Sentry state: {e}"))
                    failure_reasons.append("Sentry state unreadable")
            else:
                overall_passed = False
                checks.append(VerificationCheck(name="Sentry incident resolved", passed=False, evidence="No Sentry state found in workspace."))
                failure_reasons.append("Missing Sentry state")

        return VerificationResult(
            passed=overall_passed,
            checks=checks,
            failure_reason="; ".join(failure_reasons) if failure_reasons else None,
        )
