"""
GHOST Failure Classifier — MAST taxonomy failure detection.

This module classifies AI agent failures into the MAST (Multi-Agent System
Taxonomy) categories using NVIDIA NIM's Llama 3.1 70B model, with a pure-Python
heuristic fallback for when the API is unavailable.

Failure types (snake_case):
  - step_repetition_loop  — agent repeats the same tool call
  - goal_drift            — agent wanders from the original objective
  - tool_hallucination    — agent calls non-existent tools or malformed inputs
  - in_context_locking    — agent fixates on one approach despite failures
  - resource_exhaustion   — agent takes too many steps without producing output
  - no_failure            — no failure pattern detected

Usage:
    from core.classifier import FailureClassifier

    classifier = FailureClassifier()
    failure_type, confidence, reasoning = classifier.classify(
        tool_call_history=[...],
        objective="book a flight to NYC",
        step_count=8,
    )
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("ghost.classifier")


class FailureClassifier:
    """
    Classifies AI agent failures into the MAST taxonomy.

    Uses NVIDIA NIM (Llama 3.1 70B) as the primary classifier, with a
    deterministic heuristic fallback for reliability when the API is
    unavailable, rate-limited, or returns malformed responses.

    Attributes:
        client: The OpenAI-compatible client pointed at NVIDIA NIM.
        model: The NIM model identifier.
        max_retries: Number of retry attempts on API/parse failures.
    """

    # ─────────────────────────────────────────
    # System prompt — instructs the LLM on MAST taxonomy
    # ─────────────────────────────────────────

    SYSTEM_PROMPT: str = """You are a MAST (Multi-Agent System Taxonomy) failure classifier for AI agents.

Your job is to analyze an AI agent's tool-call history and classify the failure mode into exactly ONE of the following categories. Use the exact snake_case name.

## Failure Types

1. **step_repetition_loop** — The agent calls the same tool with the same or nearly identical input multiple times in succession without making progress.
   Example: The agent calls search_flights("NYC to LAX") three times in a row, getting the same results each time.

2. **goal_drift** — The agent starts working on the correct task but gradually shifts to unrelated activities, losing sight of the original objective.
   Example: Tasked with booking a flight, the agent starts searching for restaurants and local attractions instead.

3. **tool_hallucination** — The agent attempts to call tools that do not exist or passes structurally invalid inputs, resulting in repeated errors.
   Example: The agent calls "send_email", "email_user", and "dispatch_email" — none of which exist in its toolkit.

4. **in_context_locking** — The agent fixates on a single approach or piece of information, unable to pivot to alternatives even when the current approach is failing.
   Example: The agent keeps rephrasing the same web search query instead of trying a different tool like a database lookup.

5. **resource_exhaustion** — The agent takes an excessive number of steps (>12) without producing any output or deliverable, consuming resources without converging.
   Example: After 15 steps of searching and reading, the agent has not written, sent, or produced any output.

6. **no_failure** — The agent's behavior appears normal and on-track. No failure pattern is detected.
   Example: The agent follows a logical sequence of search → read → extract → write with no errors or repetition.

## Output Format

You MUST respond with ONLY a JSON object. No markdown formatting, no code fences, no explanation outside the JSON.

{"failure_type": "step_repetition_loop", "confidence": 0.85, "reasoning": "One sentence explaining why"}

