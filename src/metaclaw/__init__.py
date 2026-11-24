"""evo-metaclaw — live conversation-driven meta-learning.

Capture signals from agent conversations, distill session-end skill
candidates, and emit them in evo-skillopt /train format. Gates and
promotion live in evo-skillopt; deployment lives in EvoForge. This
package does one thing: turn conversations into clean training signal.
"""

__version__ = "0.1.0"

from .signals import SIGNAL_KINDS, Signal, SignalStore

__all__ = ["SIGNAL_KINDS", "Signal", "SignalStore", "__version__"]
