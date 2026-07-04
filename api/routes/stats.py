"""
GHOST API — Aggregate statistics endpoint.

Provides a single endpoint that returns dashboard-level metrics
aggregated from the sessions and trajectory_logs tables.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["stats"])

_DB_PATH = os.getenv("GHOST_DB_PATH", "db/ghost.db")


def _get_connection() -> sqlite3.Connection:
    """Open a read-only connection to the GHOST database."""
    db_path = _DB_PATH
    if not Path(db_path).exists():
        raise HTTPException(status_code=503, detail="Database not found. Run a GHOST session first.")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Return aggregate statistics for the dashboard header cards.

    Includes: total_sessions, successful_sessions, success_rate,
    total_recoveries, failure_breakdown, avg_adherence.
    """
    conn = _get_connection()
    try:
        # Total sessions
        row = conn.execute("SELECT COUNT(*) AS cnt FROM sessions").fetchone()
        total_sessions = row["cnt"]

        # Successful sessions
        row = conn.execute("SELECT COUNT(*) AS cnt FROM sessions WHERE success = 1").fetchone()
        successful_sessions = row["cnt"]

        # Success rate
        success_rate = 0.0
        if total_sessions > 0:
            success_rate = round((successful_sessions / total_sessions) * 100, 1)

        # Total recoveries
        row = conn.execute(
            "SELECT COALESCE(SUM(recovery_count), 0) AS total FROM sessions"
        ).fetchone()
        total_recoveries = row["total"]

        # Failure breakdown from trajectory_logs
        cursor = conn.execute(
            """
            SELECT failure_type, COUNT(*) AS cnt
            FROM trajectory_logs
            WHERE failure_detected = 1 AND failure_type IS NOT NULL
            GROUP BY failure_type
            ORDER BY cnt DESC
            """
        )
        failure_breakdown: Dict[str, int] = {}
        total_failures = 0
        for frow in cursor.fetchall():
            failure_breakdown[frow["failure_type"]] = frow["cnt"]
            total_failures += frow["cnt"]

        # Average adherence score
        row = conn.execute(
            "SELECT COALESCE(AVG(adherence_score), 0) AS avg_score FROM trajectory_logs"
        ).fetchone()
        avg_adherence = round(row["avg_score"], 3)

        # Memory stats (if available)
        memory_stats = {}
        try:
            from core.memory import FailureMemory
            memory = FailureMemory()
            if hasattr(memory, "get_failure_stats"):
                memory_stats = memory.get_failure_stats()
        except Exception:
            pass  # ChromaDB may not be available

        return {
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "success_rate": success_rate,
            "total_recoveries": total_recoveries,
            "total_failures": total_failures,
            "failure_breakdown": failure_breakdown,
            "avg_adherence": avg_adherence,
            "memory_stats": memory_stats,
        }
    finally:
        conn.close()
