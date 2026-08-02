"""Insta360 video format detection."""

import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger("insta360.detector")


class Insta360Detector:
    """Detect Insta360 video formats and extract metadata."""

    # Insta360 file extensions
    INSTA360_EXTENSIONS = {".insv", ".insp", ".lrv"}

    # Common Insta360 models
    INSTA360_MODELS = {
        "ONE X": "Insta360 ONE X",
        "ONE X2": "Insta360 ONE X2",
        "ONE X3": "Insta360 ONE X3",
        "ONE R": "Insta360 ONE R",
        "PRO": "Insta360 PRO",
        "GO": "Insta360 GO",
        "GO 2": "Insta360 GO 2",
    }

    @staticmethod
    def is_insta360_format(file_path: Path) -> bool:
        """Check if file is Insta360 format by extension."""
        return file_path.suffix.lower() in Insta360Detector.INSTA360_EXTENSIONS

    @staticmethod
    def detect_360_projection(file_path: Path) -> Optional[str]:
        """Detect if video is 360-degree format.

        Returns:
            "equirectangular" if 360°, "perspective" if single-view, None if unknown
        """
        try:
            # Use ffprobe to get video metadata
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)

            if not data.get("streams"):
                return None

            stream = data["streams"][0]
            width = stream.get("width", 0)
            height = stream.get("height", 0)

            # 360° videos typically have 2:1 aspect ratio (equirectangular)
            if width > 0 and height > 0:
                aspect_ratio = width / height

                # Equirectangular projection is roughly 2:1
                if 1.9 < aspect_ratio < 2.1:
                    logger.info(f"Detected equirectangular 360° video ({width}×{height})")
                    return "equirectangular"
                else:
                    logger.info(f"Detected perspective video ({width}×{height}, aspect={aspect_ratio:.2f})")
                    return "perspective"

            return None

        except Exception as e:
            logger.warning(f"Could not detect projection: {str(e)}")
            return None

    @staticmethod
    def get_insta360_metadata(file_path: Path) -> Dict[str, any]:
        """Extract Insta360-specific metadata."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {}

            data = json.loads(result.stdout)

            metadata = {
                "is_insta360": Insta360Detector.is_insta360_format(file_path),
                "projection": Insta360Detector.detect_360_projection(file_path),
                "format": data.get("format", {}).get("format_name", "unknown"),
                "duration": float(data.get("format", {}).get("duration", 0)),
                "bit_rate": int(data.get("format", {}).get("bit_rate", 0)),
            }

            # Extract video stream info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    metadata.update({
                        "width": stream.get("width"),
                        "height": stream.get("height"),
                        "fps": eval(stream.get("r_frame_rate", "30/1")),
                        "codec": stream.get("codec_name"),
                    })
                    break

            # Look for Insta360 tags in metadata
            tags = data.get("format", {}).get("tags", {})
            if tags:
                metadata["camera_make"] = tags.get("make", "unknown")
                metadata["camera_model"] = tags.get("model", "unknown")

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract metadata: {str(e)}")
            return {}

    @staticmethod
    def needs_conversion(file_path: Path) -> bool:
        """Check if file needs 360→single-view conversion."""
        metadata = Insta360Detector.get_insta360_metadata(file_path)
        return metadata.get("projection") == "equirectangular"
