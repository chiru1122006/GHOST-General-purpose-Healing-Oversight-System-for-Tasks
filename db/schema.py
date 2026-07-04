"""
GHOST Database Schema — SQLite storage layer.

This module defines and initializes the SQLite database used by GHOST to persist:
  - Agent session metadata (sessions table)
  - Step-by-step tool call logs (trajectory_logs table)
  - Successful execution patterns for reference (successful_trajectories table)

On import, this module:
  1. Loads environment variables from .env
  2. Ensures the database directory exists
  3. Creates all tables (idempotent — safe to call repeatedly)
  4. Enables WAL mode for non-blocking concurrent reads

Usage:
    import db.schema  # Tables are auto-created on import
    conn = db.schema.get_connection()
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("ghost.db")

DB_PATH: str = os.getenv("GHOST_DB_PATH", "db/ghost.db")

# Ensure the parent directory exists so sqlite3.connect() doesn't fail
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# SQL Statements
# ─────────────────────────────────────────────

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    UNIQUE NOT NULL,
    task_type       TEXT,
    objective       TEXT,
    status          TEXT    DEFAULT 'running',   -- running | completed | failed
    total_steps     INTEGER DEFAULT 0,
    recovery_count  INTEGER DEFAULT 0,
    final_adherence REAL,
    success         INTEGER DEFAULT 0,           -- 0 or 1
    started_at      REAL,
    ended_at        REAL
);
"""

_CREATE_TRAJECTORY_LOGS = """
CREATE TABLE IF NOT EXISTS trajectory_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT    NOT NULL,
    task_type           TEXT    NOT NULL,
    objective           TEXT,
    step_number         INTEGER NOT NULL,
    tool_name           TEXT    NOT NULL,
    tool_input          TEXT,
    tool_output         TEXT,
    tool_error          TEXT,
    adherence_score     REAL,
    failure_detected    INTEGER DEFAULT 0,
    failure_type        TEXT,
    recovery_triggered  INTEGER DEFAULT 0,
    recovery_strategy   TEXT,
    timestamp           REAL    NOT NULL
);
"""

_CREATE_SUCCESSFUL_TRAJECTORIES = """
CREATE TABLE IF NOT EXISTS successful_trajectories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type     TEXT    NOT NULL,
    tool_sequence TEXT    NOT NULL,   -- JSON array of tool names
    total_steps   INTEGER,
    duration_secs REAL,
    created_at    REAL    NOT NULL
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_session_id      ON sessions (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_task_type        ON sessions (task_type);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_started_at       ON sessions (started_at);",
    "CREATE INDEX IF NOT EXISTS idx_traj_session_id           ON trajectory_logs (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_traj_task_type            ON trajectory_logs (task_type);",
    "CREATE INDEX IF NOT EXISTS idx_traj_timestamp            ON trajectory_logs (timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_success_task_type         ON successful_trajectories (task_type);",
    "CREATE INDEX IF NOT EXISTS idx_success_created_at        ON successful_trajectories (created_at);",
]


# ─────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Open a connection to the GHOST database.

    Args:
        db_path: Override path to the SQLite file. Defaults to ``DB_PATH``.

    Returns:
        A ``sqlite3.Connection`` with ``row_factory`` set to ``sqlite3.Row``
        so rows behave like dicts.
    """
    path = db_path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────

def init_db(db_path: Optional[str] = None) -> None:
    """
    Create all GHOST tables and indexes if they do not already exist.

    This function is idempotent — calling it multiple times is safe and will
    not destroy existing data.  It also enables WAL journal mode for better
    concurrency (non-blocking reads while writing).

    Args:
        db_path: Override path to the SQLite file. Defaults to ``DB_PATH``.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Enable WAL mode for non-blocking concurrent access
        cursor.execute("PRAGMA journal_mode=WAL;")
        wal_result = cursor.fetchone()
        logger.debug("Journal mode set to: %s", wal_result[0] if wal_result else "unknown")

        # Create tables
        cursor.execute(_CREATE_SESSIONS)
        cursor.execute(_CREATE_TRAJECTORY_LOGS)
        cursor.execute(_CREATE_SUCCESSFUL_TRAJECTORIES)

        # Create indexes for query performance
        for index_sql in _CREATE_INDEXES:
            cursor.execute(index_sql)

        conn.commit()
        logger.info("GHOST database initialized at: %s", db_path or DB_PATH)

    except sqlite3.Error as e:
        logger.error("Failed to initialize GHOST database: %s", e)
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Auto-initialize on import
# ─────────────────────────────────────────────
init_db()
