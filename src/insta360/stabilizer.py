"""Video stabilization for converted perspective views."""

import subprocess
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("insta360.stabilizer")


class VideoStabilizer:
    """Apply stabilization to video output."""

    @staticmethod
    def stabilize_video(
        input_video: Path,
        output_path: Path,
        smoothness: int = 10,
    ) -> bool:
        """
        Apply video stabilization using FFmpeg vidstab filters.

        Args:
            input_video: Input video
            output_path: Stabilized output video
            smoothness: Smoothness level 1-15 (higher = smoother)

        Returns:
            True if successful
        """
        try:
            logger.info(f"Stabilizing {input_video.name} (smoothness={smoothness})")

            # First pass: detect motion
            detect_cmd = [
                "ffmpeg",
                "-i", str(input_video),
                "-vf", "vidstabdetect=stepsize=32:shakiness=10:accuracy=15",
                "-f", "null",
                "-",
                "-y",
            ]

            logger.debug("Running stabilization detection pass...")
            detect_result = subprocess.run(detect_cmd, capture_output=True, timeout=600)

            if detect_result.returncode != 0:
                logger.warning("Motion detection failed, skipping stabilization")
                return False

            # Second pass: apply stabilization
            transform_cmd = [
                "ffmpeg",
                "-i", str(input_video),
                "-vf", f"vidstabtransform=smoothing={smoothness}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                str(output_path),
                "-y",
            ]

            logger.debug("Running stabilization transform pass...")
            transform_result = subprocess.run(transform_cmd, capture_output=True, timeout=1200)

            if transform_result.returncode == 0:
                logger.info(f"Stabilization successful: {output_path.name}")
                return True
            else:
                logger.error(f"Stabilization failed: {transform_result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Stabilization timeout")
            return False
        except Exception as e:
            logger.error(f"Stabilization error: {str(e)}")
            return False

    @staticmethod
    def apply_gimbal_effect(
        input_video: Path,
        output_path: Path,
    ) -> bool:
        """
        Apply gimbal-like smoothing effect (simulates professional gimbal).

        Uses smooth motion interpolation to create professional camera feel.

        Args:
            input_video: Input video
            output_path: Output with gimbal effect

        Returns:
            True if successful
        """
        try:
            logger.info(f"Applying gimbal effect to {input_video.name}")

            # Use slow frame rate interpolation for smooth motion
            cmd = [
                "ffmpeg",
                "-i", str(input_video),
                "-vf", "minterpolate=mi_mode=mci:mc_mode=aobmc:vsbmc=1",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                str(output_path),
                "-y",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=1200)

            if result.returncode == 0:
                logger.info(f"Gimbal effect applied: {output_path.name}")
                return True
            else:
                logger.warning("Gimbal effect failed, proceeding without it")
                return False

        except Exception as e:
            logger.warning(f"Gimbal effect error: {str(e)}")
            return False
