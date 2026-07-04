from core.recovery import RecoveryEngine

FAILURE_TYPES = [
    "step_repetition_loop", "goal_drift", "tool_hallucination",
    "in_context_locking", "resource_exhaustion"
]

def test_all_failure_types_have_recovery():
    e = RecoveryEngine()
    for ft in FAILURE_TYPES:
        r = e.get_recovery(ft, objective="Fix the bug")
        assert r["strategy"] != "continue", f"{ft} should not continue"
        assert r["injection"] is not None, f"{ft} has no injection"

def test_objective_placeholder_filled():
    e = RecoveryEngine()
    r = e.get_recovery("goal_drift", objective="Write a Python script")
    # Case-insensitive validation of formatting
    injection_upper = r["injection"].upper()
    assert "WRITE A PYTHON SCRIPT" in injection_upper
    assert "{objective}" not in r["injection"]

def test_no_failure_returns_none_injection():
    e = RecoveryEngine()
    r = e.get_recovery("no_failure")
    assert r["injection"] is None

def test_recovery_appends_exact_reason():
    e = RecoveryEngine()
    r = e.get_recovery(
        "tool_hallucination",
        available_tools=["update_order"],
        recovery_reason="missing 1 required positional argument: order_id",
    )
    assert "missing 1 required positional argument: order_id" in r["injection"]
    assert "Reason:" in r["injection"]
