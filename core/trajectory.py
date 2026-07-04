"""
GHOST Trajectory Tracker — Adherence scoring engine.

This module compares an agent's current tool-call sequence against previously
successful trajectories for the same task type.  It produces a score between
0.0 (completely off-track) and 1.0 (perfectly aligned) using a weighted blend
of Jaccard set-similarity (0.6) and embedding cosine similarity (0.4).

Embedding is handled by ChromaDB's built-in ONNX model (all-MiniLM-L6-v2),
which avoids a heavy PyTorch dependency while using the same underlying model.

Pathological patterns (loops, runaway sequences) are detected first and
short-circuit the scoring with appropriately low values.

Usage:
    from core.trajectory import TrajectoryTracker

    tracker = TrajectoryTracker()
    score = tracker.compute_adherence(
        task_type="web_research",
        current_sequence=["search_web", "read_page", "extract_info"],
    )
    # score ≈ 0.78
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("ghost.trajectory")

# Default reference trajectories, seeded on first run so that scoring
# works even before the system has observed any real agent executions.
_DEFAULT_TRAJECTORIES: Dict[str, List[str]] = {
    "web_research": [
        "search_web", "read_page", "search_web",
        "read_page", "extract_info", "summarize",
    ],
    "code_task": [
        "read_file", "analyze_code", "write_code",
        "run_tests", "fix_errors", "run_tests", "finalize",
    ],
    "data_analysis": [
        "load_data", "inspect_data", "clean_data",
        "run_analysis", "create_visualization", "write_report",
    ],
    "file_task": [
        "list_directory", "read_file", "process_content",
        "validate_output", "write_file",
    ],
    "customer_support": [
        "read_query", "search_knowledge_base",
        "retrieve_info", "compose_response", "send_response",
    ],
}


class TrajectoryTracker:
    """
    Scores how closely an agent's current tool-call sequence matches
    previously successful trajectories for the same task type.

    Scoring is a weighted combination of:
      - **Jaccard similarity** (weight 0.6): set-overlap of tool names
      - **Embedding cosine similarity** (weight 0.4): semantic similarity
        of the tool-call sequence treated as a sentence

    Pathological patterns are detected first and override the score:
      - Tool repeated 3+ times in last 5 steps → 0.05
      - Sequence length > 15 steps             → 0.15
      - Empty sequence                         → 0.70

    Attributes:
        db_path: Path to the GHOST SQLite database.
        encoder: ChromaDB's default embedding function (all-MiniLM-L6-v2 via ONNX).
    """

    # Scoring weights
    _JACCARD_WEIGHT: float = 0.6
    _EMBEDDING_WEIGHT: float = 0.4

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize the trajectory tracker.

        Args:
            db_path: Override path to the SQLite database.
                     Defaults to ``GHOST_DB_PATH`` env var or ``db/ghost.db``.
        """
        self.db_path: str = db_path or os.getenv("GHOST_DB_PATH", "db/ghost.db")

        # Use ChromaDB's built-in ONNX embedding function (all-MiniLM-L6-v2).
        # This avoids the heavy PyTorch/sentence-transformers dependency
        # while using the exact same model underneath.
        self.encoder: DefaultEmbeddingFunction = DefaultEmbeddingFunction()
        print("[GHOST Trajectory] Loaded embedding model")
        logger.info(
            "[GHOST Trajectory] Loaded embedding model: "
            "all-MiniLM-L6-v2 (ONNX via ChromaDB)"
        )

        # Ensure the database tables exist
        import db.schema
        db.schema.init_db(self.db_path)

        # Seed default trajectories if the database is empty
        self._seed_successful_trajectories()

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def compute_adherence(
        self, task_type: str, current_sequence: List[str]
    ) -> float:
        """
        Compute how closely *current_sequence* adheres to known-good
        trajectories for *task_type*.

        Args:
            task_type: Category of the task (e.g. ``"web_research"``).
            current_sequence: Ordered list of tool names the agent has
                              called so far.

        Returns:
            A float in ``[0.0, 1.0]`` where higher = more adherent.
        """
        # ── Step 1: Pathological-pattern short-circuits ──────────
        if not current_sequence:
            logger.debug("Empty sequence → returning 0.7 (neutral)")
            return 0.7

        # Repetition loop: same tool ≥3 times in the last 5 steps
        last5 = current_sequence[-5:]
        counts = Counter(last5)
        if any(c >= 3 for c in counts.values()):
            logger.warning(
                "Repetition loop detected in last 5 steps: %s", last5
            )
            return 0.05

        # Runaway sequence
        if len(current_sequence) > 15:
            logger.warning(
                "Sequence length %d exceeds 15 → returning 0.15",
                len(current_sequence),
            )
            return 0.15

        # ── Step 2: Load successful trajectories ─────────────────
        successful_sequences = self._load_successful_sequences(task_type)
        if not successful_sequences:
            logger.debug(
                "No successful trajectories for task_type=%s → neutral 0.7",
                task_type,
            )
            return 0.7

        # ── Step 3: Jaccard similarity (set overlap) ─────────────
        jaccard_score = self._best_jaccard(current_sequence, successful_sequences)

        # ── Step 4: Embedding cosine similarity ──────────────────
        embedding_score = self._best_embedding_similarity(
            current_sequence, successful_sequences
        )

        # ── Step 5: Weighted combination, clamped to [0, 1] ─────
        combined = (
            jaccard_score * self._JACCARD_WEIGHT
            + embedding_score * self._EMBEDDING_WEIGHT
        )
        result = float(np.clip(combined, 0.0, 1.0))

        logger.info(
            "Adherence for %s: jaccard=%.3f, embedding=%.3f, combined=%.3f",
            task_type, jaccard_score, embedding_score, result,
        )
        return result

    def add_successful_trajectory(
        self, task_type: str, tool_sequence: List[str]
    ) -> None:
        """
        Persist a successful trajectory so future scoring can reference it.

        Args:
            task_type: Category of the task.
            tool_sequence: Ordered list of tool names that led to success.
        """
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO successful_trajectories
                    (task_type, tool_sequence, total_steps, duration_secs, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task_type,
                    json.dumps(tool_sequence),
                    len(tool_sequence),
                    0.0,
                    time.time(),
                ),
            )
            conn.commit()
            print(f"[GHOST Trajectory] Saved successful path for {task_type}")
            logger.info(
                "[GHOST Trajectory] Saved successful path for %s (%d steps)",
                task_type, len(tool_sequence),
            )
        finally:
            conn.close()

    # ─────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the GHOST database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_successful_sequences(self, task_type: str) -> List[List[str]]:
        """
        Load all known-good tool sequences for *task_type* from SQLite.

        Returns:
            A list of tool-name lists, one per successful trajectory.
        """
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT tool_sequence FROM successful_trajectories WHERE task_type = ?",
                (task_type,),
            )
            rows = cursor.fetchall()
            sequences: List[List[str]] = []
            for row in rows:
                try:
                    seq = json.loads(row["tool_sequence"])
                    if isinstance(seq, list):
                        sequences.append(seq)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed tool_sequence row")
            return sequences
        finally:
            conn.close()

    def _best_jaccard(
        self, current: List[str], successes: List[List[str]]
    ) -> float:
        """
        Compute the maximum Jaccard similarity between *current* and each
        sequence in *successes*.

        Jaccard(A, B) = |A ∩ B| / |A ∪ B|
        """
        current_set = set(current)
        best = 0.0
        for success in successes:
            success_set = set(success)
            intersection = len(current_set & success_set)
            union = len(current_set | success_set)
            if union == 0:
                continue
            score = intersection / union
            best = max(best, score)
        return best

    def _embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a list of texts using ChromaDB's default embedding function.

        Args:
            texts: List of strings to embed.

        Returns:
            List of numpy arrays, one embedding per input text.
        """
        # DefaultEmbeddingFunction.__call__ returns List[List[float]]
        raw_embeddings = self.encoder(texts)
        return [np.array(emb, dtype=np.float32) for emb in raw_embeddings]

    def _best_embedding_similarity(
        self, current: List[str], successes: List[List[str]]
    ) -> float:
        """
        Compute the maximum cosine similarity between the embedding of
        *current* (joined as a sentence) and each *success* sequence.

        Uses ChromaDB's built-in all-MiniLM-L6-v2 ONNX model.
        """
        current_text = " → ".join(current)
        success_texts = [" → ".join(seq) for seq in successes]

        # Encode all texts in a single batch for efficiency
        all_texts = [current_text] + success_texts
        embeddings = self._embed_texts(all_texts)

        current_emb = embeddings[0]
        best = 0.0
        for i in range(1, len(embeddings)):
            sim = self._cosine_similarity(current_emb, embeddings[i])
            best = max(best, sim)
        return best

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        cosine_sim(a, b) = (a · b) / (‖a‖ × ‖b‖)

        Returns 0.0 if either vector has zero norm (degenerate case).
        """
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _seed_successful_trajectories(self) -> None:
        """
        Insert default reference trajectories for common task types if
        the database has no entries for them yet.

        This ensures that scoring works out-of-the-box before the system
        has observed any real agent executions.
        """
        conn = self._connect()
        try:
            for task_type, sequence in _DEFAULT_TRAJECTORIES.items():
                cursor = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM successful_trajectories WHERE task_type = ?",
                    (task_type,),
                )
                row = cursor.fetchone()
                if row["cnt"] == 0:
                    conn.execute(
                        """
                        INSERT INTO successful_trajectories
                            (task_type, tool_sequence, total_steps, duration_secs, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            task_type,
                            json.dumps(sequence),
                            len(sequence),
                            0.0,
                            time.time(),
                        ),
                    )
                    logger.debug("Seeded trajectory for task_type=%s", task_type)
            conn.commit()
            logger.info("Default trajectories seeded.")
        finally:
            conn.close()
