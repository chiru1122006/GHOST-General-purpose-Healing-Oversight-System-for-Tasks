"""Shared NVIDIA NIM retry helpers for benchmark agents."""

from __future__ import annotations

import os
import time
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def get_nvidia_api_keys() -> List[str]:
    """Return configured NVIDIA keys in fallback order."""
    keys = [
        os.getenv("NVIDIA_API_KEY_1", "").strip() or os.getenv("NVIDIA_API_KEY1", "").strip(),
        os.getenv("NVIDIA_API_KEY_2", "").strip() or os.getenv("NVIDIA_API_KEY2", "").strip(),
    ]

    legacy_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if legacy_key and legacy_key != "your_nvidia_nim_api_key_here":
        keys.append(legacy_key)

    seen = set()
    return [key for key in keys if key and not (key in seen or seen.add(key))]


def build_nvidia_clients(
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.1,
) -> List[ChatOpenAI]:
    """Create one LangChain client per configured NVIDIA API key."""
    return [
        ChatOpenAI(
            model=model,
            openai_api_base=NVIDIA_BASE_URL,
            openai_api_key=key,
            temperature=temperature,
            timeout=30,
        )
        for key in get_nvidia_api_keys()
    ]


def invoke_with_fallback(
    clients: List[ChatOpenAI],
    messages: List[Any],
    max_attempts: int = 3,
) -> str:
    """
    Invoke NVIDIA NIM with key fallback.

    Each attempt tries key 1, then key 2 immediately. If all configured keys
    fail with rate limits, empty content, or transport errors, wait 2 seconds
    before the next attempt.
    """
    if not clients:
        raise RuntimeError("No NVIDIA API keys configured")

    last_error: Optional[BaseException] = None
    for attempt in range(max_attempts):
        for client in clients:
            try:
                content = client.invoke(messages).content
                if not content or not str(content).strip():
                    raise ValueError("NIM API returned empty content")
                return str(content)
            except Exception as exc:
                last_error = exc
                print(f"[GHOST ⚠️] NIM key fallback failed on attempt {attempt + 1}: {exc}")
                continue

        if attempt < max_attempts - 1:
            time.sleep(2)

    raise RuntimeError(f"NIM API failed after key fallback: {last_error}")
