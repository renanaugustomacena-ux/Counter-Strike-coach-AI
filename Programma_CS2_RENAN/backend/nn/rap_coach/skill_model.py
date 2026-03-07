# DEPRECATED: Use Programma_CS2_RENAN.backend.processing.skill_assessment
# This shim exists for backward compatibility during P9 transition.
# SkillAxes and SkillLatentModel are production utilities, not RAP-specific.
from Programma_CS2_RENAN.backend.processing.skill_assessment import (  # noqa: F401
    SkillAxes,
    SkillLatentModel,
)

__all__ = ["SkillAxes", "SkillLatentModel"]
