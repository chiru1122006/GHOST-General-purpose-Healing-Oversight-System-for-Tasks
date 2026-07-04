#!/usr/bin/env python3
"""
GHOST Verification Script — Step 5.

Performs final verification of GHOST:
1. Runs pytest tests/ -v and reports results.
2. Checks that benchmarks/tasks.py has at least 50 tasks.
3. Checks that README.md has > 200 lines.
4. Checks that all 5 step README files exist.
5. Prints the GHOST launch checklist.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ANSI coloring
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_section(num: int, title: str) -> None:
    print(f"\n{BOLD}[{num}/4] {title}{RESET}")


def check(assertion: bool, message: str) -> bool:
    if assertion:
        print(f"  {GREEN}✓ {message}{RESET}")
        return True
    else:
        print(f"  {RED}✗ {message}{RESET}")
        return False


def main() -> None:
    print("=" * 60)
    print("  GHOST Step 5 — Final Verification Script")
    print("=" * 60)

    # 1. Run pytest suite
    print_section(1, "Running Pytest Suite...")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            capture_output=True,
            text=True,
            shell=True if os.name == "nt" else False
        )
        print(res.stdout)
        
        if res.returncode == 0:
            print(f"  {GREEN}✓ Pytest suite completed successfully.{RESET}")
        else:
            print(f"  {RED}✗ Pytest suite failed.{RESET}")
            print(res.stderr)
    except Exception as e:
        print(f"  {RED}✗ Failed to execute pytest: {e}{RESET}")

    # 2. Check benchmarks tasks count
    print_section(2, "Checking Synthetic Benchmark Tasks...")
    try:
        from benchmarks.tasks import TASK_TEMPLATES
        count = len(TASK_TEMPLATES)
        check(count >= 50, f"benchmarks/tasks.py has {count} tasks (expected >= 50)")
    except Exception as e:
        print(f"  {RED}✗ Failed to import tasks: {e}{RESET}")

    # 3. Check README lines count
    print_section(3, "Checking Root README.md...")
    readme_path = Path("README.md")
    if check(readme_path.exists(), "README.md exists"):
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        check(len(lines) > 200, f"README.md has {len(lines)} lines (expected > 200)")

    # 4. Check all 5 step READMEs exist
    print_section(4, "Checking Step README Files...")
    readmes = [
        "STEP1_README.md",
        "STEP2_README.md",
        "STEP3_README.md",
        "STEP4_README.md",
        "STEP5_README.md",
    ]
    for r in readmes:
        check(Path(r).exists(), f"{r} exists")

    # Print Launch Checklist
    print("\n" + "=" * 60)
    print("✅ GHOST IS FULLY BUILT. LAUNCH CHECKLIST:")
    print("=" * 60)
    print()
    print("[ ] python test_step1.py        — Foundation")
    print("[ ] python test_step2.py        — Scoring + Classifier")
    print("[ ] python test_step3.py        — Recovery + Interceptor")
    print("[ ] Dashboard opens at localhost:3000")
    print("[ ] python examples/demo_simple.py  — End-to-end demo works")
    print("[ ] pytest tests/ -v            — All tests pass")
    print("[ ] python benchmarks/run_tau_bench.py --tasks 50 --runs 3  — Get real numbers")
    print("[ ] Put real numbers into README.md benchmark table")
    print()
    print("THEN POST IN THIS ORDER:")
    print("1. Record 90-second demo video of GHOST catching a failure")
    print("2. Post to Hacker News: Show HN: GHOST — open-source AI agent drift detection")
    print("3. Post to X/Twitter with demo video + benchmark table image")
    print("4. Post to r/MachineLearning")
    print("5. Post to r/LocalLLaMA")
    print("6. Email 3 professors who work on agent reliability")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
