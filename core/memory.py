"""
GHOST Failure Memory — ChromaDB vector store for failure patterns.

This module provides semantic search over past agent failures so that GHOST
can warn the agent (or the recovery engine) about previously encountered
pitfalls before they happen again.

Two ChromaDB collections are maintained:
  - ``ghost_failures``   — stores failure events with metadata
  - ``ghost_recoveries`` — stores what recovery strategy worked (future use)

Usage:
    from core.memory import FailureMemory

    memory = FailureMemory()
    memory.store_failure(
        task_type="airline",
        objective="book a flight to NYC",
        failure_type="wrong_tool",
        tool_sequence=["search_flights", "book_hotel"],
        recovery_strategy="retry_with_correct_tool",
    )

    warnings = memory.get_warnings_for_task("airline", "book a flight to LA")
    # => "Previously seen failures: wrong_tool fixed by retry_with_correct_tool"
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("ghost.memory")


class FailureMemory:
    """
    Semantic memory layer backed by ChromaDB.

    Stores past agent failures and their successful recoveries so GHOST can
    proactively warn agents about known failure modes for similar tasks.

    Attributes:
        persist_dir: Filesystem path where ChromaDB stores its data.
        client: The ChromaDB ``PersistentClient`` instance.
        failures: The ``ghost_failures`` collection.
        recoveries: The ``ghost_recoveries`` collection.
    """

    def __init__(self, persist_dir: Optional[str] = None) -> None:
        """
        Initialize the failure memory store.

        Args:
            persist_dir: Directory for ChromaDB persistence.
                         Defaults to ``GHOST_CHROMA_PATH`` env var or ``db/chroma``.
        """
        self.persist_dir: str = persist_dir or os.getenv(
            "GHOST_CHROMA_PATH", "db/chroma"
        )

        # Ensure the storage directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client: chromadb.ClientAPI = chromadb.PersistentClient(
            path=self.persist_dir
        )

        # Create (or get) the two collections
        self.failures: chromadb.Collection = self.client.get_or_create_collection(
            name="ghost_failures",
            metadata={"description": "Stores agent failure events with context"},
        )
        self.recoveries: chromadb.Collection = self.client.get_or_create_collection(
            name="ghost_recoveries",
            metadata={"description": "Stores successful recovery strategies"},
        )

        logger.info(
            "[GHOST Memory] Initialized — persist_dir=%s, failures=%d, recoveries=%d",
            self.persist_dir,
            self.failures.count(),
            self.recoveries.count(),
        )

    def store_failure(
        self,
        task_type: str,
        objective: str,
        failure_type: str,
        tool_sequence: List[str],
        recovery_strategy: str,
    ) -> str:
        """
        Store a failure event in the vector database.

        The failure is embedded as a natural-language document so that future
        semantic queries can surface it for similar tasks.

        Args:
            task_type: Category of the task (e.g., ``"airline"``, ``"retail"``).
            objective: The agent's goal at the time of failure.
            failure_type: Classification of the failure (e.g., ``"wrong_tool"``).
            tool_sequence: Ordered list of tool names the agent called.
            recovery_strategy: What GHOST did (or should do) to fix it.

        Returns:
            The unique ID assigned to this failure record.
        """
        joined_sequence = ", ".join(tool_sequence)
        document = (
            f"Task: {task_type}. "
            f"Goal: {objective}. "
            f"Failure: {failure_type}. "
            f"Tools used: {joined_sequence}"
        )

        timestamp_str = str(time.time())
        failure_id = f"failure_{int(time.time() * 1000)}"

        metadata: Dict[str, Any] = {
            "task_type": task_type,
            "objective": objective,
            "failure_type": failure_type,
            "tool_sequence": joined_sequence,
            "recovery_strategy": recovery_strategy,
            "timestamp": timestamp_str,
        }

        self.failures.add(
            documents=[document],
            metadatas=[metadata],
            ids=[failure_id],
        )

        logger.info("[GHOST Memory] Stored failure: %s", failure_type)
        print(f"[GHOST Memory] Stored failure: {failure_type}")

        return failure_id

    def get_warnings_for_task(
        self, task_type: str, objective: str
    ) -> Optional[str]:
        """
        Query past failures for warnings relevant to a new task.

        Performs a semantic similarity search against the failures collection
        and returns a human-readable summary of the most relevant past failures.

        Args:
            task_type: Category of the upcoming task.
            objective: The agent's stated goal.

        Returns:
            A formatted string of warnings, or ``None`` if no relevant
            failures are found.
        """
        total = self.failures.count()
        if total == 0:
            logger.debug("[GHOST Memory] No failures stored yet — no warnings.")
            return None

        query_text = f"Task: {task_type}. Goal: {objective}"
        n_results = min(3, total)

        results = self.failures.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        # ChromaDB returns nested lists: results["metadatas"][0] is the list
        # of metadata dicts for the first (and only) query.
        metadatas = results.get("metadatas")
        if not metadatas or not metadatas[0]:
            logger.debug("[GHOST Memory] Query returned no results.")
            return None

        warnings_parts: List[str] = []
        for meta in metadatas[0]:
            failure = meta.get("failure_type", "unknown")
            strategy = meta.get("recovery_strategy", "unknown")
            warnings_parts.append(f"{failure} fixed by {strategy}")

        warning_text = "Previously seen failures: " + "; ".join(warnings_parts)
        logger.info("[GHOST Memory] Returning warnings: %s", warning_text)
        return warning_text

    def get_failure_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about stored failures.

        Returns:
            A dict with:
              - ``total``: Total number of stored failures.
              - ``by_failure_type``: Mapping of failure_type → count.
        """
        total = self.failures.count()
        by_type: Dict[str, int] = {}

        if total > 0:
            # Retrieve all metadata to compute breakdown
            all_data = self.failures.get(include=["metadatas"])
            for meta in all_data.get("metadatas", []):
                ft = meta.get("failure_type", "unknown")
                by_type[ft] = by_type.get(ft, 0) + 1

        stats = {
            "total": total,
            "by_failure_type": by_type,
        }

        logger.debug("[GHOST Memory] Stats: %s", stats)
        return stats
