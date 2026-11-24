"""Session-end skill distiller.

Reads one session's signals and produces a candidate SKILL.md draft.
The heuristic path works offline (repeated failure clusters become
'avoid' rules; feedback becomes 'prefer/never' rules; emerging needs
become gaps). An optional LLM hook can replace the drafter — pass any
callable taking the signal digest and returning Markdown.

Gates, versioning, and promotion are NOT here. Output goes to
evo-skillopt /train, which decides accept/reject/rollback.
"""
from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable

from .signals import Signal, SignalStore

logger = logging.getLogger(__name__)

_MIN_SIGNALS = 3  # below this a session is anecdote, not pattern


def digest(signals: list[Signal]) -> dict:
    """Deterministic reduction of a session's signals for drafting."""
    kinds = Counter(s.kind for s in signals)
    failures = [s for s in signals if s.kind == "task_failure"]
    feedback = [s for s in signals if s.kind == "user_feedback"]
    needs = [s for s in signals if s.kind == "emerging_need"]
    insights = [s for s in signals if s.kind == "domain_insight"]
    return {
        "n_signals": len(signals),
        "kinds": dict(kinds),
        "failure_rate": round(len(failures) / max(len(signals), 1), 3),
        "failures": [s.detail for s in failures],
        "feedback": [(s.score, s.detail) for s in feedback],
        "emerging_needs": [s.detail for s in needs],
        "insights": [s.detail for s in insights],
    }


def draft_skill(session_id: str, signals: list[Signal], agent: str = "") -> str | None:
    """Heuristic SKILL.md draft. Returns None when the session is too
    thin to distill (circuit breaker against overfitting to noise)."""
    if len(signals) < _MIN_SIGNALS:
        return None
    d = digest(signals)
    name = f"session-{session_id[:8]}"
    lines = [
        "---",
        f"name: {name}",
        (
            f"description: Auto-distilled from session {session_id} "
            f"({d['n_signals']} signals, failure rate {d['failure_rate']}). "
            "Draft — must pass evo-skillopt held-out gate before use."
        ),
        "---",
        "",
        f"# {name}",
        "",
        "Distilled behavioral rules from observed usage. Negative rules first.",
        "",
        "## Avoid (observed failures)",
    ]
    for f in d["failures"][:5]:
        lines.append(f"- {f}")
    if not d["failures"]:
        lines.append("- none observed")
    lines += ["", "## Prefer / Never (user feedback)"]
    for score, detail in sorted(d["feedback"], key=lambda x: x[0] or 0)[:5]:
        verb = "Never" if (score or 0) < 0 else "Prefer"
        lines.append(f"- {verb}: {detail}")
    if not d["feedback"]:
        lines.append("- none recorded")
    lines += ["", "## Reusable facts"]
    for i in d["insights"][:5]:
        lines.append(f"- {i}")
    if not d["insights"]:
        lines.append("- none captured")
    lines += ["", "## Coverage gaps (do not fake capability)"]
    for n in d["emerging_needs"][:5]:
        lines.append(f"- {n}")
    if not d["emerging_needs"]:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def summarize_session(
    store: SignalStore,
    session_id: str,
    llm_hook: Callable[[dict], str] | None = None,
) -> str | None:
    """Produce a candidate SKILL.md for one session, or None if too thin.
    llm_hook receives the digest and must return Markdown; its failure
    falls back to the heuristic draft rather than losing the session."""
    signals = store.for_session(session_id)
    if len(signals) < _MIN_SIGNALS:
        return None
    if llm_hook is not None:
        try:
            return llm_hook(digest(signals))
        except Exception:  # hook is third-party code; any failure falls back
            logger.warning("llm_hook failed; using heuristic draft", exc_info=True)
    return draft_skill(session_id, signals)
