"""
GHOST API — Session endpoints.

Provides endpoints for listing sessions, viewing session details,
and retrieving trajectory adherence score series for charting.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["sessions"])

_DB_PATH = os.getenv("GHOST_DB_PATH", "db/ghost.db")


def _get_connection() -> sqlite3.Connection:
    """Open a read-only connection to the GHOST database."""
    db_path = _DB_PATH
    if not Path(db_path).exists():
        raise HTTPException(status_code=503, detail="Database not found. Run a GHOST session first.")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """
    Return the last 100 sessions, most recent first.

    Each session includes: session_id, task_type, status, total_steps,
    recovery_count, final_adherence, success, duration_seconds.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT session_id, task_type, objective, status,
                   total_steps, recovery_count, final_adherence,
                   success, started_at, ended_at
            FROM sessions
            ORDER BY started_at DESC
            LIMIT 100
            """
        )
        rows = cursor.fetchall()
        sessions = []
        for row in rows:
            started = row["started_at"]
            ended = row["ended_at"]
            duration = None
            if started and ended:
                duration = round(ended - started, 1)

            sessions.append({
                "session_id": row["session_id"],
                "task_type": row["task_type"],
                "objective": row["objective"],
                "status": row["status"] or "unknown",
                "total_steps": row["total_steps"] or 0,
                "recovery_count": row["recovery_count"] or 0,
                "final_adherence": row["final_adherence"],
                "success": row["success"],
                "duration_seconds": duration,
            })
        return sessions
    finally:
        conn.close()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """
    Return full session detail including every trajectory log step.
    """
    conn = _get_connection()
    try:
        # Get session info
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        started = session_row["started_at"]
        ended = session_row["ended_at"]
        duration = round(ended - started, 1) if started and ended else None

        session_info = {
            "session_id": session_row["session_id"],
            "task_type": session_row["task_type"],
            "objective": session_row["objective"],
            "status": session_row["status"] or "unknown",
            "total_steps": session_row["total_steps"] or 0,
            "recovery_count": session_row["recovery_count"] or 0,
            "final_adherence": session_row["final_adherence"],
            "success": session_row["success"],
            "duration_seconds": duration,
        }

        # Get trajectory log steps
        cursor = conn.execute(
            """
            SELECT step_number, tool_name, tool_input, tool_output,
                   tool_error, adherence_score, failure_detected,
                   failure_type, recovery_triggered, recovery_strategy,
                   timestamp
            FROM trajectory_logs
            WHERE session_id = ?
            ORDER BY step_number ASC
            """,
            (session_id,),
        )
        steps = []
        for row in cursor.fetchall():
            steps.append({
                "step_number": row["step_number"],
                "tool_name": row["tool_name"],
                "tool_input": row["tool_input"],
                "tool_output": row["tool_output"],
                "tool_error": row["tool_error"],
                "adherence_score": row["adherence_score"],
                "failure_detected": bool(row["failure_detected"]),
                "failure_type": row["failure_type"],
                "recovery_triggered": bool(row["recovery_triggered"]),
                "recovery_strategy": row["recovery_strategy"],
                "timestamp": row["timestamp"],
            })

        return {**session_info, "steps": steps}
    finally:
        conn.close()


@router.get("/sessions/{session_id}/trajectory")
async def get_trajectory(session_id: str) -> List[Dict[str, Any]]:
    """
    Return the adherence score time series for charting.

    Each entry: step, score, failure type (or null), recovery strategy (or null).
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT step_number, adherence_score, failure_type,
                   recovery_strategy, failure_detected, recovery_triggered
            FROM trajectory_logs
            WHERE session_id = ?
            ORDER BY step_number ASC
            """,
            (session_id,),
        )
        trajectory = []
        for row in cursor.fetchall():
            trajectory.append({
                "step": row["step_number"],
                "score": row["adherence_score"],
                "failure": row["failure_type"] if row["failure_detected"] else None,
                "recovery": row["recovery_strategy"] if row["recovery_triggered"] else None,
            })
        return trajectory
    finally:
        conn.close()
