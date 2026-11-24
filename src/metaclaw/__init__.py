"""evo-metaclaw — the lock on self-evolving AI agents.

Governance + learning in one layer: the claw gate decides what may
change (four axes, before a mutation ever runs); signal capture and
session summarization decide when learning runs. Training and rollout
gates live in evo-skillopt; deployment lives in EvoForge.
"""

__version__ = "0.2.0"

from .claw import Mutation, Verdict, gate
from .signals import SIGNAL_KINDS, Signal, SignalStore

__all__ = [
    "SIGNAL_KINDS",
    "Mutation",
    "Signal",
    "SignalStore",
    "Verdict",
    "__version__",
    "gate",
]
