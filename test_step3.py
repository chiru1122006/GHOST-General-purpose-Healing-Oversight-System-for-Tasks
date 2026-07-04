#!/usr/bin/env python3
"""
GHOST Step 3 — Recovery Engine & Interceptor Verification Script.

Run with:
    python test_step3.py

Tests:
  1. Recovery engine — all 5 failure types produce valid injections
  2. Handler initialization — session setup and state
  3. Simulated tool calls — end-to-end flow without a real LLM

Exit code 0 = all checks passed, 1 = something failed.
"""

from __future__ import annotations

import os
import sys
import time
import traceback

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Counters
# ─────────────────────────────────────────────

_passed = 0
_failed = 0


def check(condition: bool, label: str) -> bool:
    """Assert a condition and print pass/fail."""
    global _passed, _failed
    if condition:
        print(f"  \u2713 {label}")
        _passed += 1
        return True
    else:
        print(f"  \u2717 {label}")
        _failed += 1
        return False


def section(number: int, total: int, title: str) -> None:
    """Print a section header."""
    print(f"\n[{number}/{total}] {title}")


# ─────────────────────────────────────────────
# Test 1: Recovery Engine
# ─────────────────────────────────────────────

def test_recovery_engine() -> None:
    """Test that all 5 failure types produce valid recovery strategies."""
    section(1, 3, "Testing recovery engine...")

    from core.recovery import RecoveryEngine

    engine = RecoveryEngine()

    failure_types = [
        "step_repetition_loop",
        "goal_drift",
        "tool_hallucination",
        "in_context_locking",
        "resource_exhaustion",
    ]

    for failure_type in failure_types:
        recovery = engine.get_recovery(
            failure_type,
            objective="Fix the bug in the login page",
            available_tools=["search_web", "read_file", "write_code"],
        )

        has_injection = recovery["injection"] is not None
        check(has_injection, f"{failure_type} has injection text")

        if has_injection:
            no_unfilled = "{objective}" not in recovery["injection"]
            check(
                no_unfilled,
                f"{failure_type} has no unfilled {{objective}} placeholder",
            )

        print(f"    → strategy: {recovery['strategy']} (priority {recovery['priority']})")

    # Test no_failure case
    no_fail = engine.get_recovery("no_failure")
    check(
        no_fail["injection"] is None,
        "no_failure returns None injection",
    )

    # Test unknown failure type falls back to no_failure
    unknown = engine.get_recovery("some_unknown_type")
    check(
        unknown["strategy"] == "continue",
        "Unknown failure type falls back to 'continue'",
    )


# ─────────────────────────────────────────────
# Test 2: Handler Initialization
# ─────────────────────────────────────────────

def test_handler_init() -> None:
    """Test that the callback handler initializes correctly."""
    section(2, 3, "Testing handler initialization...")

    from core.interceptor import GHOSTCallbackHandler

    handler = GHOSTCallbackHandler(
        task_type="test",
        objective="Do a test thing",
        verbose=False,  # Suppress output during testing
    )

    check(
        handler.session_id.startswith("ghost_"),
        f"Session ID format correct: {handler.session_id}",
    )
    check(
        handler.tool_call_sequence == [],
        "Tool call sequence starts empty",
    )
    check(
        handler.task_type == "test",
        "Task type stored correctly",
    )
    check(
        handler.objective == "Do a test thing",
        "Objective stored correctly",
    )
    check(
        handler.recovery_count == 0,
        "Recovery count starts at zero",
    )
    check(
        isinstance(handler.drift_threshold, float),
        f"Drift threshold is float: {handler.drift_threshold}",
    )


# ─────────────────────────────────────────────
# Test 3: Simulated Tool Calls
# ─────────────────────────────────────────────

def test_simulated_tool_calls() -> None:
    """Test end-to-end flow with simulated tool calls (no real LLM)."""
    section(3, 3, "Testing simulated tool calls...")

    from core.interceptor import GHOSTCallbackHandler

    handler = GHOSTCallbackHandler(
        task_type="web_research",
        objective="Research AI breakthroughs",
        verbose=True,
    )

    # Simulate 3 tool calls (same tool to trigger repetition detection)
    for i in range(3):
        handler.on_tool_start({"name": "search_web"}, f"query {i+1}")
        handler.on_tool_end(f"results for query {i+1}")
        time.sleep(0.05)  # Small delay for unique timestamps

    summary = handler.get_summary()

    check(
        summary["total_steps"] == 3,
        f"Handler tracked {summary['total_steps']} steps (expected 3)",
    )

    print(f"  INFO: Adherence history: {summary['adherence_history']}")
    print(f"  INFO: Recovery count: {summary['recovery_count']}")
    print(f"  INFO: Failure types seen: {summary['failure_types_seen']}")
    print(f"  INFO: Duration: {summary['duration_seconds']:.2f}s")

    # Verify that the handler detected the repetition
    if summary["adherence_history"]:
        last_score = summary["adherence_history"][-1]
        check(
            last_score < 0.5,
            f"Low adherence detected for repetitive calls ({last_score:.2f})",
        )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    """Run all Step 3 verification checks."""
    print("=" * 60)
    print("  GHOST Step 3 \u2014 Recovery Engine & Interceptor Verification")
    print("=" * 60)

    try:
        test_recovery_engine()
        test_handler_init()
        test_simulated_tool_calls()
    except Exception as e:
        print(f"\n  \u2717 UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    if _failed == 0:
        print(f"  \u2705 Step 3 complete. Recovery engine and interceptor working.")
        print(f"  \U0001f4d6 Read STEP3_README.md to understand what was built.")
        print(f"  \u27a1\ufe0f  Next: paste the Step 4 prompt.")
        print(f"  \U0001f4a1 Optional now: python examples/demo_simple.py (needs NVIDIA_API_KEY)")
    else:
        print(f"  \u274c {_failed} CHECK(S) FAILED out of {_passed + _failed}.")
    print("=" * 60)

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
