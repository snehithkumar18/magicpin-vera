"""
Master Test Runner for Vera Message Engine
Executes all test suites, edge case probes, case study benchmarks, and concurrency audits in one command.
Usage: python test_all.py
"""

from __future__ import annotations
import sys
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_command_suite(name: str, cmd: list[str]) -> tuple[bool, str]:
    print("\n" + "=" * 80)
    print(f"  RUNNING SUITE: {name}")
    print("=" * 80)
    t0 = time.time()
    try:
        res = subprocess.run(
            [sys.executable] + cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        dur = time.time() - t0
        output = res.stdout + res.stderr
        print(output.strip())
        success = res.returncode == 0
        status_str = f"PASSED ({dur:.2f}s)" if success else f"FAILED (code {res.returncode})"
        return success, status_str
    except Exception as e:
        return False, f"ERROR: {e}"


def main():
    print("=" * 80)
    print("   VERA MESSAGE ENGINE — MASTER TEST & VERIFICATION HARNESS")
    print("   Author: Snehith Barkam (snehithbarkam@gmil.com)")
    print("=" * 80)

    suites = [
        ("Core Test Suite (12 PyTest Suites)", ["-m", "pytest"]),
        ("Official 30 Canonical Test Pairs", ["test_canonical_pairs.py"]),
        ("Official 10 Scoring Case Studies", ["benchmark_case_studies.py"]),
        ("Replay Scenarios & Adversarial Guardrails", ["test_replay_and_robustness.py"]),
        ("Conversational Domain & Inquiry Audit", ["audit_all_scenarios.py"]),
        ("Live Cloud Edge-Resilience Audit", ["test_edge_scenarios.py"]),
        ("High-Concurrency Scale Benchmark (15k+ RPS)", ["benchmark_concurrency.py"]),
    ]

    results = []
    total_start = time.time()

    for name, cmd in suites:
        passed, status_str = run_command_suite(name, cmd)
        results.append((name, passed, status_str))

    total_duration = time.time() - total_start

    print("\n" + "=" * 80)
    print("                         MASTER AUDIT SUMMARY TABLE")
    print("=" * 80)
    all_passed = True
    for name, passed, status_str in results:
        status_icon = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  {status_icon} {name:<45} : {status_str}")

    print("-" * 80)
    print(f"  Total Suites Executed : {len(results)}")
    print(f"  Total Elapsed Time    : {total_duration:.2f} seconds")
    if all_passed:
        print("  FINAL CERTIFICATION   : 100% PASS — ZERO FAILURES (READY FOR SUBMISSION)")
    else:
        print("  FINAL CERTIFICATION   : FAILURES DETECTED")
    print("=" * 80)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
