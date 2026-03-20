"""Локальные навыки без внешнего LLM: математика, время, погода."""

from .local_skills import run_skill_math, run_skill_time, run_skill_weather

__all__ = ["run_skill_math", "run_skill_time", "run_skill_weather"]
