from core.interceptor import GHOSTCallbackHandler


class _StubClassifier:
    def __init__(self, failure_type, confidence):
        self.failure_type = failure_type
        self.confidence = confidence

    def classify(self, **kwargs):
        return self.failure_type, self.confidence, "stubbed classifier result"

def test_handler_initializes():
    h = GHOSTCallbackHandler(task_type="test", objective="do a thing")
    assert h.session_id.startswith("ghost_")
    assert h.tool_call_sequence == []
    assert h.recovery_count == 0

def test_tool_tracking():
    h = GHOSTCallbackHandler(task_type="test", objective="do a thing")
    h.on_tool_start({"name": "search_web"}, "some query")
    h.on_tool_end("some result")
    assert len(h.tool_call_sequence) == 1
    assert h.tool_call_sequence[0] == "search_web"
    
    # We require 3 steps for trajectory checking, let's verify sequence and history
    assert h.tool_call_details[0]["tool"] == "search_web"
    assert h.tool_call_details[0]["input"] == "some query"
    assert h.tool_call_details[0]["output"] == "some result"

def test_summary_structure():
    h = GHOSTCallbackHandler(task_type="test", objective="do a thing")
    summary = h.get_summary()
    required_keys = ["session_id", "task_type", "total_steps",
                     "recovery_count", "adherence_history", "duration_seconds"]
    for key in required_keys:
        assert key in summary, f"Missing key: {key}"


def test_low_confidence_context_reset_is_suppressed():
    h = GHOSTCallbackHandler(task_type="test", objective="do a thing", verbose=False)
    h.classifier = _StubClassifier("step_repetition_loop", 0.85)
    h.tool_call_sequence = ["search", "search", "search"]
    h.tool_call_details = [
        {"tool": "search", "input": "same", "step": 1},
        {"tool": "search", "input": "same", "step": 2},
        {"tool": "search", "input": "same", "step": 3},
    ]
    h.adherence_history = [0.05]

    recovery = h._handle_drift()

    assert recovery is None
    assert h.recovery_count == 0
    assert h.pending_injection is None
    assert h.failure_log == []
