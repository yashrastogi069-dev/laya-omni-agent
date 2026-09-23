"""
omni_engine.skills
==================
First-class Skills Substrate for the standalone LAYA Omni Agent.
"""

from .registry import SkillRegistry
from .definitions import (
    CANONICAL_SKILLS,
    build_canonical_skill_registry,
)

__all__ = [
    "SkillRegistry",
    "CANONICAL_SKILLS",
    "build_canonical_skill_registry",
]
