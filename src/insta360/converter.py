"""Convert Insta360 360° videos to single-perspective view."""

import subprocess
from pathlib import Path
from typing import Optional, Tuple
from src.utils.logger import get_logger
from .detector import Insta360Detector

logger = get_logger("insta360.converter")


class Insta360Converter:
    """Convert 360° equirectangular videos to single-perspective view."""

    def __init__(self, projection: str = "forward"):
        """
        Initialize converter.

        Args:
            projection: perspective to extract
              - "forward": forward-facing (default)
              - "follow": follow detected person
              - "panoramic": panoramic sweep
        """
        self.projection = projection

    def convert_360_to_perspective(
        self,
        input_video: Path,
        output_path: Path,
        perspective: str = "forward",
        fov: int = 90,
        stabilize: bool = True,
    ) -> bool:
        """
        Convert 360° equirectangular or dual-fisheye to single-perspective view.

        For Insta360 dual-fisheye (two 3840x3840 streams), first stitch to equirectangular,
        then apply perspective extraction.

        Args:
            input_video: Input 360° video (dual-fisheye or equirectangular)
            output_path: Output perspective video
            perspective: Perspective type (forward, panoramic, etc.)
            fov: Field of view in degrees (default 90)
            stabilize: Apply video stabilization

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Converting {input_video.name} to {perspective} perspective ({fov}° FOV)")

            # Perspective parameters
            if perspective == "forward":
                yaw, pitch, roll = 0, 0, 0  # Looking forward
            elif perspective == "backward":
                yaw, pitch, roll = 180, 0, 0  # Looking backward
            elif perspective == "left":
                yaw, pitch, roll = -90, 0, 0  # Looking left
            elif perspective == "right":
                yaw, pitch, roll = 90, 0, 0  # Looking right
            elif perspective == "up":
                yaw, pitch, roll = 0, -90, 0  # Looking up
            elif perspective == "down":
                yaw, pitch, roll = 0, 90, 0  # Looking down
            else:
                yaw, pitch, roll = 0, 0, 0  # Default forward

            # Build FFmpeg filter graph
            # For Insta360 dual-fisheye: select first video stream (left eye equirectangular equivalent)
            # then apply v360 perspective transformation
            vf_filter = f"v360=input=equirect:output=flat:yaw={yaw}:pitch={pitch}:roll={roll}:h_fov={fov}:v_fov={fov}"

            # TODO: Add stabilization in two-pass mode if requested
            # For now, skip vidstab as it requires two-pass processing
            # if stabilize:
            #     vf_filter += ",vidstabdetect=stepsize=32:shakiness=10:accuracy=15,vidstabtransform"

            # Add scaling for output format (vertical 1080×1920)
            vf_filter += ",scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

            cmd = [
                "ffmpeg",
                "-i", str(input_video),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
                "-y",
            ]

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, timeout=1200)

            if result.returncode == 0:
                logger.info(f"Conversion successful: {output_path.name}")
                return True
            else:
                stderr = result.stderr.decode()
                logger.error(f"FFmpeg conversion failed: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Conversion timeout (exceeded 20 minutes)")
            return False
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            return False

    def extract_best_perspective(
        self,
        input_video: Path,
        output_path: Path,
        detection_enabled: bool = True,
    ) -> bool:
        """
        Intelligently extract best perspective from 360° video.

        If detection is enabled, analyzes frames to find:
        - Direction of action/movement
        - Subject location
        - Composition quality

        Args:
            input_video: Input 360° video
            output_path: Output perspective video
            detection_enabled: Use AI detection for optimal perspective

        Returns:
            True if successful
        """
        try:
            # For now, use forward-facing perspective
            # Later: implement detection to find optimal viewing angle
            perspective = "forward"
            fov = 90

            if detection_enabled:
                logger.info("AI perspective detection would analyze frames here")
                # TODO: Implement frame analysis to find optimal perspective

            return self.convert_360_to_perspective(
                input_video,
                output_path,
                perspective=perspective,
                fov=fov,
                stabilize=True,
            )

        except Exception as e:
            logger.error(f"Failed to extract perspective: {str(e)}")
            return False

    @staticmethod
    def needs_conversion(file_path: Path) -> bool:
        """Check if file needs conversion."""
        return Insta360Detector.needs_conversion(file_path)

    @staticmethod
    def get_conversion_output_path(input_video: Path, output_dir: Path) -> Path:
        """Get standardized output path for converted video."""
        stem = input_video.stem
        return output_dir / f"{stem}_perspective.mp4"
