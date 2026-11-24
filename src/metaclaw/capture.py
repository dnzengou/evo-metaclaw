"""Exchange recorder — the conversation proxy's write path.

Wrap any agent call with `record_exchange`; it classifies the outcome
and writes the right signals. Classification is deliberately dumb and
deterministic: explicit errors and empty replies are failures,
everything else is success. Nuance belongs to the user-feedback
channel, not to heuristics guessing at quality.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .signals import Signal, SignalStore

_ERROR_MARKERS = ("traceback", "exception", "error:", "i can't", "i cannot", "unable to")


def classify(response: str, error: Exception | None = None) -> tuple[str, float]:
    """Return (kind, score) for an exchange outcome."""
    if error is not None:
        return "task_failure", -1.0
    text = (response or "").strip().lower()
    if not text:
        return "task_failure", -0.5
    if any(m in text for m in _ERROR_MARKERS):
        return "task_failure", -0.5
    return "task_success", 0.5


def record_exchange(
    store: SignalStore,
    session_id: str,
    agent: str,
    prompt: str,
    response: str | None,
    latency_s: float,
    error: Exception | None = None,
) -> Signal:
    """Classify one prompt/response pair and store the outcome signal."""
    kind, score = classify(response or "", error)
    detail = response if error is None else f"{type(error).__name__}: {error}"
    return store.add(Signal(
        kind=kind, session_id=session_id, agent=agent,
        detail=f"[{latency_s:.2f}s] {detail[:500]}",
        score=score,
    ))


def record_feedback(
    store: SignalStore,
    session_id: str,
    agent: str,
    detail: str,
    score: float,
) -> Signal:
    """Explicit user feedback — the highest-value signal kind."""
    return store.add(Signal(
        kind="user_feedback", session_id=session_id, agent=agent,
        detail=detail[:500], score=score,
    ))


def wrap_agent(
    store: SignalStore,
    session_id: str,
    agent: str,
    fn: Callable[[str], Any],
) -> Callable[[str], Any]:
    """Wrap an agent callable so every call is captured. The wrapped
    function's exceptions are recorded as failures, then re-raised —
    capture never swallows errors."""
    import time

    def wrapped(prompt: str) -> Any:
        t0 = time.monotonic()
        try:
            out = fn(prompt)
        except Exception as exc:
            record_exchange(store, session_id, agent, prompt, None,
                            time.monotonic() - t0, error=exc)
            raise
        record_exchange(store, session_id, agent, prompt, str(out),
                        time.monotonic() - t0)
        return out

    return wrapped
