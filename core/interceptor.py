"""
GHOST Interceptor — LangChain callback handler and decorator.

This is the central integration point for GHOST. The ``GHOSTCallbackHandler``
hooks into LangChain's callback lifecycle to intercept every tool call, score
trajectory adherence, detect drift, classify failures, and trigger recovery —
all in real time.

The ``@ghost_monitor`` decorator provides a zero-config way to wrap any
function that calls a LangChain agent.

Usage (decorator):
    from core import ghost_monitor

    @ghost_monitor(task_type="web_research", objective="Research AI news")
    def run_agent(query):
        return agent_executor.invoke({"input": query})

Usage (handler):
    from core import GHOSTCallbackHandler

    handler = GHOSTCallbackHandler(
        task_type="web_research",
        objective="Research AI news",
    )
    result = agent_executor.invoke(
        {"input": "AI news"},
        config={"callbacks": [handler]},
    )
    print(handler.get_summary())
"""

from __future__ import annotations

import functools
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler

from .classifier import FailureClassifier
from .memory import FailureMemory
from .recovery import RecoveryEngine
from .trajectory import TrajectoryTracker
from db.schema import init_db

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("ghost.interceptor")

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class GHOSTCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that monitors agent tool calls in real time.

    On every tool call, the handler:
      1. Records the tool name and input
      2. After the tool completes, scores trajectory adherence
      3. If adherence drops below the drift threshold, classifies the failure
      4. Triggers the appropriate recovery strategy
      5. Logs everything to SQLite and ChromaDB

    Attributes:
        session_id: Unique identifier for this monitoring session.
        task_type: Category of the task being monitored.
        objective: The agent's stated goal.
        drift_threshold: Adherence score below which drift is triggered.
        verbose: Whether to print colored status output.
        tracker: Trajectory adherence scorer.
        classifier: MAST failure classifier.
        recovery: Recovery strategy engine.
        memory: ChromaDB failure memory.
        tool_call_sequence: Ordered list of tool names called.
        tool_call_details: Full detail records for each tool call.
        adherence_history: List of adherence scores over time.
        failure_log: List of failure/recovery events.
        recovery_count: Number of times recovery was triggered.
    """

    def __init__(
        self,
        task_type: str,
        objective: str,
        session_id: Optional[str] = None,
        drift_threshold: Optional[float] = None,
        verbose: bool = True,
    ) -> None:
        """
        Initialize the GHOST callback handler.

        Args:
            task_type: Category of the task (e.g. ``"web_research"``).
            objective: The agent's stated goal.
            session_id: Override session ID. Auto-generated if not provided.
            drift_threshold: Adherence score threshold for drift detection.
                             Defaults to ``GHOST_DRIFT_THRESHOLD`` env var or 0.4.
            verbose: Whether to print colored terminal output.
        """
        super().__init__()

        # Session identity
        self.session_id: str = session_id or f"ghost_{uuid4().hex[:8]}"
        self.task_type: str = task_type
        self.objective: str = objective
        self.verbose: bool = verbose

        # Drift threshold
        if drift_threshold is not None:
            self.drift_threshold: float = drift_threshold
        else:
            self.drift_threshold = float(
                os.getenv("GHOST_DRIFT_THRESHOLD", "0.4")
            )
        self.context_reset_confidence_threshold: float = float(
            os.getenv("GHOST_CONTEXT_RESET_CONFIDENCE_THRESHOLD", "0.85")
        )

        # Database path
        self._db_path: str = os.getenv("GHOST_DB_PATH", "db/ghost.db")

        # Ensure database tables exist
        init_db(self._db_path)

        # Initialize all GHOST components
        self.tracker: TrajectoryTracker = TrajectoryTracker(db_path=self._db_path)
        self.classifier: FailureClassifier = FailureClassifier()
        self.recovery: RecoveryEngine = RecoveryEngine()
        self.memory: FailureMemory = FailureMemory()

        # Session state
        self.tool_call_sequence: List[str] = []
        self.tool_call_details: List[Dict[str, Any]] = []
        self.adherence_history: List[float] = []
        self.failure_log: List[Dict[str, Any]] = []
        self.recovery_count: int = 0
        self.start_time: float = time.time()
        self._drift_cooldown: int = 0  # Prevents double-firing recovery
        self.pending_injection: Optional[str] = None
        self.pruning_data: Optional[Dict[str, Any]] = None  # Scratchpad pruning metadata

        # Check memory for prior warnings about this task type
        warnings = self.memory.get_warnings_for_task(task_type, objective)
        if warnings and self.verbose:
            print(
                f"{YELLOW}[GHOST ⚠️] Prior warnings: {warnings}{RESET}"
            )

        # Insert session record into database
        self._insert_session()

        if self.verbose:
            print(
                f"{GREEN}[GHOST 🟢] Session {self.session_id} started "
                f"| Task: {task_type}{RESET}"
            )

        logger.info(
            "[GHOST] Session %s started — task=%s, objective=%s, threshold=%.2f",
            self.session_id, task_type, objective, self.drift_threshold,
        )

    # ─────────────────────────────────────────
    # LangChain Callbacks
    # ─────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing."""
        tool_name = serialized.get("name", "unknown_tool")
        step_number = len(self.tool_call_sequence) + 1

        # Record the tool call
        self.tool_call_sequence.append(tool_name)
        self.tool_call_details.append({
            "tool": tool_name,
            "input": str(input_str)[:300],
            "step": step_number,
            "timestamp": time.time(),
        })

        if self.verbose:
            print(f"{BLUE}[GHOST 🔧] Step {step_number}: {tool_name}{RESET}")

        logger.debug(
            "[GHOST] Tool start — step=%d, tool=%s", step_number, tool_name
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes successfully."""
        # Attach output to the last recorded detail
        if self.tool_call_details:
            self.tool_call_details[-1]["output"] = str(output)[:400]

        # Run trajectory check
        self._check_trajectory()

    def on_tool_error(
        self, error: BaseException, **kwargs: Any
    ) -> None:
        """Called when a tool raises an error."""
        error_str = str(error)[:400]

        # Attach error to the last recorded detail
        if self.tool_call_details:
            self.tool_call_details[-1]["error"] = error_str

        if self.verbose:
            print(f"{RED}[GHOST ❌] Tool error: {error_str[:100]}{RESET}")

        logger.warning("[GHOST] Tool error at step %d: %s",
                       len(self.tool_call_sequence), error_str[:200])

        # Force drift handling on errors
        self._handle_drift(force=True)

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        """Called when the agent completes its task."""
        end_time = time.time()
        duration = end_time - self.start_time
        total_steps = len(self.tool_call_sequence)
        final_adherence = (
            self.adherence_history[-1] if self.adherence_history else None
        )

        # Determine success: completed with zero or few recoveries
        success = 1 if self.recovery_count <= 1 else 0

        # Update session record in database
        self._update_session(
            status="completed",
            total_steps=total_steps,
            final_adherence=final_adherence,
            success=success,
            ended_at=end_time,
        )

        # Save the trajectory as successful if no recoveries were needed
        if self.recovery_count == 0 and total_steps > 0:
            self.tracker.add_successful_trajectory(
                self.task_type, self.tool_call_sequence
            )

        if self.verbose:
            print(
                f"\n{GREEN}{BOLD}[GHOST ✅] Session complete "
                f"| Steps: {total_steps} "
                f"| Recoveries: {self.recovery_count} "
                f"| Duration: {duration:.1f}s{RESET}"
            )

        logger.info(
            "[GHOST] Session %s complete — steps=%d, recoveries=%d, "
            "duration=%.1fs, success=%d",
            self.session_id, total_steps, self.recovery_count,
            duration, success,
        )

    # ─────────────────────────────────────────
    # Trajectory Monitoring
    # ─────────────────────────────────────────

    def _check_trajectory(self) -> None:
        """
        Evaluate the current tool-call trajectory and trigger drift
        handling if the adherence score drops below the threshold.

        Only runs after 3+ tool calls, and respects the cooldown period
        after a recovery to avoid double-firing.
        """
        step_count = len(self.tool_call_sequence)

        # Decrement cooldown
        if self._drift_cooldown > 0:
            self._drift_cooldown -= 1

        # Need at least 3 steps for meaningful scoring
        if step_count < 3:
            return

        # Skip if in cooldown (just recovered, give agent time to adjust)
        if self._drift_cooldown > 0:
            return

        # Compute adherence score
        adherence = self.tracker.compute_adherence(
            self.task_type, self.tool_call_sequence
        )
        self.adherence_history.append(adherence)

        # Log step to database
        self._log_step_to_db(adherence)

        # Print colored score
        if self.verbose:
            if adherence >= 0.6:
                color, emoji = GREEN, "🟢"
            elif adherence >= 0.4:
                color, emoji = YELLOW, "🟡"
            else:
                color, emoji = RED, "🔴"
            print(
                f"{color}[GHOST 📊] Adherence: {adherence:.2f} ({emoji}){RESET}"
            )

        # Check for drift
        if adherence < self.drift_threshold:
            self._handle_drift()

    def _handle_drift(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Handle detected drift: classify the failure, get recovery strategy,
        store in memory, and log to database.

        Args:
            force: If True, skip cooldown check (used for tool errors).

        Returns:
            The recovery dict, or None if no intervention needed.
        """
        # ADD THIS GUARD — don't check until 2+ steps
        if len(self.tool_call_sequence) < 2:
            return None

        step_count = len(self.tool_call_sequence)

        # Set cooldown to prevent re-triggering for 3 steps
        self._drift_cooldown = 3

        if self.verbose:
            print(
                f"\n{RED}{BOLD}[GHOST 🚨] DRIFT DETECTED at step "
                f"{step_count}{RESET}"
            )

        # Classify the failure
        failure_type, confidence, reasoning = self.classifier.classify(
            tool_call_history=self.tool_call_details,
            objective=self.objective,
            step_count=step_count,
        )

        # Lower sensitivity: only use context_reset for high-confidence loops.
        if (
            failure_type == "step_repetition_loop"
            and confidence < self.context_reset_confidence_threshold
        ):
            if self.verbose:
                print(
                    f"{YELLOW}[GHOST ⚠️] Repetition loop confidence ({confidence:.2f}) "
                    f"is below threshold ({self.context_reset_confidence_threshold:.2f}). "
                    f"Giving the agent another chance.{RESET}"
                )
            logger.info(
                "[GHOST] Suppressed context_reset at step %d: confidence %.2f < %.2f",
                step_count,
                confidence,
                self.context_reset_confidence_threshold,
            )
            return None

        if self.verbose:
            print(
                f"{RED}[GHOST 🔬] Failure: {failure_type} "
                f"| Confidence: {confidence:.0%}{RESET}"
            )
            print(f"{RED}[GHOST 💭] Reasoning: {reasoning}{RESET}")

        if failure_type == "no_failure":
            logger.info("[GHOST] Drift score was low, but classifier found no failure")
            return None

        recovery_reason = reasoning
        if self.tool_call_details:
            latest_error = self.tool_call_details[-1].get("error")
            if latest_error and str(latest_error).strip():
                recovery_reason = str(latest_error)

        # Get recovery strategy
        recovery = self.recovery.get_recovery(
            failure_type=failure_type,
            objective=self.objective,
            available_tools=list(set(self.tool_call_sequence)),
            recovery_reason=recovery_reason,
        )

        if self.verbose:
            print(
                f"{YELLOW}[GHOST 🛠️] Recovery: {recovery['strategy']} → "
                f"{recovery['description']}{RESET}"
            )

        # Record the failure event
        failure_event = {
            "step": step_count,
            "failure_type": failure_type,
            "confidence": confidence,
            "reasoning": reasoning,
            "recovery_strategy": recovery["strategy"],
            "timestamp": time.time(),
        }
        self.failure_log.append(failure_event)
        self.recovery_count += 1

        # Store failure in ChromaDB for future warnings
        self.memory.store_failure(
            task_type=self.task_type,
            objective=self.objective,
            failure_type=failure_type,
            tool_sequence=self.tool_call_sequence.copy(),
            recovery_strategy=recovery["strategy"],
        )

        # Update the trajectory log with failure/recovery info
        self._log_step_to_db(
            adherence=self.adherence_history[-1] if self.adherence_history else 0.0,
            failure_type=failure_type,
            recovery_strategy=recovery["strategy"],
        )

        logger.warning(
            "[GHOST] Drift at step %d — %s (%.0f%%) → %s",
            step_count, failure_type, confidence * 100, recovery["strategy"],
        )

        # Store pending injection so the executor can insert it into the prompt
        if recovery.get("injection"):
            self.pending_injection = recovery["injection"]

        # For step_repetition_loop, compute scratchpad pruning metadata
        if failure_type == "step_repetition_loop":
            # Identify the repeated tool and how far back the loop started
            loop_tool = None
            loop_count = 0
            from collections import Counter
            last5 = self.tool_call_sequence[-5:]
            counts = Counter(last5)
            for tool_name, count in counts.most_common(1):
                if count >= 2:
                    loop_tool = tool_name
                    loop_count = count

            if loop_tool:
                # Find the earliest index in the sequence where the loop started
                prune_from = len(self.tool_call_sequence) - 1
                for i in range(len(self.tool_call_sequence) - 1, -1, -1):
                    if self.tool_call_sequence[i] == loop_tool:
                        prune_from = i
                    else:
                        break

                self.pruning_data = {
                    "loop_tool": loop_tool,
                    "loop_count": loop_count,
                    "prune_from_step": prune_from,  # 0-indexed into tool_call_sequence
                }

                if self.verbose:
                    print(
                        f"{YELLOW}[GHOST ✂️] Scratchpad pruning queued: "
                        f"tool={loop_tool}, count={loop_count}, "
                        f"prune_from_step={prune_from}{RESET}"
                    )

                logger.info(
                    "[GHOST] Pruning data set: tool=%s, count=%d, prune_from=%d",
                    loop_tool, loop_count, prune_from,
                )

        return recovery

    # ─────────────────────────────────────────
    # Database Operations
    # ─────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        """Open a connection to the GHOST database."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _insert_session(self) -> None:
        """Insert a new session record into the database."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions
                    (session_id, task_type, objective, status, started_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.session_id,
                    self.task_type,
                    self.objective,
                    "running",
                    self.start_time,
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to insert session: %s", e)
        finally:
            conn.close()

    def _update_session(
        self,
        status: str,
        total_steps: int,
        final_adherence: Optional[float],
        success: int,
        ended_at: float,
    ) -> None:
        """Update the session record with final results."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE sessions SET
                    status = ?,
                    total_steps = ?,
                    recovery_count = ?,
                    final_adherence = ?,
                    success = ?,
                    ended_at = ?
                WHERE session_id = ?
                """,
                (
                    status,
                    total_steps,
                    self.recovery_count,
                    final_adherence,
                    success,
                    ended_at,
                    self.session_id,
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to update session: %s", e)
        finally:
            conn.close()

    def _log_step_to_db(
        self,
        adherence: float,
        failure_type: Optional[str] = None,
        recovery_strategy: Optional[str] = None,
    ) -> None:
        """
        Insert a trajectory log entry for the current step.

        Args:
            adherence: The current adherence score.
            failure_type: If a failure was detected, its MAST type.
            recovery_strategy: If recovery was triggered, its strategy name.
        """
        if not self.tool_call_details:
            return

        detail = self.tool_call_details[-1]
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO trajectory_logs
                    (session_id, task_type, objective, step_number, tool_name,
                     tool_input, tool_output, tool_error, adherence_score,
                     failure_detected, failure_type, recovery_triggered,
                     recovery_strategy, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.session_id,
                    self.task_type,
                    self.objective,
                    detail.get("step", 0),
                    detail.get("tool", "unknown"),
                    detail.get("input", ""),
                    detail.get("output", ""),
                    detail.get("error"),
                    adherence,
                    1 if failure_type else 0,
                    failure_type,
                    1 if recovery_strategy else 0,
                    recovery_strategy,
                    detail.get("timestamp", time.time()),
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to log step: %s", e)
        finally:
            conn.close()

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a summary of the current monitoring session.

        Returns:
            A dict with session metadata, step counts, failure info,
            adherence history, and timing.
        """
        duration = time.time() - self.start_time
        return {
            "session_id": self.session_id,
            "task_type": self.task_type,
            "objective": self.objective,
            "total_steps": len(self.tool_call_sequence),
            "recovery_count": self.recovery_count,
            "failure_types_seen": list(
                {f["failure_type"] for f in self.failure_log}
            ),
            "final_adherence": (
                self.adherence_history[-1] if self.adherence_history else None
            ),
            "duration_seconds": duration,
            "adherence_history": self.adherence_history.copy(),
        }


# ─────────────────────────────────────────────
# Decorator
# ─────────────────────────────────────────────

def ghost_monitor(
    task_type: str = "general",
    objective: str = "",
    drift_threshold: float = 0.4,
):
    """
    Decorator that wraps a LangChain agent function with GHOST monitoring.

    Usage::

        @ghost_monitor(task_type="web_research", objective="Research AI news")
        def run_agent(query):
            return agent_executor.invoke({"input": query})

        result = run_agent("What are the latest AI breakthroughs?")

    The decorator automatically:
      - Creates a ``GHOSTCallbackHandler``
      - Injects it into the LangChain config callbacks
      - Prints a session summary after the agent completes

    Args:
        task_type: Category of the task.
        objective: The agent's stated goal.
        drift_threshold: Adherence score threshold for drift detection.

    Returns:
        A decorator function.
    """

    def decorator(agent_func):
        @functools.wraps(agent_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            handler = GHOSTCallbackHandler(
                task_type=task_type,
                objective=objective or "Complete the assigned task",
                drift_threshold=drift_threshold,
            )

            # Inject the handler into LangChain config callbacks
            if "config" not in kwargs:
                kwargs["config"] = {}
            if "callbacks" not in kwargs["config"]:
                kwargs["config"]["callbacks"] = []
            kwargs["config"]["callbacks"].append(handler)

            # Run the agent function
            result = agent_func(*args, **kwargs)

            # Print session summary
            summary = handler.get_summary()
            print(f"\n{BOLD}[GHOST] Session Summary:{RESET}")
            print(f"  Steps: {summary['total_steps']}")
            print(f"  Recoveries triggered: {summary['recovery_count']}")
            print(f"  Duration: {summary['duration_seconds']:.1f}s")
            if summary["failure_types_seen"]:
                print(
                    f"  Failure types: {', '.join(summary['failure_types_seen'])}"
                )

            return result

        return wrapper

    return decorator
