"""Pipeline stages."""

from src.stages.base import Stage, StageResult, ProgressInfo
from src.stages.stage1_discovery import Stage1Discovery
from src.stages.stage2_scene_detection import Stage2SceneDetection
from src.stages.stage3_vision_editor import Stage3VisionEditor
from src.stages.stage4_reel_assembly import Stage4ReelAssembly
from src.stages.stage5_encoding import Stage5Encoding

__all__ = [
    "Stage",
    "StageResult",
    "ProgressInfo",
    "Stage1Discovery",
    "Stage2SceneDetection",
    "Stage3VisionEditor",
    "Stage4ReelAssembly",
    "Stage5Encoding",
]
