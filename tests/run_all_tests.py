"""Test suite orchestrator — runs data-quality and integration test tiers."""

from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

DATA_QUALITY_SCRIPT = TESTS_DIR / "test_data_quality.py"
PIPELINE_INTEGRATION_SCRIPT = TESTS_DIR / "test_pipeline_integration.py"


def _load_test_module(script_path: Path, module_name: str):
    """
    Load a test module by file path using the same importlib pattern as pipeline scripts.

    Test filenames are valid Python identifiers, but importlib keeps loading consistent
    with src/bronze/ingest_all.py and src/silver/create_silver_tables.py.
    """
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_all_tests(spark) -> None:
    """
    Run all test tiers and report a combined pass/fail summary.

    Data quality runs first (reads existing Silver only); integration re-runs the
    full pipeline. Both tests execute even if one fails, then a final AssertionError
    is raised when any tier failed so this script can gate CI/notebook runs.
    """
    data_quality_mod = _load_test_module(DATA_QUALITY_SCRIPT, "test_data_quality_mod")
    integration_mod = _load_test_module(
        PIPELINE_INTEGRATION_SCRIPT,
        "test_pipeline_integration_mod",
    )

    test_plan = [
        ("test_silver_quality_checks", data_quality_mod.test_silver_quality_checks),
        ("test_pipeline_end_to_end", integration_mod.test_pipeline_end_to_end),
    ]

    results: list[tuple[str, str, str]] = []

    for test_name, test_fn in test_plan:
        try:
            test_fn(spark)
            results.append((test_name, "PASS", ""))
        except Exception as exc:
            notes = f"{type(exc).__name__}: {exc}"
            results.append((test_name, "FAIL", notes))
            traceback.print_exc()

    print("\n=== Test Suite Summary ===")
    header = f"{'Test Name':<30} | {'Status':<6} | Notes"
    print(header)
    print("-" * len(header))
    for test_name, status, notes in results:
        print(f"{test_name:<30} | {status:<6} | {notes}")

    failed_tests = [name for name, status, _ in results if status == "FAIL"]
    if failed_tests:
        raise AssertionError(
            "Test suite failed: " + ", ".join(failed_tests)
        )


if __name__ == "__main__":
    run_all_tests(spark)
