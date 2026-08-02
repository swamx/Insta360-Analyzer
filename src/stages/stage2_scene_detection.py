"""Stage 2: Scene Detection using PySceneDetect."""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from PIL import Image
import json
import logging as stdlib_logging

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger

try:
    from scenedetect import detect, AdaptiveDetector, ContentDetector
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False

logger = get_logger("stages.stage2_scene_detection")


class Stage2SceneDetection(Stage):
    """Detect scene boundaries and extract key frames."""

    def __init__(self, checkpoint_manager: CheckpointManager, threshold: float = 27.0):
        super().__init__("stage2_scene_detection")
        self.checkpoint_manager = checkpoint_manager
        self.threshold = threshold  # Scene detection sensitivity

    def run(
        self,
        file_id: str,
        video_path: Path,
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """Detect scenes and extract key frames."""
        self._log_stage_start(file_id)

        try:
            video_path = Path(video_path)

            if not video_path.exists():
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message=f"Video file not found: {video_path}",
                )

            # 1. Detect scenes
            scenes = self._detect_scenes(video_path)

            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scenes detected",
                )

            logger.info(f"[{file_id}] Detected {len(scenes)} scenes")

            # 2. Extract key frame from each scene
            scene_data = []
            for idx, (start_frame, start_time, end_frame, end_time) in enumerate(scenes):
                key_frame_path = self._extract_key_frame(
                    video_path,
                    start_time,
                    end_time,
                    file_id,
                    idx,
                )

                if key_frame_path:
                    scene_data.append({
                        "scene_id": f"{file_id}_scene_{idx:03d}",
                        "scene_idx": idx,
                        "start_frame": int(start_frame),
                        "end_frame": int(end_frame),
                        "start_time_ms": int(start_time * 1000),
                        "end_time_ms": int(end_time * 1000),
                        "duration_seconds": float(end_time - start_time),
                        "key_frame_path": str(key_frame_path),
                    })

                self._log_progress(file_id, idx + 1, len(scenes))

            if not scene_data:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="Failed to extract key frames",
                )

            # 3. Save checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "total_scenes": len(scene_data),
                "scenes": scene_data,
                "threshold": self.threshold,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )

            # 4. Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "SCENES_DETECTED"
            metadata["scene_count"] = len(scene_data)
            metadata["stage_timestamps"]["SCENES_DETECTED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Detected {len(scene_data)} scenes",
                data={"scene_count": len(scene_data)},
            )

        except Exception as e:
            logger.exception(f"[{file_id}] Stage 2 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Scene detection failed: {str(e)}",
            )

    def _detect_scenes(self, video_path: Path) -> List[tuple]:
        """Detect scene boundaries using PySceneDetect or fallback."""
        try:
            if SCENEDETECT_AVAILABLE:
                return self._detect_scenes_with_pyscenedetect(video_path)
            else:
                logger.warning("PySceneDetect not available, using fallback detection")
                return self._detect_scenes_fallback(video_path)

        except Exception as e:
            logger.error(f"Scene detection failed: {str(e)}, using fallback")
            return self._detect_scenes_fallback(video_path)

    def _detect_scenes_with_pyscenedetect(self, video_path: Path) -> List[tuple]:
        """Detect scenes using PySceneDetect library."""
        try:
            # Suppress PySceneDetect's own logging
            psd_logger = stdlib_logging.getLogger("scenedetect")
            psd_logger.setLevel(stdlib_logging.WARNING)

            logger.info(f"Detecting scenes with PySceneDetect (threshold={self.threshold})")

            # Try adaptive detector first (more accurate for varied content)
            try:
                scenes = detect(str(video_path), AdaptiveDetector())
                if len(scenes) >= 2:
                    logger.info(f"Adaptive detector found {len(scenes)} scenes")
                    return self._convert_pyscenedetect_output(video_path, scenes)
            except Exception as e:
                logger.warning(f"Adaptive detector failed: {str(e)}")

            # Fallback to content detector
            logger.info("Trying content detector")
            scenes = detect(str(video_path), ContentDetector(threshold=self.threshold))

            if len(scenes) >= 1:
                logger.info(f"Content detector found {len(scenes)} scenes")
                return self._convert_pyscenedetect_output(video_path, scenes)
            else:
                logger.warning("No scenes detected with PySceneDetect")
                return self._detect_scenes_fallback(video_path)

        except Exception as e:
            logger.error(f"PySceneDetect error: {str(e)}")
            return self._detect_scenes_fallback(video_path)

    @staticmethod
    def _convert_pyscenedetect_output(video_path: Path, scenes: List) -> List[tuple]:
        """Convert PySceneDetect output to internal format."""
        result = []

        for i, scene in enumerate(scenes):
            # PySceneDetect returns (start_time, end_time) in seconds
            start_time = float(scene[0].get_seconds())
            end_time = float(scene[1].get_seconds()) if i < len(scenes) - 1 else Stage2SceneDetection._get_video_duration(video_path)

            # Estimate frame numbers at 30fps
            start_frame = int(start_time * 30)
            end_frame = int(end_time * 30)

            result.append((start_frame, start_time, end_frame, end_time))

        return result

    def _detect_scenes_fallback(self, video_path: Path) -> List[tuple]:
        """Fallback scene detection: split by fixed duration or estimate from file size."""
        try:
            duration = self._get_video_duration(video_path)

            # If duration detection fails, estimate from file size
            if duration <= 0:
                try:
                    file_size_gb = video_path.stat().st_size / (1024**3)
                    # Rough estimate: Insta360 videos ~200MB per minute at 4K
                    # So 1GB ≈ 5 minutes
                    estimated_duration = file_size_gb * 300  # seconds
                    logger.warning(f"Estimated video duration from file size: {estimated_duration:.1f}s ({estimated_duration/60:.1f} minutes)")
                    duration = estimated_duration
                except Exception as e:
                    logger.warning(f"Could not estimate duration: {str(e)}")
                    # Default to 10 minute video if all else fails
                    duration = 600
                    logger.info(f"Using default 10-minute duration estimate")

            scenes = []
            chunk_duration = 5.0  # 5-second chunks
            scene_count = int(duration / chunk_duration) + 1

            for i in range(scene_count):
                start_time = i * chunk_duration
                end_time = min((i + 1) * chunk_duration, duration)

                if start_time < duration:
                    scenes.append((
                        int(start_time * 30),
                        start_time,
                        int(end_time * 30),
                        end_time,
                    ))

            logger.debug(f"Fallback: created {len(scenes)} scenes from video")
            return scenes

        except Exception as e:
            logger.error(f"Fallback scene detection failed: {str(e)}")
            return []

    def _extract_key_frame(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        file_id: str,
        scene_idx: int,
    ) -> Optional[Path]:
        """Extract middle frame of scene as key frame."""
        try:
            # Extract frame at midpoint of scene
            mid_time = (start_time + end_time) / 2.0

            output_dir = Path("data/working/scenes")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{file_id}_scene_{scene_idx:03d}_keyframe.jpg"

            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-ss", str(mid_time),
                "-vframes", "1",
                "-q:v", "2",
                str(output_path),
                "-hide_banner",
                "-loglevel", "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.warning(f"Failed to extract frame at {mid_time}s")
                return None

        except Exception as e:
            logger.warning(f"Frame extraction error: {str(e)}")
            return None

    @staticmethod
    def _get_video_duration(video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            try:
                return float(result.stdout.strip())
            except (ValueError, AttributeError):
                return 0.0

        except Exception as e:
            logger.error(f"Could not get video duration: {str(e)}")
            return 0.0

    def can_resume(self, file_id: str) -> bool:
        """Scene detection is not resumable (always re-run)."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get progress info."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=checkpoint.get("total_scenes", 0),
                completed_items=checkpoint.get("total_scenes", 0),
            )
        return None
