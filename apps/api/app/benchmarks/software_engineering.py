import os
import shutil
from pathlib import Path
from typing import List
from app.benchmarks.base import Benchmark, BenchmarkTask, TaskEvaluation
from app.agents.state import AgentState
from app.tools.test_runner import TestRunnerTool


TASKS_DATA = [
    {
        "id": "task_01_simple_bug",
        "title": "Fix Pagination Off-By-One Boundary",
        "description": "The paginate function raises IndexError when page * page_size equals the list length.",
        "repository": "pagination_utils",
        "issue": "Fix off-by-one boundary error in paginate() in src/pagination.py so it returns the last page instead of raising IndexError.",
        "expected_behavior": "paginate([1,2,3,4], page=2, page_size=2) should return [3, 4] and not raise IndexError.",
        "constraints": ["Do not change page_size calculation logic", "All tests in tests/ must pass"],
    },
    {
        "id": "task_02_find_correct_file",
        "title": "Locate Formatter and Add ISO Timestamp",
        "description": "Find the logging formatter among multiple utils modules and add ISO 8601 timestamp support.",
        "repository": "logger_pkg",
        "issue": "Add 'iso_timestamp' field formatted as YYYY-MM-DD to LogRecord in the appropriate formatter module.",
        "expected_behavior": "LogRecord formatter returns json payload with valid 'iso_timestamp'.",
        "constraints": ["Do not modify config.py or transports.py"],
    },
    {
        "id": "task_03_multi_file_change",
        "title": "Sync User Schema and Serializer",
        "description": "Add 'phone_number' to UserModel and update UserSerializer to serialize it.",
        "repository": "user_service",
        "issue": "Add optional phone_number field to UserModel in models/user.py and ensure serializers/user.py includes it in output dictionary.",
        "expected_behavior": "UserSerializer.to_dict(user) contains 'phone_number'.",
        "constraints": ["Both models/user.py and serializers/user.py must be updated"],
    },
    {
        "id": "task_04_understand_existing_tests",
        "title": "Implement Discount Edge Case",
        "description": "Discount calculator fails on order values above $1000 with tier 3 coupons.",
        "repository": "discount_engine",
        "issue": "Read tests/test_discount.py to understand expected Tier 3 coupon behavior (25% off capped at $300) and implement it in discount.py.",
        "expected_behavior": "Orders above $1000 with TIER3 discount capped at $300 discount.",
        "constraints": ["Do not modify tests/test_discount.py"],
    },
    {
        "id": "task_05_fix_failing_test",
        "title": "Fix ZeroDivisionError in Statistics Module",
        "description": "calculate_mean and calculate_variance crash when an empty list or single element is provided.",
        "repository": "stats_lib",
        "issue": "calculate_variance() in stats.py raises ZeroDivisionError on empty or 1-element arrays. Return 0.0 instead.",
        "expected_behavior": "calculate_variance([]) == 0.0 and calculate_variance([42]) == 0.0.",
        "constraints": ["Maintain float return type"],
    },
    {
        "id": "task_06_ambiguous_requirement",
        "title": "Robust Config Loader with Sane Defaults",
        "description": "Config parser crashes when optional database.timeout setting is missing.",
        "repository": "config_loader",
        "issue": "Load database timeout with default 30.0s when key is absent in config.json.",
        "expected_behavior": "load_config() does not KeyError and defaults timeout to 30.0.",
        "constraints": ["Keep existing json loading logic intact"],
    },
    {
        "id": "task_07_avoid_unrelated_modifications",
        "title": "Fix Auth Token Validation Without Touching Billing",
        "description": "Validate auth bearer token without inadvertently modifying billing/charge.py.",
        "repository": "monolith_api",
        "issue": "Fix token validation in auth/tokens.py. IMPORTANT: Do not touch billing/charge.py.",
        "expected_behavior": "auth/tokens.py validates Bearer token, billing/charge.py unchanged.",
        "constraints": ["billing/charge.py must remain untouched"],
    },
    {
        "id": "task_08_feature_implementation",
        "title": "Implement LRU Cache Decorator",
        "description": "Implement a simple in-memory LRU cache decorator in cache.py.",
        "repository": "cache_system",
        "issue": "Implement @lru_cache_custom(max_size=3) decorator in cache.py that evicts the least recently used key.",
        "expected_behavior": "Calling cached function with 4th distinct argument evicts the oldest item.",
        "constraints": ["Do not use functools.lru_cache; implement custom dictionary-based logic"],
    },
    {
        "id": "task_09_recovery_from_error",
        "title": "Fix Broken JSON Serializer and Recover from Syntax Errors",
        "description": "Fix datetime serialization in CustomJsonEncoder and ensure recovery from runtime exceptions.",
        "repository": "json_encoder",
        "issue": "Support datetime.date and datetime.datetime serialization in CustomJsonEncoder (encoder.py).",
        "expected_behavior": "CustomJsonEncoder().encode({'now': datetime.now()}) outputs ISO string.",
        "constraints": ["All tests pass"],
    },
    {
        "id": "task_10_verify_before_success",
        "title": "Strict Semver Parser Verification",
        "description": "Parse semantic version strings into (major, minor, patch, prerelease).",
        "repository": "semver_tool",
        "issue": "Implement parse_semver(v_str) in semver.py handling '1.2.3-beta.1' correctly. Run tests to verify all 5 test cases pass.",
        "expected_behavior": "parse_semver('2.1.0-rc.1') returns SemVer(2, 1, 0, 'rc.1').",
        "constraints": ["Must execute test_runner before completing"],
    },
]


