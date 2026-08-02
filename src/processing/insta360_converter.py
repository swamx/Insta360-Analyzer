"""Insta360 format detection and stitching integration."""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.utils.errors import InvalidInputError


logger = get_logger("insta360_converter")


INSTA360_EXTENSIONS = {".insv", ".insp", ".lrv"}


@dataclass
class StitchTool:
    """Represents an available Insta360 stitching tool."""

    name: str
    path: Path
    version: Optional[str] = None
    available: bool = False
    test_cmd: list = None


class Insta360ToolDetector:
    """Detect available Insta360 stitching tools."""

    # Known Insta360 Studio installation paths (Windows)
    STUDIO_PATHS_WINDOWS = [
        Path("C:\\Program Files\\Insta360\\Insta360Studio"),
        Path("C:\\Program Files (x86)\\Insta360\\Insta360Studio"),
        Path(
            "C:\\Users"
        )  # Search user's AppData
        / "AppData"
        / "Local"
        / "Insta360",
    ]

    # Known Insta360 Studio paths (Mac)
    STUDIO_PATHS_MAC = [
        Path("/Applications/Insta360Studio.app/Contents/MacOS"),
        Path("/opt/insta360/studio"),
    ]

    # OneX API executable paths
    ONEX_PATHS = [
        Path("C:\\Program Files\\Insta360\\OneX"),
        Path("C:\\Program Files (x86)\\Insta360\\OneX"),
    ]

    def __init__(self):
        self.detected_tools: Dict[str, StitchTool] = {}
        self.system = sys.platform

    def detect_all(self) -> Dict[str, StitchTool]:
        """Detect all available Insta360 tools."""
        self._detect_studio()
        self._detect_onex_api()
        self._detect_ffmpeg_plugins()

        logger.info(f"Detected {len(self.detected_tools)} Insta360 tool(s)")
        for name, tool in self.detected_tools.items():
            logger.info(f"  ✓ {name}: {tool.path}")

        return self.detected_tools

    def _detect_studio(self) -> None:
        """Detect Insta360 Studio installation."""
        paths = (
            self.STUDIO_PATHS_WINDOWS
            if self.system == "win32"
            else self.STUDIO_PATHS_MAC
        )

        for path in paths:
            if not path.exists():
                continue

            # Look for executable
            exe_name = "Insta360Studio.exe" if self.system == "win32" else "Insta360Studio"
            exe_path = path / exe_name if path.is_dir() else path

            if exe_path.exists():
                tool = StitchTool(
                    name="Insta360Studio",
                    path=exe_path,
                    available=True,
                )
                self._get_version(tool)
                self.detected_tools["studio"] = tool
                logger.debug(f"Found Insta360 Studio: {exe_path}")
                return

    def _detect_onex_api(self) -> None:
        """Detect Insta360 OneX API."""
        paths = self.ONEX_PATHS if self.system == "win32" else []

        for path in paths:
            if not path.exists():
                continue

            exe_path = path / "Insta360OneX.exe"
            if exe_path.exists():
                tool = StitchTool(
                    name="Insta360OneX",
                    path=exe_path,
                    available=True,
                )
                self.detected_tools["onex"] = tool
                logger.debug(f"Found Insta360 OneX API: {exe_path}")
                return

    def _detect_ffmpeg_plugins(self) -> None:
        """Detect FFmpeg with Insta360 support."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-h", "filter=insta360"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                tool = StitchTool(
                    name="FFmpeg (insta360 filter)",
                    path=Path("ffmpeg"),
                    available=True,
                )
                self.detected_tools["ffmpeg_insta360"] = tool
                logger.debug("Found FFmpeg with Insta360 filter")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _get_version(self, tool: StitchTool) -> None:
        """Try to get tool version."""
        try:
            result = subprocess.run(
                [str(tool.path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                tool.version = result.stdout.split("\n")[0]
        except Exception:
            pass

    def get_recommended_tool(self) -> Optional[StitchTool]:
        """Get the best available tool (in order of preference)."""
        preference_order = ["studio", "onex", "ffmpeg_insta360"]
        for key in preference_order:
            if key in self.detected_tools:
                return self.detected_tools[key]
        return None


class Insta360Converter:
    """Convert Insta360 formats to standard video."""

    def __init__(self):
        self.detector = Insta360ToolDetector()
        self.available_tools = self.detector.detect_all()
        self.preferred_tool = self.detector.get_recommended_tool()

    def is_insta360_format(self, file_path: Path) -> bool:
        """Check if file is Insta360 format."""
        return Path(file_path).suffix.lower() in INSTA360_EXTENSIONS

    def can_convert(self, file_path: Path) -> bool:
        """Check if we can convert this file."""
        return self.is_insta360_format(file_path) and self.preferred_tool is not None

    def convert_to_mp4(
        self,
        input_path: Path,
        output_path: Path,
        stitch_tool: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Convert Insta360 format to standard MP4.

        Args:
            input_path: Path to .insv/.insp file
            output_path: Path to save converted MP4
            stitch_tool: Specific tool to use ("studio", "onex", "ffmpeg"), or None for auto

        Returns:
            (success, message)
        """
        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        if not self.is_insta360_format(input_path):
            return False, f"Not an Insta360 format: {input_path}"

        # Select tool
        if stitch_tool and stitch_tool in self.available_tools:
            tool = self.available_tools[stitch_tool]
        elif self.preferred_tool:
            tool = self.preferred_tool
        else:
            return False, "No Insta360 stitching tool available"

        logger.info(
            f"Converting {input_path.name} using {tool.name} → {output_path.name}"
        )

        try:
            if tool.name == "Insta360Studio":
                return self._convert_with_studio(input_path, output_path, tool)
            elif tool.name == "Insta360OneX":
                return self._convert_with_onex(input_path, output_path, tool)
            elif "FFmpeg" in tool.name:
                return self._convert_with_ffmpeg(input_path, output_path)
            else:
                return False, f"Unknown tool: {tool.name}"

        except Exception as e:
            logger.exception(f"Conversion failed: {str(e)}")
            return False, f"Conversion error: {str(e)}"

    def _convert_with_studio(
        self,
        input_path: Path,
        output_path: Path,
        tool: StitchTool,
    ) -> Tuple[bool, str]:
        """Use Insta360 Studio for conversion."""
        # Insta360 Studio CLI might look like:
        # Insta360Studio.exe -input video.insv -output video.mp4 -stitch

        cmd = [
            str(tool.path),
            "-input",
            str(input_path),
            "-output",
            str(output_path),
            "-stitch",
            "-exit",  # Close after stitching
        ]

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout for stitching
            )

            if result.returncode == 0 and output_path.exists():
                return True, f"Stitched with Insta360 Studio ({output_path.stat().st_size / 1e9:.2f}GB)"
            else:
                return False, f"Studio stitching failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Stitching timed out (took >1 hour)"

    def _convert_with_onex(
        self,
        input_path: Path,
        output_path: Path,
        tool: StitchTool,
    ) -> Tuple[bool, str]:
        """Use Insta360 OneX API for conversion."""
        # OneX API format (similar to Studio)
        cmd = [
            str(tool.path),
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ]

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )

            if result.returncode == 0 and output_path.exists():
                return True, f"Stitched with OneX API ({output_path.stat().st_size / 1e9:.2f}GB)"
            else:
                return False, f"OneX API stitching failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Stitching timed out"

    def _convert_with_ffmpeg(
        self,
        input_path: Path,
        output_path: Path,
    ) -> Tuple[bool, str]:
        """Use FFmpeg with Insta360 filter for conversion."""
        # FFmpeg command with insta360 filter
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-vf",
            "insta360=equirect",  # Output equirectangular 360 video
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_path),
        ]

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )

            if result.returncode == 0 and output_path.exists():
                return True, f"Converted with FFmpeg ({output_path.stat().st_size / 1e9:.2f}GB)"
            else:
                return False, f"FFmpeg conversion failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Conversion timed out"

    def get_tools_status(self) -> Dict[str, str]:
        """Get status of all detected tools."""
        status = {}

        if not self.available_tools:
            status["status"] = "NO_TOOLS"
            status["message"] = (
                "No Insta360 stitching tools detected. "
                "See SETUP.md for installation instructions."
            )
            return status

        status["detected"] = len(self.available_tools)
        status["tools"] = {
            name: {
                "path": str(tool.path),
                "available": tool.available,
                "version": tool.version or "unknown",
            }
            for name, tool in self.available_tools.items()
        }
        status["preferred"] = (
            self.preferred_tool.name if self.preferred_tool else "none"
        )

        return status
