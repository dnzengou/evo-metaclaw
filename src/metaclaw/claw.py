"""The claw — four-axis governance gate on every proposed mutation.

Evolution proposes. The claw decides what is allowed to stay.

A purely fitness-maximising loop will eventually delete the cost cap,
the airgap, or the kill-switch, because constraints cost fitness. The
claw makes that class of edit illegal in advance: every proposed child
is scored on four axes and stamped or rejected BEFORE it ever runs.

Axes (fail one, the child dies):
  B  — Budget:    cost and hours must not jump
  Ci — Circuit:   self-edit recursion depth <= max_depth (default 2)
  E  — Evolution: child fitness >= ratio * parent fitness (default 0.8x)
  Bl — Blacklist: constitutional clauses present in the parent cannot
                  be deleted (airgap, kill-switch, ownership, ...)

Rejections carry their failing axes so attempted escapes are
themselves auditable data. Distinct from evo-skillopt's held-out
Q-gate: that gate answers "is the child better?", the claw answers
"is the child allowed to exist?".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_BLACKLIST = (
    r"airgap",
    r"kill[- ]switch",
    r"budget\s*cap",
    r"ownership",
    r"human\s+oversight",
    r"rate\s*limit",
    r"max_depth",
    r"approval\s*gate",
)


@dataclass
class Mutation:
    """One proposed child, before it runs."""

    parent_md: str
    child_md: str
    parent_fitness: float
    child_fitness: float
    depth: int = 1          # self-edit recursion depth of the child
    cost_delta: float = 0.0  # relative cost change vs parent (0 = no jump)
    hours_delta: float = 0.0  # relative compute-hours change vs parent


@dataclass
class Verdict:
    passed: bool
    failed_axes: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.passed:
            return "PASS (B, Ci, E, Bl)"
        return f"REJECTED ({', '.join(self.failed_axes)})"


def _has_clause(md: str, pattern: str) -> bool:
    return re.search(pattern, md, flags=re.IGNORECASE) is not None


def gate(
    m: Mutation,
    *,
    max_depth: int = 2,
    min_fitness_ratio: float = 0.8,
    budget_tolerance: float = 0.0,
    blacklist: tuple[str, ...] = DEFAULT_BLACKLIST,
) -> Verdict:
    """Score a proposed child on all four axes. Fail one → rejected."""
    failed: list[str] = []
    details: dict = {}

    b_ok = m.cost_delta <= budget_tolerance and m.hours_delta <= budget_tolerance
    details["B"] = {"cost_delta": m.cost_delta, "hours_delta": m.hours_delta,
                    "tolerance": budget_tolerance, "ok": b_ok}
    if not b_ok:
        failed.append("B")

    ci_ok = m.depth <= max_depth
    details["Ci"] = {"depth": m.depth, "max_depth": max_depth, "ok": ci_ok}
    if not ci_ok:
        failed.append("Ci")

    e_floor = min_fitness_ratio * m.parent_fitness
    e_ok = m.child_fitness >= e_floor
    details["E"] = {"child": m.child_fitness, "floor": round(e_floor, 6), "ok": e_ok}
    if not e_ok:
        failed.append("E")

    deleted = [p for p in blacklist
               if _has_clause(m.parent_md, p) and not _has_clause(m.child_md, p)]
    details["Bl"] = {"deleted_clauses": deleted, "ok": not deleted}
    if deleted:
        failed.append("Bl")

    return Verdict(passed=not failed, failed_axes=failed, details=details)