class SoftwareEngineeringBenchmark(Benchmark):
    name = "software_engineering"
    version = "v1"

    def list_tasks(self) -> List[BenchmarkTask]:
        return [BenchmarkTask(**t) for t in TASKS_DATA]

    async def setup_task(self, task: BenchmarkTask, workspace: Path) -> None:
        """Seeds the workspace with task repository files and pytest tests."""
        # Clean workspace
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        task_id = task.id

        if task_id == "task_01_simple_bug":
            src_dir = workspace / "src"
            tests_dir = workspace / "tests"
            src_dir.mkdir(parents=True, exist_ok=True)
            tests_dir.mkdir(parents=True, exist_ok=True)

            (src_dir / "pagination.py").write_text(
                "def paginate(items, page=1, page_size=10):\n"
                "    start = (page - 1) * page_size\n"
                "    end = start + page_size\n"
                "    if start >= len(items):\n"
                "        raise IndexError('Page out of range')\n"
                "    return items[start:end]\n"
            )
            (tests_dir / "test_pagination.py").write_text(
                "from src.pagination import paginate\n\n"
                "def test_paginate_normal():\n"
                "    items = [1, 2, 3, 4, 5]\n"
                "    assert paginate(items, 1, 2) == [1, 2]\n\n"
                "def test_paginate_boundary():\n"
                "    items = [1, 2, 3, 4]\n"
                "    # Exactly 2 pages of size 2\n"
                "    assert paginate(items, 2, 2) == [3, 4]\n\n"
                "def test_paginate_empty():\n"
                "    assert paginate([], 1, 2) == []\n"
            )

        elif task_id == "task_02_find_correct_file":
            utils_dir = workspace / "utils"
            tests_dir = workspace / "tests"
            utils_dir.mkdir(parents=True, exist_ok=True)
            tests_dir.mkdir(parents=True, exist_ok=True)

            (utils_dir / "config.py").write_text("DEBUG = True\n")
            (utils_dir / "transports.py").write_text("class HttpTransport: pass\n")
            (utils_dir / "formatter.py").write_text(
                "from datetime import datetime\n\n"
                "class LogFormatter:\n"
                "    def format_record(self, level: str, message: str) -> dict:\n"
                "        # TODO: Add iso_timestamp field formatted as YYYY-MM-DD\n"
                "        return {'level': level, 'message': message}\n"
            )
            (tests_dir / "test_formatter.py").write_text(
                "from utils.formatter import LogFormatter\n"
                "import re\n\n"
                "def test_formatter_iso_timestamp():\n"
                "    fmt = LogFormatter()\n"
                "    rec = fmt.format_record('INFO', 'Test msg')\n"
                "    assert 'iso_timestamp' in rec\n"
                "    assert re.match(r'^\\d{4}-\\d{2}-\\d{2}$', rec['iso_timestamp'])\n"
            )

        elif task_id == "task_03_multi_file_change":
            models_dir = workspace / "models"
            serializers_dir = workspace / "serializers"
            tests_dir = workspace / "tests"
            models_dir.mkdir(parents=True, exist_ok=True)
            serializers_dir.mkdir(parents=True, exist_ok=True)
            tests_dir.mkdir(parents=True, exist_ok=True)

            (models_dir / "user.py").write_text(
                "class UserModel:\n"
                "    def __init__(self, username: str, email: str, phone_number: str | None = None):\n"
                "        self.username = username\n"
                "        self.email = email\n"
                "        self.phone_number = phone_number\n"
            )
            (serializers_dir / "user.py").write_text(
                "class UserSerializer:\n"
                "    @staticmethod\n"
                "    def to_dict(user) -> dict:\n"
                "        # Bug: phone_number is missing from serialized output\n"
                "        data = {'username': user.username, 'email': user.email}\n"
                "        if hasattr(user, 'phone_number'):\n"
                "            data['phone_number'] = user.phone_number\n"
                "        return data\n"
            )
            (tests_dir / "test_user_sync.py").write_text(
                "from models.user import UserModel\n"
                "from serializers.user import UserSerializer\n\n"
                "def test_user_serialization():\n"
                "    u = UserModel('alice', 'alice@example.com', '555-1234')\n"
                "    d = UserSerializer.to_dict(u)\n"
                "    assert d['username'] == 'alice'\n"
                "    assert d['phone_number'] == '555-1234'\n"
            )

        elif task_id == "task_04_understand_existing_tests":
            (workspace / "discount.py").write_text(
                "def calculate_discount(amount: float, tier: str) -> float:\n"
                "    if tier == 'TIER1': return amount * 0.05\n"
                "    if tier == 'TIER2': return amount * 0.10\n"
                "    if tier == 'TIER3':\n"
                "        # Incorrect implementation: not capped at 300\n"
                "        disc = amount * 0.25\n"
                "        return min(disc, 300.0)\n"
                "    return 0.0\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_discount.py").write_text(
                "from discount import calculate_discount\n\n"
                "def test_tier1(): assert calculate_discount(100, 'TIER1') == 5.0\n"
                "def test_tier3_cap():\n"
                "    assert calculate_discount(2000, 'TIER3') == 300.0\n"
                "    assert calculate_discount(800, 'TIER3') == 200.0\n"
            )

        elif task_id == "task_05_fix_failing_test":
            (workspace / "stats.py").write_text(
                "def calculate_mean(nums: list[float]) -> float:\n"
                "    if not nums: return 0.0\n"
                "    return sum(nums) / len(nums)\n\n"
                "def calculate_variance(nums: list[float]) -> float:\n"
                "    if len(nums) <= 1: return 0.0\n"
                "    m = calculate_mean(nums)\n"
                "    return sum((x - m) ** 2 for x in nums) / (len(nums) - 1)\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_stats.py").write_text(
                "from stats import calculate_mean, calculate_variance\n\n"
                "def test_variance_empty():\n"
                "    assert calculate_variance([]) == 0.0\n\n"
                "def test_variance_single():\n"
                "    assert calculate_variance([10.0]) == 0.0\n\n"
                "def test_variance_normal():\n"
                "    assert calculate_variance([1.0, 2.0, 3.0]) == 1.0\n"
            )

        elif task_id == "task_06_ambiguous_requirement":
            (workspace / "config_loader.py").write_text(
                "import json\n\n"
                "def load_database_timeout(config_json_str: str) -> float:\n"
                "    data = json.loads(config_json_str)\n"
                "    db = data.get('database', {})\n"
                "    return float(db.get('timeout', 30.0))\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_config.py").write_text(
                "from config_loader import load_database_timeout\n\n"
                "def test_missing_timeout():\n"
                "    assert load_database_timeout('{\"database\": {}}') == 30.0\n\n"
                "def test_explicit_timeout():\n"
                "    assert load_database_timeout('{\"database\": {\"timeout\": 15.5}}') == 15.5\n"
            )

        elif task_id == "task_07_avoid_unrelated_modifications":
            auth_dir = workspace / "auth"
            billing_dir = workspace / "billing"
            tests_dir = workspace / "tests"
            auth_dir.mkdir(parents=True, exist_ok=True)
            billing_dir.mkdir(parents=True, exist_ok=True)
            tests_dir.mkdir(parents=True, exist_ok=True)

            (auth_dir / "tokens.py").write_text(
                "def validate_bearer_token(header: str) -> bool:\n"
                "    if not header.startswith('Bearer '):\n"
                "        return False\n"
                "    token = header.split(' ', 1)[1].strip()\n"
                "    return len(token) >= 16\n"
            )
            (billing_dir / "charge.py").write_text(
                "# CRITICAL FINANCIAL CODE - DO NOT MODIFY\n"
                "def process_charge(amount: float): return {'status': 'processed', 'amount': amount}\n"
            )
            (tests_dir / "test_auth.py").write_text(
                "from auth.tokens import validate_bearer_token\n\n"
                "def test_token_validation():\n"
                "    assert validate_bearer_token('Bearer token1234567890abcdef') is True\n"
                "    assert validate_bearer_token('Basic dXNlcjpwYXNz') is False\n"
            )

        elif task_id == "task_08_feature_implementation":
            (workspace / "cache.py").write_text(
                "def lru_cache_custom(max_size=3):\n"
                "    def decorator(fn):\n"
                "        cache = {}\n"
                "        def wrapper(*args):\n"
                "            if args in cache:\n"
                "                val = cache.pop(args)\n"
                "                cache[args] = val\n"
                "                return val\n"
                "            res = fn(*args)\n"
                "            if len(cache) >= max_size:\n"
                "                oldest = next(iter(cache))\n"
                "                del cache[oldest]\n"
                "            cache[args] = res\n"
                "            return res\n"
                "        return wrapper\n"
                "    return decorator\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_cache.py").write_text(
                "from cache import lru_cache_custom\n\n"
                "def test_lru_cache():\n"
                "    calls = []\n"
                "    @lru_cache_custom(max_size=2)\n"
                "    def double(x):\n"
                "        calls.append(x)\n"
                "        return x * 2\n\n"
                "    assert double(1) == 2\n"
                "    assert double(2) == 4\n"
                "    assert double(1) == 2\n"
                "    assert len(calls) == 2\n"
                "    assert double(3) == 6\n"
                "    assert len(calls) == 3\n"
            )

        elif task_id == "task_09_recovery_from_error":
            (workspace / "encoder.py").write_text(
                "import json\nfrom datetime import date, datetime\n\n"
                "class CustomJsonEncoder(json.JSONEncoder):\n"
                "    def default(self, obj):\n"
                "        if isinstance(obj, (date, datetime)):\n"
                "            return obj.isoformat()\n"
                "        return super().default(obj)\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_encoder.py").write_text(
                "import json\nfrom datetime import date, datetime\nfrom encoder import CustomJsonEncoder\n\n"
                "def test_date_encode():\n"
                "    d = {'today': date(2026, 9, 5)}\n"
                "    s = json.dumps(d, cls=CustomJsonEncoder)\n"
                "    assert '2026-09-05' in s\n"
            )

        elif task_id == "task_10_verify_before_success":
            (workspace / "semver.py").write_text(
                "from dataclasses import dataclass\nimport re\n\n"
                "@dataclass\n"
                "class SemVer:\n"
                "    major: int\n"
                "    minor: int\n"
                "    patch: int\n"
                "    prerelease: str | None = None\n\n"
                "def parse_semver(v: str) -> SemVer:\n"
                "    pattern = r'^(\\d+)\\.(\\d+)\\.(\\d+)(?:-(.+))?$'\n"
                "    m = re.match(pattern, v)\n"
                "    if not m:\n"
                "        raise ValueError(f'Invalid semver: {v}')\n"
                "    maj, min_, pat, pre = m.groups()\n"
                "    return SemVer(int(maj), int(min_), int(pat), pre)\n"
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_semver.py").write_text(
                "from semver import parse_semver, SemVer\n\n"
                "def test_simple_semver():\n"
                "    v = parse_semver('1.2.3')\n"
                "    assert v == SemVer(1, 2, 3, None)\n\n"
                "def test_prerelease():\n"
                "    v = parse_semver('2.0.0-rc.1')\n"
                "    assert v == SemVer(2, 0, 0, 'rc.1')\n"
            )

    async def evaluate_task(self, state: AgentState, task: BenchmarkTask, workspace: Path) -> TaskEvaluation:
        runner = TestRunnerTool()
        test_result = await runner.run_tests(workspace)

        # Constraint checks
        if task.id == "task_07_avoid_unrelated_modifications":
            billing_file = workspace / "billing" / "charge.py"
            if billing_file.exists():
                content = billing_file.read_text(encoding="utf-8")
                if "DO NOT MODIFY" not in content:
                    return TaskEvaluation(
                        task_id=task.id,
                        passed=False,
                        score=0.0,
                        reason="Constraint violation: billing/charge.py was modified or corrupted.",
                        failed_tests=["CONSTRAINT_VIOLATION"],
                    )

        score = 1.0 if test_result.passed else 0.0
        reason = "All unit tests passed successfully." if test_result.passed else f"Tests failed with exit code {test_result.exit_code}."

        return TaskEvaluation(
            task_id=task.id,
            passed=test_result.passed,
            score=score,
            reason=reason,
            test_stdout=test_result.stdout,
            test_stderr=test_result.stderr,
            failed_tests=test_result.failed_tests,
            verification_passed=state.verification_passed,
            details={"duration_ms": test_result.duration_ms},
        )
