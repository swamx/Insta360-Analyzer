"""Pipeline stages."""

from src.stages.base import Stage, StageResult, ProgressInfo
from src.stages.stage1_discovery import Stage1Discovery
from src.stages.stage2_extraction import Stage2Extraction

__all__ = [
    "Stage",
    "StageResult",
    "ProgressInfo",
    "Stage1Discovery",
    "Stage2Extraction",
]
