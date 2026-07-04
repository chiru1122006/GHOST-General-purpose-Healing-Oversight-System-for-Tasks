#!/usr/bin/env python3
"""
GHOST Step 2 — Scoring & Classification Verification Script.

Run with:
    python test_step2.py

Tests:
  1. Trajectory adherence scoring (Jaccard + embedding)
  2. Heuristic failure classifier (no API needed)
  3. Live NIM API classifier (requires NVIDIA_API_KEY in .env)

Exit code 0 = all checks passed, 1 = something failed.
"""

from __future__ import annotations

import os
import sys
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
# Test 1: Trajectory Adherence Scoring
# ─────────────────────────────────────────────

def test_trajectory_scoring() -> None:
    """Test that adherence scoring correctly differentiates sequences."""
    section(1, 3, "Testing trajectory adherence scoring...")

    from core.trajectory import TrajectoryTracker

    tracker = TrajectoryTracker()

    # Score 1: Sequence similar to the seeded "web_research" trajectory
    score_similar = tracker.compute_adherence(
        "web_research",
        ["search_web", "read_page", "search_web", "read_page", "extract_info"],
    )
    print(f"  Score (similar to success): {score_similar:.2f}")

    # Score 2: Completely unrelated tools
    score_random = tracker.compute_adherence(
        "web_research",
        ["cook_food", "drive_car", "fly_plane"],
    )
    print(f"  Score (random tools):       {score_random:.2f}")

    # Score 3: Repetition loop (should trigger pathological detection)
    score_repetition = tracker.compute_adherence(
        "web_research",
        ["search_web", "search_web", "search_web", "search_web"],
    )
    print(f"  Score (repetition loop):    {score_repetition:.2f}")

    # Assertions
    check(
        score_similar > score_random,
        f"Similar sequence scores higher than random ({score_similar:.2f} > {score_random:.2f})",
    )
    check(
        score_repetition < 0.2,
        f"Repetition loop detected (score {score_repetition:.2f} < 0.2)",
    )


# ─────────────────────────────────────────────
# Test 2: Heuristic Classifier
# ─────────────────────────────────────────────

def test_heuristic_classifier() -> None:
    """Test the deterministic heuristic classifier (no API needed)."""
    section(2, 3, "Testing heuristic classifier...")

    from core.classifier import FailureClassifier

    classifier = FailureClassifier()

    # Test repetition loop detection
    fake_history = [
        {"tool": "search_web", "input": "AI news", "output": "results"},
        {"tool": "search_web", "input": "AI news", "output": "results"},
        {"tool": "search_web", "input": "AI news", "output": "results"},
    ]
    failure_type, confidence, reasoning = classifier._heuristic_classify(
        fake_history
    )
    print(f"  Failure type: {failure_type}")
    print(f"  Confidence:   {confidence}")
    print(f"  Reasoning:    {reasoning}")

    check(
        failure_type == "step_repetition_loop",
        "Correctly classified repetition loop",
    )

    # Test error-based detection (tool hallucination)
    error_history = [
        {"tool": "send_email", "input": "hello", "error": "Tool not found"},
        {"tool": "email_user", "input": "hello", "error": "Tool not found"},
        {"tool": "dispatch_email", "input": "hello", "error": "Tool not found"},
    ]
    ft2, conf2, reason2 = classifier._heuristic_classify(error_history)
    print(f"  Error test → {ft2} (confidence: {conf2})")
    check(
        ft2 == "tool_hallucination",
        "Correctly classified tool hallucination from errors",
    )

    # Test no-failure case
    normal_history = [
        {"tool": "search_web", "input": "query", "output": "results"},
        {"tool": "read_page", "input": "url", "output": "content"},
        {"tool": "write_file", "input": "report", "output": "saved"},
    ]
    ft3, conf3, reason3 = classifier._heuristic_classify(normal_history)
    print(f"  Normal test → {ft3} (confidence: {conf3})")
    check(
        ft3 == "no_failure",
        "Correctly identified no failure in normal sequence",
    )


# ─────────────────────────────────────────────
# Test 3: Live NIM API Classifier
# ─────────────────────────────────────────────

def test_live_classifier() -> None:
    """Test the live NIM API classifier (requires NVIDIA_API_KEY)."""
    section(3, 3, "Testing live NIM API classifier...")

    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key or api_key == "your_nvidia_nim_api_key_here":
        print("  \u23ed Skipping \u2014 no NVIDIA_API_KEY in .env")
        print("  (Set NVIDIA_API_KEY in .env to test live classification)")
        return

    from core.classifier import FailureClassifier

    classifier = FailureClassifier()

    fake_history = [
        {"tool": "search_web", "input": "AI news", "output": "results"},
        {"tool": "search_web", "input": "AI news", "output": "results"},
        {"tool": "search_web", "input": "AI news", "output": "results"},
    ]

    try:
        failure_type, confidence, reasoning = classifier.classify(
            tool_call_history=fake_history,
            objective="Find and summarize the latest AI research papers",
            step_count=3,
        )
        print(f"  NIM response:")
        print(f"    Failure type: {failure_type}")
        print(f"    Confidence:   {confidence}")
        print(f"    Reasoning:    {reasoning}")
        check(
            failure_type in {
                "step_repetition_loop", "goal_drift", "tool_hallucination",
                "in_context_locking", "resource_exhaustion", "no_failure",
            },
            f"Valid failure type returned: {failure_type}",
        )
    except Exception as e:
        print(f"  \u26a0 NIM API call failed: {e}")
        print("  This is expected if NVIDIA_API_KEY is invalid or NIM is down.")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    """Run all Step 2 verification checks."""
    print("=" * 60)
    print("  GHOST Step 2 \u2014 Scoring & Classification Verification")
    print("=" * 60)

    try:
        test_trajectory_scoring()
        test_heuristic_classifier()
        test_live_classifier()
    except Exception as e:
        print(f"\n  \u2717 UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    if _failed == 0:
        print(f"  \u2705 Step 2 complete. Scoring and classification working.")
        print(f"  \U0001f4d6 Read STEP2_README.md to understand what was built.")
        print(f"  \u27a1\ufe0f  Next: paste the Step 3 prompt.")
    else:
        print(f"  \u274c {_failed} CHECK(S) FAILED out of {_passed + _failed}.")
    print("=" * 60)

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
