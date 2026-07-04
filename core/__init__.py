"""
GHOST Core — Public API surface.

All primary classes and the decorator are re-exported here for
convenient importing::

    from core import GHOSTCallbackHandler, ghost_monitor
    from core import TrajectoryTracker, FailureClassifier
    from core import RecoveryEngine, FailureMemory
"""

from .classifier import FailureClassifier
from .interceptor import GHOSTCallbackHandler, ghost_monitor
from .memory import FailureMemory
from .recovery import RecoveryEngine
from .trajectory import TrajectoryTracker

__all__ = [
    "GHOSTCallbackHandler",
    "ghost_monitor",
    "TrajectoryTracker",
    "FailureClassifier",
    "RecoveryEngine",
    "FailureMemory",
]