## Rules
- confidence must be a float between 0.0 and 0.99. Never return 1.0 — always reflect genuine uncertainty.
- failure_type must be one of the 6 exact snake_case names listed above.
- reasoning must be a single concise sentence.
- Do NOT wrap the JSON in ```json``` or any other formatting."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
    ) -> None:
        """
        Initialize the failure classifier.

        Args:
            model: NVIDIA NIM model identifier for classification.
        """
        self.api_keys: List[str] = self._get_api_keys()
        self.clients: List[OpenAI] = [
            OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key,
                timeout=30,
            )
            for api_key in self.api_keys
        ]
        if not self.clients:
            self.clients = [
                OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key="not-set",
                    timeout=30,
                )
            ]
        self.model: str = model
        self.max_retries: int = 2

        logger.info(
            "[GHOST Classifier] Initialized with model=%s, api_key=%s",
            model,
            "set" if self.api_keys else "NOT SET",
        )

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def classify(
        self,
        tool_call_history: List[Dict[str, Any]],
        objective: str,
        step_count: int,
    ) -> Tuple[str, float, str]:
        """
        Classify the failure mode of an agent's tool-call history.

        Sends the history to NVIDIA NIM for LLM-based classification.
        On failure, falls back to the deterministic heuristic classifier.

        Args:
            tool_call_history: List of dicts, each with keys
                ``tool``, ``input``, ``output``, and optionally ``error``.
            objective: The agent's original stated goal.
            step_count: Total number of steps the agent has taken.

        Returns:
            A tuple of ``(failure_type, confidence, reasoning)``.
        """
        formatted = self._format_history(tool_call_history)

        user_message = (
            f"Original objective: {objective}\n"
            f"Total steps taken: {step_count}\n\n"
            f"Tool call history (most recent last):\n{formatted}\n\n"
            f"Classify the failure type."
        )

        # ── Attempt 1: Full classification ───────────────────────
        for attempt in range(self.max_retries):
            try:
                if attempt == 0:
                    result = self._call_nim(user_message)
                else:
                    # Simplified retry prompt with fewer steps
                    last3 = self._format_history(tool_call_history[-3:])
                    retry_message = (
                        f'Return only JSON: {{"failure_type": "...", '
                        f'"confidence": 0.85, "reasoning": "..."}}\n'
                        f"History: {last3}"
                    )
                    result = self._call_nim(retry_message)

                return self._parse_response(result)

            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON parse failed on attempt %d: %s", attempt + 1, e
                )
                continue

            except Exception as e:
                logger.warning(
                    "NIM API error on attempt %d: %s", attempt + 1, e
                )
                continue

        # ── All retries exhausted — use heuristic fallback ───────
        logger.warning("All NIM attempts failed, falling back to heuristic")
        return self._heuristic_classify(tool_call_history)

    # ─────────────────────────────────────────
    # Heuristic fallback (pure Python, no LLM)
    # ─────────────────────────────────────────

    def _heuristic_classify(
        self, history: List[Dict[str, Any]]
    ) -> Tuple[str, float, str]:
        """
        Deterministic, rule-based failure classifier.

        Used as a reliable fallback when the NIM API is unavailable or
        returns malformed responses. Checks patterns in priority order.

        Args:
            history: List of tool-call dicts.

        Returns:
            A tuple of ``(failure_type, confidence, reasoning)``.
        """
        tools = [h.get("tool", "") for h in history]
        last5 = tools[-5:]

        # Rule 1: Step repetition loop — any tool appears 3+ times in last 5
        from collections import Counter

        counts = Counter(last5)
        for tool, count in counts.items():
            if count >= 3:
                return (
                    "step_repetition_loop",
                    0.95,
                    f"Same tool repeated {count}+ times in last 5 steps",
                )

        # Rule 2: Tool hallucination — multiple errors in recent steps
        recent = history[-4:]
        error_count = sum(
            1 for h in recent
            if h.get("error") is not None and str(h.get("error", "")).strip() != ""
        )
        if error_count >= 2:
            return (
                "tool_hallucination",
                0.75,
                "Multiple tool errors in recent steps",
            )

        # Rule 3: Resource exhaustion — many steps with no output tool
        output_keywords = {"write", "output", "final", "send", "submit", "save"}
        if len(history) > 12:
            has_output = any(
                any(kw in t.lower() for kw in output_keywords)
                for t in tools
            )
            if not has_output:
                return (
                    "resource_exhaustion",
                    0.65,
                    "Many steps with no output-producing tool",
                )

        # Default: no clear failure
        return (
            "no_failure",
            0.5,
            "No clear failure pattern detected",
        )

    # ─────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────

    def _format_history(
        self, history: List[Dict[str, Any]]
    ) -> str:
        """
        Format tool-call history into a human-readable string for the LLM.

        Uses only the last 10 entries to keep the prompt within token limits.

        Args:
            history: Full list of tool-call dicts.

        Returns:
            A multi-line string of formatted steps.
        """
        # Only use the last 10 entries
        recent = history[-10:]
        lines: List[str] = []

        for i, entry in enumerate(recent, start=1):
            tool = entry.get("tool", "unknown")
            inp = str(entry.get("input", ""))[:80]
            error = entry.get("error")

            if error and str(error).strip():
                out_str = f"ERROR: {str(error)[:80]}"
            else:
                out = str(entry.get("output", ""))[:80]
                out_str = f"OUTPUT: {out}"

            lines.append(f"Step {i}: [{tool}] INPUT: {inp} → {out_str}")

        return "\n".join(lines)

    def _get_api_keys(self) -> List[str]:
        """Return NVIDIA API keys in fallback order."""
        keys = [
            os.getenv("NVIDIA_API_KEY_1", "").strip() or os.getenv("NVIDIA_API_KEY1", "").strip(),
            os.getenv("NVIDIA_API_KEY_2", "").strip() or os.getenv("NVIDIA_API_KEY2", "").strip(),
        ]
        legacy_key = os.getenv("NVIDIA_API_KEY", "").strip()
        if legacy_key and legacy_key != "your_nvidia_nim_api_key_here":
            keys.append(legacy_key)

        seen = set()
        return [key for key in keys if key and not (key in seen or seen.add(key))]

    def _call_nim(self, user_message: str) -> str:
        """
        Send a classification request to the NVIDIA NIM API.

        Args:
            user_message: The formatted user prompt.

        Returns:
            The raw text content of the API response.

        Raises:
            Exception: On any API error.
        """
        last_error: Optional[BaseException] = None
        for attempt in range(3):
            for client in self.clients:
                try:
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": user_message},
                        ],
                        temperature=1,
                        top_p=1,
                        max_tokens=4096,
                        stream=False,
                    )

                    content = response.choices[0].message.content
                    if content is None or not str(content).strip():
                        raise ValueError("NIM API returned empty content")

                    logger.debug("NIM raw response: %s", content)
                    return content
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "NIM key fallback failed on attempt %d: %s",
                        attempt + 1,
                        exc,
                    )
                    continue

            if attempt < 2:
                time.sleep(2)

        raise RuntimeError(f"NIM API failed after key fallback: {last_error}")

    def _parse_response(self, raw: str) -> Tuple[str, float, str]:
        """
        Parse the LLM's JSON response into a structured tuple.

        Strips common formatting artifacts (markdown code fences) before
        attempting JSON parsing.

        Args:
            raw: The raw text from the LLM.

        Returns:
            A tuple of ``(failure_type, confidence, reasoning)``.

        Raises:
            json.JSONDecodeError: If the response cannot be parsed as JSON.
        """
        # Strip markdown code fences and whitespace
        cleaned = raw.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        # Validate required fields with safe defaults
        valid_types = {
            "step_repetition_loop",
            "goal_drift",
            "tool_hallucination",
            "in_context_locking",
            "resource_exhaustion",
            "no_failure",
        }

        failure_type = data.get("failure_type", "no_failure")
        if failure_type not in valid_types:
            logger.warning(
                "Unknown failure_type '%s', defaulting to no_failure",
                failure_type,
            )
            failure_type = "no_failure"

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(confidence, 0.99))  # Clamp to [0, 0.99]

        reasoning = str(data.get("reasoning", "No reasoning provided"))

        return (failure_type, confidence, reasoning)
