"""
OmniEngine Package Initialization
"""

from .system1 import System1Router
from .system2 import System2Engine
from .memory import OmniMemory
from .planner import AutonomousPlanner
from .tools import OMNI_TOOL_REGISTRY
from . import contracts

__version__ = "2.0.0"
__all__ = [
    "System1Router",
    "System2Engine",
    "OmniMemory",
    "AutonomousPlanner",
    "OMNI_TOOL_REGISTRY",
    "contracts",
]
