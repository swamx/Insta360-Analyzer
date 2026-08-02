"""Stage 2: Frame Extraction & Preparation - extract frames from video."""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger


logger = get_logger("stages.stage2_extraction")


class Stage2Extraction(Stage):
    """Extract frames from video at regular intervals."""

    def __init__(self, checkpoint_manager: CheckpointManager, frame_interval: float = 2.0):
        super().__init__("stage2_extraction")
        self.checkpoint_manager = checkpoint_manager
        self.frame_interval = frame_interval  # Extract frame every N seconds

    def run(
        self,
        file_id: str,
        input_path: Path,
        output_dir: Path,
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """
        Extract frames from video.

        Args:
            file_id: Unique identifier for this file
            input_path: Path to input video
            output_dir: Directory to save extracted frames
            resume_from: Ignored for frame extraction (always re-extracts)

        Returns:
            StageResult with frame extraction info
        """
        self._log_stage_start(file_id)

        try:
            input_path = Path(input_path)
            output_dir = Path(output_dir) / file_id / "frames"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Use FFmpeg to extract frames
            frame_pattern = str(output_dir / "frame_%06d.jpg")

            # FFmpeg command: extract frames every N seconds
            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-vf", f"fps=1/{self.frame_interval}",
                "-q:v", "2",  # Quality (1-31, lower is better)
                frame_pattern,
                "-hide_banner",
                "-loglevel", "error",
            ]

            logger.info(f"[{file_id}] Extracting frames with interval {self.frame_interval}s")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode != 0:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message=f"FFmpeg failed: {result.stderr}",
                )

            # Count extracted frames
            frames = sorted(output_dir.glob("frame_*.jpg"))
            frame_count = len(frames)

            if frame_count == 0:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No frames extracted",
                )

            # Save extraction checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "output_dir": str(output_dir),
                "frame_count": frame_count,
                "frame_interval_seconds": self.frame_interval,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )

            # Update file metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "FRAMES_EXTRACTED"
            metadata["frame_count"] = frame_count
            metadata["stage_timestamps"]["FRAMES_EXTRACTED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Extracted {frame_count} frames",
                data={
                    "frame_count": frame_count,
                    "output_dir": str(output_dir),
                },
            )

        except subprocess.TimeoutExpired:
            logger.error(f"[{file_id}] Frame extraction timed out")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message="Frame extraction timed out",
            )
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 2 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Extraction failed: {str(e)}",
            )

    def can_resume(self, file_id: str) -> bool:
        """Frame extraction cannot resume mid-process (full re-extraction)."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get extraction progress."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id,
                self.stage_name,
            )
            frame_count = checkpoint.get("frame_count", 0)
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=frame_count,
                completed_items=frame_count,
            )
        return None
