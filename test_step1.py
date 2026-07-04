#!/usr/bin/env python3
"""
GHOST Step 1 — Foundation Verification Script.

Run with:
    python test_step1.py

This script validates that all Step 1 artifacts are correctly set up:
  1. Folder structure exists
  2. Required files exist
  3. Database initializes and tables are present
  4. CRUD operations work on all tables
  5. ChromaDB failure memory works end-to-end
  6. Cleanup of test artifacts

Exit code 0 = all checks passed, 1 = something failed.
"""

from __future__ import annotations

import gc
import json
import os
import shutil
import sqlite3
import stat
import sys
import time
import traceback
from pathlib import Path

# ─────────────────────────────────────────────
# Test configuration
# ─────────────────────────────────────────────

TEST_DB_PATH = "db/test_ghost.db"
TEST_CHROMA_PATH = "db/test_chroma"

# Counters
_passed = 0
_failed = 0

# Global reference to ChromaDB memory so we can close it before cleanup
_chroma_memory = None


def _rmtree_onerror(func, path, exc_info):
    """Error handler for shutil.rmtree on Windows — clears read-only and retries."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass  # Best-effort cleanup; don't fail the test suite for this


def check(condition: bool, label: str) -> bool:
    """Assert a condition and print the result."""
    global _passed, _failed
    if condition:
        print(f"  \u2713 {label}")
        _passed += 1
        return True
    else:
        print(f"  \u2717 {label}")
        _failed += 1
        return False


def section(number: int, title: str) -> None:
    """Print a section header."""
    print(f"\n[{number}/6] {title}")


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

def test_folder_structure() -> None:
    """Verify all expected directories exist."""
    section(1, "Checking folder structure...")
    dirs = [
        "ghost/core",
        "ghost/db",
        "ghost/api",
        "ghost/api/routes",
        "ghost/benchmarks",
        "ghost/benchmarks/results",
        "ghost/examples",
        "ghost/tests",
        "ghost/dashboard",
    ]
    for d in dirs:
        check(Path(d).is_dir(), f"{d}/ exists")


def test_required_files() -> None:
    """Verify all required files are present."""
    section(2, "Checking required files...")
    files = [
        ".env.example",
        ".gitignore",
        "requirements.txt",
        "db/__init__.py",
        "db/schema.py",
        "core/__init__.py",
        "core/memory.py",
    ]
    for f in files:
        check(Path(f).is_file(), f"{f} exists")


def test_database_init() -> None:
    """Verify database creates tables correctly."""
    section(3, "Initializing database...")

    # Set env var to use test database path
    os.environ["GHOST_DB_PATH"] = TEST_DB_PATH

    # Remove test db if it exists from a previous run
    if Path(TEST_DB_PATH).exists():
        os.remove(TEST_DB_PATH)

    # Import schema — this triggers init_db() via the module-level call,
    # but it will use the default DB_PATH. We call init_db() explicitly
    # with our test path.
    from db.schema import init_db, get_connection

    init_db(db_path=TEST_DB_PATH)
    check(Path(TEST_DB_PATH).exists(), f"Database created at {TEST_DB_PATH}")

    # Verify tables exist
    conn = get_connection(db_path=TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    check("sessions" in tables, "Table 'sessions' exists")
    check("trajectory_logs" in tables, "Table 'trajectory_logs' exists")
    check("successful_trajectories" in tables, "Table 'successful_trajectories' exists")


def test_database_operations() -> None:
    """Verify basic CRUD operations work on all tables."""
    section(4, "Testing database operations...")

    from db.schema import get_connection

    conn = get_connection(db_path=TEST_DB_PATH)
    cursor = conn.cursor()
    now = time.time()

    # Insert into sessions
    cursor.execute(
        """
        INSERT INTO sessions (session_id, task_type, objective, status, started_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test-session-001", "airline", "book a flight to NYC", "running", now),
    )
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_id = 'test-session-001'")
    check(cursor.fetchone()[0] == 1, "Insert into sessions works")

    # Insert into trajectory_logs
    cursor.execute(
        """
        INSERT INTO trajectory_logs
            (session_id, task_type, objective, step_number, tool_name,
             tool_input, tool_output, adherence_score, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "test-session-001", "airline", "book a flight to NYC", 1,
            "search_flights", '{"dest": "NYC"}', '{"flights": []}',
            0.95, now,
        ),
    )
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM trajectory_logs WHERE session_id = 'test-session-001'")
    check(cursor.fetchone()[0] == 1, "Insert into trajectory_logs works")

    # Insert into successful_trajectories
    cursor.execute(
        """
        INSERT INTO successful_trajectories (task_type, tool_sequence, total_steps, duration_secs, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("airline", json.dumps(["search_flights", "book_flight"]), 2, 12.5, now),
    )
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM successful_trajectories WHERE task_type = 'airline'")
    check(cursor.fetchone()[0] == 1, "Insert into successful_trajectories works")

    conn.close()


def test_chromadb_memory() -> None:
    """Verify ChromaDB failure memory works end-to-end."""
    global _chroma_memory
    section(5, "Testing ChromaDB memory...")

    # Clean up from previous runs
    if Path(TEST_CHROMA_PATH).exists():
        shutil.rmtree(TEST_CHROMA_PATH, onerror=_rmtree_onerror)

    from core.memory import FailureMemory

    memory = FailureMemory(persist_dir=TEST_CHROMA_PATH)
    _chroma_memory = memory  # Keep reference for cleanup
    check(memory is not None, "FailureMemory initialized")

    # Store a failure
    failure_id = memory.store_failure(
        task_type="airline",
        objective="book a flight to NYC",
        failure_type="wrong_tool",
        tool_sequence=["search_flights", "book_hotel"],
        recovery_strategy="retry_with_correct_tool",
    )
    check(
        failure_id is not None and failure_id.startswith("failure_"),
        "store_failure() works",
    )

    # Small delay to ensure ChromaDB has indexed the document
    time.sleep(0.5)

    # Query for warnings
    warnings = memory.get_warnings_for_task("airline", "book a flight to LA")
    check(
        warnings is not None and "wrong_tool" in warnings,
        "get_warnings_for_task() returns results",
    )

    # Get stats
    stats = memory.get_failure_stats()
    check(
        stats["total"] >= 1 and "wrong_tool" in stats.get("by_failure_type", {}),
        "get_failure_stats() returns stats",
    )


def test_cleanup() -> None:
    """Remove test artifacts."""
    global _chroma_memory
    section(6, "Cleanup...")

    # Remove test database
    for suffix in ["", "-wal", "-shm"]:
        path = Path(TEST_DB_PATH + suffix)
        if path.exists():
            os.remove(path)
    check(not Path(TEST_DB_PATH).exists(), "Test database removed")

    # Release ChromaDB client before attempting to delete its files.
    # On Windows, ChromaDB (via hnswlib) holds file locks that prevent
    # deletion until the client object is garbage-collected.
    if _chroma_memory is not None:
        try:
            # Reset the ChromaDB client to release file handles
            _chroma_memory.client._system.stop()
        except Exception:
            pass
        _chroma_memory = None
        gc.collect()
        time.sleep(0.5)  # Give OS time to release file locks

    # Remove test ChromaDB directory (with Windows-safe error handler)
    if Path(TEST_CHROMA_PATH).exists():
        shutil.rmtree(TEST_CHROMA_PATH, onerror=_rmtree_onerror)
    
    cleaned = not Path(TEST_CHROMA_PATH).exists()
    if not cleaned:
        # Second attempt after a longer pause
        time.sleep(1.0)
        gc.collect()
        shutil.rmtree(TEST_CHROMA_PATH, onerror=_rmtree_onerror)
        cleaned = not Path(TEST_CHROMA_PATH).exists()
    
    if cleaned:
        check(True, "Test ChromaDB directory removed")
    else:
        # Don't fail the entire suite for a cleanup issue on Windows
        print("  ⚠ Test ChromaDB directory could not be fully removed (Windows file lock).")
        print("    This is cosmetic — manually delete db/test_chroma/ if desired.")
        check(True, "Test ChromaDB cleanup attempted (Windows lock)")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    """Run all Step 1 verification checks."""
    print("=" * 60)
    print("  GHOST Step 1 \u2014 Foundation Verification")
    print("=" * 60)

    try:
        test_folder_structure()
        test_required_files()
        test_database_init()
        test_database_operations()
        test_chromadb_memory()
        test_cleanup()
    except Exception as e:
        print(f"\n  \u2717 UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    if _failed == 0:
        print(f"  \u2705 ALL {_passed} CHECKS PASSED \u2014 Step 1 foundation is solid.")
    else:
        print(f"  \u274c {_failed} CHECK(S) FAILED out of {_passed + _failed}.")
    print("=" * 60)

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
