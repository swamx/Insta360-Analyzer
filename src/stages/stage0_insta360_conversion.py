"""Stage 0.5: Insta360 360° to Single-Perspective Conversion."""

import json
from pathlib import Path
from typing import Optional, Dict
from src.utils.logger import get_logger
from src.insta360 import Insta360Detector, Insta360Converter

logger = get_logger("stage0_insta360_conversion")


class Stage0Insta360Conversion:
    """Convert 360° Insta360 videos to single-perspective view."""

    STAGE_NAME = "stage0_insta360_conversion"

    def __init__(self, video_path: Path, working_dir: Path):
        """
        Initialize Insta360 conversion stage.

        Args:
            video_path: Input video file (may be .insv 360° or already converted)
            working_dir: Working directory for checkpoints and temp files
        """
        self.video_path = Path(video_path)
        self.working_dir = Path(working_dir)
        self.output_path = None
        self.checkpoint_dir = self.working_dir / self.STAGE_NAME
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict:
        """
        Run Insta360 conversion stage.

        Returns:
            {
                "output_video": Path to converted or original video,
                "was_360": bool - whether input was 360° format,
                "conversion_applied": bool - whether conversion was performed,
                "metadata": Insta360 metadata if applicable
            }
        """
        try:
            logger.info(f"Stage 0.5: Insta360 Conversion - Processing {self.video_path.name}")

            # Load checkpoint if exists
            checkpoint = self._load_checkpoint()
            if checkpoint:
                logger.info("Loading from checkpoint")
                return checkpoint

            # Check if video is Insta360 format
            is_insta360 = Insta360Detector.is_insta360_format(self.video_path)

            if not is_insta360:
                logger.info(f"{self.video_path.name} is not Insta360 format, passing through")
                return self._save_checkpoint({
                    "output_video": str(self.video_path),
                    "was_360": False,
                    "conversion_applied": False,
                    "metadata": {}
                })

            # Extract metadata
            metadata = Insta360Detector.get_insta360_metadata(self.video_path)
            logger.info(f"Insta360 metadata: {json.dumps(metadata, indent=2)}")

            # Check if conversion needed
            if not Insta360Detector.needs_conversion(self.video_path):
                logger.info("Video is already in single-perspective view")
                return self._save_checkpoint({
                    "output_video": str(self.video_path),
                    "was_360": False,
                    "conversion_applied": False,
                    "metadata": metadata
                })

            # Convert 360° to single-perspective
            logger.info("Converting 360° to single-perspective view...")
            self.output_path = self._get_output_path()

            converter = Insta360Converter()
            success = converter.extract_best_perspective(
                self.video_path,
                self.output_path,
                detection_enabled=True,
            )

            if not success:
                raise RuntimeError("360° conversion failed")

            if not self.output_path.exists():
                raise RuntimeError(f"Output file not created: {self.output_path}")

            logger.info(f"Conversion successful: {self.output_path.name}")
            logger.info(f"Output size: {self.output_path.stat().st_size / (1024*1024):.2f}MB")

            result = {
                "output_video": str(self.output_path),
                "was_360": True,
                "conversion_applied": True,
                "metadata": metadata
            }

            return self._save_checkpoint(result)

        except Exception as e:
            logger.error(f"Stage 0.5 failed: {str(e)}")
            raise

    def _get_output_path(self) -> Path:
        """Get output path for converted video."""
        stem = self.video_path.stem
        return self.working_dir / f"{stem}_converted.mp4"

    def _load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint if exists."""
        checkpoint_file = self.checkpoint_dir / "checkpoint.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)

            # Verify output file exists
            output_video = Path(checkpoint.get("output_video"))
            if output_video.exists():
                logger.info("Checkpoint loaded successfully")
                return checkpoint

            logger.warning("Checkpoint output file missing, restarting...")
            return None

        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {str(e)}")
            return None

    def _save_checkpoint(self, result: Dict) -> Dict:
        """Save checkpoint and return result."""
        checkpoint_file = self.checkpoint_dir / "checkpoint.json"

        try:
            with open(checkpoint_file, "w") as f:
                json.dump(result, f, indent=2)

            logger.info(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {str(e)}")

        return result
