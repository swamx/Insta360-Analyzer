"""Stage 5: Encoding - Create final vertical reel."""

import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger


logger = get_logger("stages.stage5_encoding")


class Stage5Encoding(Stage):
    """Encode final 15-second vertical reel."""

    def __init__(self, checkpoint_manager: CheckpointManager):
        super().__init__("stage5_encoding")
        self.checkpoint_manager = checkpoint_manager

    def run(
        self,
        file_id: str,
        source_video: Path,
        reel_plan_checkpoint: Dict[str, Any],
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """Encode final reel using FFmpeg."""
        self._log_stage_start(file_id)

        temp_clips_dir = None

        try:
            source_video = Path(source_video)
            reel_plan = reel_plan_checkpoint.get("reel_plan", {})
            clips = reel_plan.get("clips", [])

            if not clips:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No clips in reel plan",
                )

            logger.info(f"[{file_id}] Encoding {len(clips)} clips")

            # Create temporary directory for clips
            temp_clips_dir = Path("data/working") / f"{file_id}_clips"
            temp_clips_dir.mkdir(parents=True, exist_ok=True)

            # Determine start index for resume
            start_idx = resume_from or 0
            if resume_from is None:
                if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
                    checkpoint = self.checkpoint_manager.load_file_checkpoint(
                        file_id, self.stage_name
                    )
                    start_idx = checkpoint.get("last_encoded_clip", -1) + 1

            extracted_clips = []

            # Extract clips from source video
            for idx in range(start_idx, len(clips)):
                clip_info = clips[idx]
                output_path = temp_clips_dir / f"clip_{idx:03d}.mp4"

                success = self._extract_clip(
                    source_video,
                    output_path,
                    clip_info.get("start_ms", 0) / 1000.0,
                    clip_info.get("end_ms", 0) / 1000.0,
                )

                if success and output_path.exists():
                    extracted_clips.append(str(output_path))
                    logger.info(f"[{file_id}] Extracted clip {idx + 1}/{len(clips)}")

                    # Save progress checkpoint
                    checkpoint_data = {
                        "stage": self.stage_name,
                        "file_id": file_id,
                        "clips_to_encode": len(clips),
                        "clips_encoded": len(extracted_clips),
                        "last_encoded_clip": idx,
                        "extracted_clips": extracted_clips,
                        "status": "IN_PROGRESS",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                    self.checkpoint_manager.save_file_checkpoint(
                        file_id, self.stage_name, checkpoint_data
                    )
                else:
                    logger.warning(f"[{file_id}] Failed to extract clip {idx}")

                self._log_progress(file_id, len(extracted_clips), len(clips))

            if not extracted_clips:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No clips extracted",
                )

            # Create concat file for FFmpeg
            concat_file = Path("data/working") / f"{file_id}_concat.txt"
            with open(concat_file, "w") as f:
                for clip_path in extracted_clips:
                    f.write(f"file '{clip_path}'\n")

            logger.info(f"[{file_id}] Concatenating {len(extracted_clips)} clips")

            # Concatenate and encode to vertical format
            output_reel = Path("data/output") / f"{file_id}_reel.mp4"
            output_reel.parent.mkdir(parents=True, exist_ok=True)

            success = self._concatenate_and_encode(concat_file, output_reel)

            if not success or not output_reel.exists():
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="FFmpeg encoding failed",
                )

            # Verify duration
            duration = self._get_video_duration(output_reel)

            if duration < 0:
                logger.warning(f"[{file_id}] Could not verify output duration")
                duration = reel_plan.get("total_duration", 15.0)

            if duration > 15.5:  # Allow 0.5s tolerance
                logger.warning(
                    f"[{file_id}] Reel duration {duration}s exceeds 15s limit"
                )

            # Get file size
            file_size_mb = output_reel.stat().st_size / (1024**2) if output_reel.exists() else 0

            # Final checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "source_video": str(source_video),
                "clips_to_encode": len(clips),
                "clips_encoded": len(extracted_clips),
                "output_path": str(output_reel),
                "final_duration_seconds": duration,
                "file_size_mb": file_size_mb,
                "status": "ENCODED",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )

            # Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "COMPLETED"
            metadata["output_path"] = checkpoint_data["output_path"]
            metadata["stage_timestamps"]["COMPLETED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Encoded 15s reel: {file_id}_reel.mp4",
                data={
                    "output_path": str(output_reel),
                    "duration": duration,
                    "file_size_mb": file_size_mb,
                },
            )

        except Exception as e:
            logger.exception(f"[{file_id}] Stage 5 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Encoding failed: {str(e)}",
            )

        finally:
            # Cleanup temporary files
            if temp_clips_dir and temp_clips_dir.exists():
                try:
                    shutil.rmtree(temp_clips_dir)
                    logger.debug(f"Cleaned up temporary clips directory")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {str(e)}")

    @staticmethod
    def _extract_clip(
        source_video: Path,
        output_path: Path,
        start_seconds: float,
        end_seconds: float,
    ) -> bool:
        """Extract clip segment from source video using FFmpeg."""
        try:
            duration_s = end_seconds - start_seconds

            cmd = [
                "ffmpeg",
                "-i",
                str(source_video),
                "-ss",
                str(start_seconds),
                "-to",
                str(end_seconds),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",  # Speed for intermediate clips
                "-crf",
                "28",  # Quality for intermediate
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
                "-y",  # Overwrite
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode == 0 and output_path.exists():
                logger.debug(f"Extracted clip: {output_path.name}")
                return True
            else:
                if result.stderr:
                    logger.warning(f"FFmpeg stderr: {result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout extracting clip")
            return False
        except Exception as e:
            logger.warning(f"Clip extraction error: {str(e)}")
            return False

    @staticmethod
    def _concatenate_and_encode(concat_file: Path, output_path: Path) -> bool:
        """Concatenate clips and encode to vertical format using FFmpeg."""
        try:
            # Video filter to scale to 1080×1920 with aspect ratio preservation
            vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",  # Higher quality for final output
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
                "-y",  # Overwrite
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=1200)

            if result.returncode == 0 and output_path.exists():
                logger.info(f"Encoding complete: {output_path.name}")
                return True
            else:
                if result.stderr:
                    logger.error(f"FFmpeg stderr: {result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout during encoding")
            return False
        except Exception as e:
            logger.error(f"Encoding error: {str(e)}")
            return False

    @staticmethod
    def _get_video_duration(video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                try:
                    return float(result.stdout.strip())
                except (ValueError, AttributeError):
                    return -1.0
            else:
                return -1.0

        except Exception as e:
            logger.warning(f"Could not get video duration: {str(e)}")
            return -1.0

    def can_resume(self, file_id: str) -> bool:
        """Check if encoding is complete."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return False

        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        return checkpoint.get("status") == "ENCODED"

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get progress."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=checkpoint.get("clips_to_encode", 0),
                completed_items=checkpoint.get("clips_encoded", 0),
            )
        return None
