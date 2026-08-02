"""Stage 1: Discovery & Cataloging - scan and catalog input media."""

from pathlib import Path
from datetime import datetime
from typing import Optional

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger


logger = get_logger("stages.stage1_discovery")


class Stage1Discovery(Stage):
    """Discover and catalog input files."""

    def __init__(self, checkpoint_manager: CheckpointManager):
        super().__init__("stage1_discovery")
        self.checkpoint_manager = checkpoint_manager

    def run(
        self,
        file_id: str,
        input_path: Path,
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """
        Catalog input file metadata.

        Args:
            file_id: Unique identifier for this file
            input_path: Path to input video/image file
            resume_from: Ignored for discovery stage (always runs)

        Returns:
            StageResult with catalog data
        """
        self._log_stage_start(file_id)

        try:
            input_path = Path(input_path)

            # Verify input exists
            if not input_path.exists():
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message=f"Input file not found: {input_path}",
                )

            # Extract basic metadata
            file_stat = input_path.stat()
            catalog = {
                "file_id": file_id,
                "source_path": str(input_path),
                "file_size_bytes": file_stat.st_size,
                "file_size_gb": file_stat.st_size / (1024 ** 3),
                "file_type": self._detect_file_type(input_path),
                "ingest_timestamp": datetime.utcnow().isoformat() + "Z",
            }

            # For videos, try to get duration and resolution
            if catalog["file_type"] == "video":
                import subprocess
                try:
                    result = subprocess.run(
                        [
                            "ffprobe",
                            "-v", "error",
                            "-show_entries", "format=duration,width,height",
                            "-of", "default=noprint_wrappers=1",
                            str(input_path),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split("\n"):
                            if "=" in line:
                                key, val = line.split("=", 1)
                                if key == "duration":
                                    catalog["duration_seconds"] = float(val)
                except Exception as e:
                    logger.warning(
                        f"Could not extract video metadata from ffprobe: {str(e)}"
                    )

            # Save catalog checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "catalog": catalog,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )

            # Save file metadata
            file_metadata = {
                "file_id": file_id,
                "source_path": str(input_path),
                "state": "DISCOVERED",
                "stage_timestamps": {
                    "DISCOVERED": datetime.utcnow().isoformat() + "Z",
                },
                **catalog,
            }
            self.checkpoint_manager.save_file_metadata(file_id, file_metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Cataloged {catalog['file_type']}: {catalog['file_size_gb']:.2f}GB",
                data=catalog,
            )

        except Exception as e:
            logger.exception(f"[{file_id}] Stage 1 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Discovery failed: {str(e)}",
            )

    def can_resume(self, file_id: str) -> bool:
        """Discovery is not resumable (always re-runs)."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Discovery has no progress tracking (single-step stage)."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=1,
                completed_items=1,
            )
        return None

    @staticmethod
    def _detect_file_type(path: Path) -> str:
        """Detect file type from extension."""
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

        suffix = path.suffix.lower()

        if suffix in video_exts:
            return "video"
        elif suffix in image_exts:
            return "image"
        else:
            return "unknown"
