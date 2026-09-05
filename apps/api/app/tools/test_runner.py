import time
import asyncio
import sys
import re
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from app.tools.base import Tool, ToolResult


class TestResult(BaseModel):
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    failed_tests: list[str] = Field(default_factory=list)


class TestRunnerTool(Tool):
    __test__ = False  # Prevent pytest from treating this tool class as a test suite
    name = "test_runner"
    description = (
        "Execute automated tests (pytest) inside the repository workspace. "
        "Returns pass/fail status, detailed failure traces, and names of failed test cases."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "test_path": {
                "type": "string",
                "description": "Specific test file or test folder (e.g. 'tests' or 'tests/test_calculator.py')",
                "default": "tests",
            },
            "extra_args": {
                "type": "string",
                "description": "Optional extra arguments to pass to pytest (e.g. '-k test_feature')",
                "default": "",
            },
        },
    }

    async def run_tests(self, workspace: Path, test_path: str = "tests", extra_args: str = "") -> TestResult:
        start_time = time.perf_counter()
        python_bin = sys.executable

        # Run pytest module
        cmd = [python_bin, "-m", "pytest", test_path, "-v"]
        if extra_args:
            cmd.extend(extra_args.strip().split())

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(process.communicate(), timeout=45.0)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return TestResult(
                    passed=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Test execution timed out after 45.0s",
                    duration_ms=duration_ms,
                    failed_tests=["TIMEOUT"],
                )

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            stdout_str = stdout_data.decode("utf-8", errors="replace")
            stderr_str = stderr_data.decode("utf-8", errors="replace")
            exit_code = process.returncode

            # Extract failed tests from pytest summary
            failed_tests: list[str] = []
            for line in stdout_str.splitlines():
                if line.startswith("FAILED ") or " FAILED " in line:
                    parts = line.split()
                    for p in parts:
                        if "::" in p:
                            failed_tests.append(p)
                            break
                    else:
                        failed_tests.append(line.strip())

            passed = (exit_code == 0)
            return TestResult(
                passed=passed,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                failed_tests=failed_tests,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return TestResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=f"Test runner invocation error: {str(e)}",
                duration_ms=duration_ms,
                failed_tests=["RUNNER_ERROR"],
            )

    async def execute(self, input_data: dict[str, Any], workspace: Path) -> ToolResult:
        test_path = input_data.get("test_path", "tests")
        extra_args = input_data.get("extra_args", "")

        test_result = await self.run_tests(workspace, test_path, extra_args)

        summary = (
            f"Test Suite: {'PASSED' if test_result.passed else 'FAILED'} (exit code {test_result.exit_code})\n"
            f"Duration: {test_result.duration_ms:.1f} ms\n"
        )
        if test_result.failed_tests:
            summary += f"Failed tests ({len(test_result.failed_tests)}):\n"
            for ft in test_result.failed_tests:
                summary += f"  - {ft}\n"
        summary += f"\n--- STDOUT ---\n{test_result.stdout[-3000:]}"
        if test_result.stderr:
            summary += f"\n--- STDERR ---\n{test_result.stderr[-1500:]}"

        return ToolResult(
            success=test_result.passed,
            output=summary,
            error=None if test_result.passed else f"{len(test_result.failed_tests)} tests failed",
            latency_ms=test_result.duration_ms,
            metadata=test_result.model_dump(),
        )
