#!/usr/bin/env python3
"""Detect available Insta360 stitching tools."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.insta360_converter import Insta360Converter
from src.utils.logger import setup_logging


def main():
    """Run Insta360 tool detection."""
    logger = setup_logging()

    logger.info("=" * 70)
    logger.info("INSTA360 TOOL DETECTION")
    logger.info("=" * 70)

    converter = Insta360Converter()
    status = converter.get_tools_status()

    if status.get("status") == "NO_TOOLS":
        logger.error("❌ NO INSTA360 STITCHING TOOLS DETECTED")
        logger.warning("\nYou need to install one of the following:")
        logger.warning("")
        logger.warning("1. INSTA360 STUDIO (Recommended)")
        logger.warning("   - Download: https://www.insta360.com/download/insta360-studio")
        logger.warning("   - Installation: Run installer, use default paths")
        logger.warning("   - This is the official Insta360 stitching tool")
        logger.warning("")
        logger.warning("2. INSTA360 ONEX API")
        logger.warning("   - Only available if you have Insta360 ONE X camera")
        logger.warning("   - Comes with OneX software")
        logger.warning("")
        logger.warning("3. FFmpeg with Insta360 filter (Community)")
        logger.warning("   - Build FFmpeg with insta360 filter support")
        logger.warning("   - Advanced: requires compilation")
        logger.warning("")
        return 1

    logger.info(f"✅ DETECTED: {status['detected']} tool(s)")
    logger.info("")

    logger.info("Detected Tools:")
    logger.info("-" * 70)
    for tool_name, tool_info in status.get("tools", {}).items():
        logger.info(f"  • {tool_name}")
        logger.info(f"    Path: {tool_info['path']}")
        logger.info(f"    Available: {tool_info['available']}")
        logger.info(f"    Version: {tool_info['version']}")
        logger.info("")

    preferred = status.get("preferred")
    logger.info(f"⭐ PREFERRED: {preferred}")
    logger.info("")

    logger.info("=" * 70)
    logger.info("Ready to process Insta360 videos!")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
