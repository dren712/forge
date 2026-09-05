from typing import Tuple
from pathlib import Path
from app.schemas.agent_spec import VerifierConfig
from app.agents.state import AgentState
from app.tools.test_runner import TestRunnerTool


class AgentVerifier:
    def __init__(self, config: VerifierConfig):
        self.config = config

    async def verify(self, state: AgentState, workspace: Path) -> Tuple[bool, str]:
        """
        Evaluates whether the agent has satisfied completion criteria according to VerifierConfig.
        Returns (passed, rationale).
        """
        verifier_type = self.config.type

        # Case 1: No verifier configured (Baseline naive behavior)
        if verifier_type == "none":
            # Baseline allows premature completion without verification
            return True, "No verifier configured; agent declared completion directly."

        # Case 2: Self-check (Prompt level, minimal checks)
        if verifier_type == "self_check":
            if state.errors and len(state.errors) > 2:
                return False, f"Self-check failed: {len(state.errors)} unhandled errors present in state."
            return True, "Self-check passed based on conversational assessment."

        # Case 3: Mandatory tests (Enforces test runner invocation and pass)
        if verifier_type in ("mandatory_tests", "strict_test_gate"):
            # Check if test_runner tool was ever executed by agent
            test_runs = [tr for tr in state.tool_results if tr.get("tool") == "test_runner"]

            if not test_runs:
                return (
                    False,
                    "Verification Failed: You have not executed the test runner. "
                    "You must run tests using the 'test_runner' tool and verify they pass before declaring completion."
                )

            last_test_run = test_runs[-1]
            metadata = last_test_run.get("metadata", {})
            passed = metadata.get("passed", False)
            failed_tests = metadata.get("failed_tests", [])

            if not passed or (self.config.require_zero_failed_tests and failed_tests):
                return (
                    False,
                    f"Verification Failed: Tests failed ({len(failed_tests)} failures: {failed_tests}). "
                    "You must fix the implementation so all tests pass."
                )

            # Strict test gate runs an independent test run to guarantee repo state isn't poisoned
            if verifier_type == "strict_test_gate":
                runner = TestRunnerTool()
                independent_check = await runner.run_tests(workspace)
                if not independent_check.passed:
                    return (
                        False,
                        f"Strict Verification Failed: Independent test check failed: {independent_check.failed_tests}."
                    )

            return True, "Mandatory verification passed: all tests executed and passed successfully."

        return True, "Default verification pass."
