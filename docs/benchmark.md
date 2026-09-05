# Software Engineering Benchmark v1

## 1. Design Philosophy
The benchmark is controlled, deterministic, and self-contained. It operates on real local file structures and executes real `pytest` assertions. No GitHub API tokens or external network access are required.

## 2. Benchmark Tasks Overview

| Task ID | Title | Target Subsystem | Key Failure Mode Tested |
|---|---|---|---|
| `task_01_simple_bug` | Fix Pagination Boundary | `src/pagination.py` | Premature completion / off-by-one |
| `task_02_find_correct_file` | Locate Logging Formatter | `utils/formatter.py` | Context & tool search navigation |
| `task_03_multi_file_change` | Sync Schema & Serializer | `models/user.py`, `serializers/user.py` | Partial / incomplete refactor |
| `task_04_understand_existing_tests` | Implement Discount Edge Case | `discount.py` | Test comprehension & constraints |
| `task_05_fix_failing_test` | Fix ZeroDivision in Variance | `stats.py` | Numerical stability & edge cases |
| `task_06_ambiguous_requirement` | Robust Config Loading | `config_loader.py` | Missing key / default fallbacks |
| `task_07_avoid_unrelated_modifications` | Auth Token Validation | `auth/tokens.py` | Negative constraints (billing untouched) |
| `task_08_feature_implementation` | Custom LRU Cache | `cache.py` | Architectural feature addition |
| `task_09_recovery_from_error` | Custom JSON Serializer | `encoder.py` | Syntax error & exception recovery |
| `task_10_verify_before_success` | Strict Semver Parser | `semver.py` | Mandatory test verification |
