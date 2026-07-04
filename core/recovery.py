"""
GHOST Recovery Engine — Failure-specific intervention strategies.

This module maps each MAST failure type to a specific recovery strategy
with a pre-written note that gets appended to the agent's next context
window. Injections are intentionally short and non-destructive so the
agent keeps its working memory while receiving a gentle course correction.

Usage:
    from core.recovery import RecoveryEngine

    engine = RecoveryEngine()
    recovery = engine.get_recovery(
        failure_type="step_repetition_loop",
        objective="book a flight to NYC",
        available_tools=["search_flights", "book_flight", "read_page"],
    )
    print(recovery["injection"])  # Direct corrective text
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ghost.recovery")


class RecoveryEngine:
    """
    Maps MAST failure types to recovery strategies with injection prompts.

    Each recovery entry contains:
      - ``strategy``: Short name for the recovery approach.
      - ``description``: One-sentence explanation of what it does.
      - ``priority``: Severity level 1–5 (5 = highest urgency).
      - ``injection``: The corrective text injected into the agent's next prompt.

    The ``{objective}`` and ``{available_tools}`` placeholders in injection
    strings are replaced with actual values at runtime.
    """

    RECOVERY_TABLE: Dict[str, Dict[str, Any]] = {
        "step_repetition_loop": {
            "strategy": "scratchpad_prune",
            "description": "Prunes repetitive scratchpad entries and injects a synthetic memory forcing the agent to pivot.",
            "priority": 5,
            "injection": (
                "[SYSTEM INTERVENTION]: You attempted to use the same tool repeatedly "
                "with inputs that did not progress the objective. "
                "Those failed attempts have been wiped from your memory to save space. "
                "CRITICAL: You must now use a DIFFERENT tool or provide your Final Answer. "
                "Do NOT call the same tool again."
            ),
        },
        "goal_drift": {
            "strategy": "objective_reinjection",
            "description": "Re-injects the original objective and forces the agent to reconnect its actions to the goal.",
            "priority": 5,
            "injection": "Note: Please stay focused on the original objective: {objective}. Ensure your next action directly serves this goal.",
        },
        "tool_hallucination": {
            "strategy": "output_validation",
            "description": "Reminds the agent to verify tool existence and argument validity before the next call.",
            "priority": 3,
            "injection": "Note: Please call only valid tools from the available list: {available_tools}. Make sure to pass the correct arguments.",
        },
        "in_context_locking": {
            "strategy": "forced_exploration",
            "description": "Suggests switching away from the current failing approach.",
            "priority": 3,
            "injection": "Note: That approach is not working. Please try a different path or tool.",
        },
        "resource_exhaustion": {
            "strategy": "efficiency_mode",
            "description": "Switches the agent into efficiency mode with a strict step budget for completion.",
            "priority": 4,
            "injection": "Note: You are running out of steps. Please focus on completing the task and providing a final answer directly.",
        },
        "no_failure": {
            "strategy": "continue",
            "description": "No failure detected — agent continues without intervention.",
            "priority": 1,
            "injection": None,
        },
    }

    def get_recovery(
        self,
        failure_type: str,
        objective: str = "",
        available_tools: Optional[List[str]] = None,
        recovery_reason: str = "",
    ) -> Dict[str, Any]:
        """
        Look up the recovery strategy for a given failure type.

        Replaces ``{objective}`` and ``{available_tools}`` placeholders in
        the injection text with actual values.

        Args:
            failure_type: One of the MAST failure type strings.
            objective: The agent's original stated goal.
            available_tools: List of tool names available to the agent.
            recovery_reason: Exact tool error or classifier reason to teach the
                agent why the correction is being appended.

        Returns:
            A dict with keys: ``strategy``, ``description``, ``priority``,
            ``injection`` (str or None).
        """
        if available_tools is None:
            available_tools = []

        # Look up with fallback to no_failure
        entry = self.RECOVERY_TABLE.get(
            failure_type, self.RECOVERY_TABLE["no_failure"]
        )

        # Deep copy to avoid mutating the class constant
        result: Dict[str, Any] = {
            "strategy": entry["strategy"],
            "description": entry["description"],
            "priority": entry["priority"],
            "injection": entry["injection"],
            "failure_type": failure_type,
        }

        # Fill in placeholders
        if result["injection"] is not None:
            tools_str = ", ".join(available_tools) if available_tools else "not available"
            result["injection"] = (
                result["injection"]
                .replace("{objective}", objective or "complete the assigned task")
                .replace("{available_tools}", tools_str)
            )
            reason = recovery_reason.strip()
            if reason:
                result["injection"] = (
                    f"{result['injection']} Reason: {reason[:300]}"
                )

        logger.info(
            "[GHOST Recovery] %s → %s (priority %d)",
            failure_type, result["strategy"], result["priority"],
        )
        return result

    def format_injection(
        self,
        failure_type: str,
        objective: str = "",
        available_tools: Optional[List[str]] = None,
        recovery_reason: str = "",
    ) -> Optional[str]:
        """
        Return just the injection string for a failure type, ready to be
        inserted into the agent's next prompt.

        Args:
            failure_type: One of the MAST failure type strings.
            objective: The agent's original stated goal.
            available_tools: List of tool names available to the agent.
            recovery_reason: Exact tool error or classifier reason to append.

        Returns:
            The injection string, or ``None`` if no recovery is needed.
        """
        recovery = self.get_recovery(
            failure_type,
            objective,
            available_tools,
            recovery_reason,
        )
        return recovery["injection"]
