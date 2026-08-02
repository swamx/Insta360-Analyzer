"""Main entry point with CLI."""

import sys
from pathlib import Path
import argparse

from src.utils.logger import setup_logging, get_logger
from src.utils.device_utils import get_device_info
from src.pipeline import Pipeline


def create_parser():
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Insta360 video analyzer with checkpoint/resume capability"
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=False,
        help="Input video or image file to process",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Base data directory (default: ./data)",
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Checkpoint directory (default: ./data/working/checkpoints)",
    )

    parser.add_argument(
        "--file-id",
        type=str,
        required=False,
        help="Unique file ID (default: auto-generated from input filename)",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint instead of restarting",
    )

    parser.add_argument(
        "--status",
        type=str,
        required=False,
        help="Check status of a file (requires file-id)",
    )

    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List all files with checkpoints",
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Verify system setup (CUDA, FFmpeg, etc)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def cmd_health_check(logger):
    """Run health check."""
    logger.info("=" * 60)
    logger.info("HEALTH CHECK")
    logger.info("=" * 60)

    # Device info
    device_info = get_device_info()
    logger.info(f"CUDA Available: {device_info['cuda_available']}")
    if device_info["cuda_available"]:
        logger.info(f"CUDA Version: {device_info['cuda_version']}")
        logger.info(f"GPU Device: {device_info['current_device_name']}")
        logger.info(f"GPU Memory: {device_info['total_memory_gb']:.1f}GB")
    else:
        logger.warning("CUDA not available - using CPU (slow)")

    # FFmpeg check
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            logger.info(f"FFmpeg: OK ({version_line})")
        else:
            logger.error("FFmpeg: FAILED")
    except Exception as e:
        logger.error(f"FFmpeg: NOT FOUND ({str(e)})")

    # PyTorch check
    try:
        import torch
        logger.info(f"PyTorch: OK (version {torch.__version__})")
    except Exception as e:
        logger.error(f"PyTorch: FAILED ({str(e)})")

    logger.info("=" * 60)


def cmd_list_files(pipeline, logger):
    """List all files with checkpoints."""
    file_ids = pipeline.list_all_files()

    if not file_ids:
        logger.info("No files found in checkpoints")
        return

    logger.info(f"Found {len(file_ids)} file(s):")
    logger.info("-" * 60)

    for file_id in file_ids:
        status = pipeline.get_file_status(file_id)
        logger.info(
            f"  {file_id}: {status['status']} "
            f"(next_stage={status['next_stage_to_run']})"
        )


def cmd_status(pipeline, file_id, logger):
    """Check status of a specific file."""
    status = pipeline.get_file_status(file_id)

    logger.info("=" * 60)
    logger.info(f"FILE STATUS: {file_id}")
    logger.info("=" * 60)
    logger.info(f"State: {status.get('status', 'unknown')}")
    logger.info(f"Last Complete Stage: {status.get('last_complete_stage', 'none')}")
    logger.info(f"Next Stage to Run: {status.get('next_stage_to_run', 'unknown')}")
    logger.info(f"Needs Processing: {status.get('needs_processing', False)}")

    if status.get("metadata"):
        metadata = status["metadata"]
        logger.info("\nMetadata:")
        logger.info(f"  Source: {metadata.get('source_path', 'unknown')}")
        logger.info(f"  Size: {metadata.get('file_size_gb', 0):.2f}GB")
        logger.info(f"  Type: {metadata.get('file_type', 'unknown')}")
        if metadata.get("duration_seconds"):
            logger.info(f"  Duration: {metadata.get('duration_seconds', 0):.1f}s")
        if metadata.get("frame_count"):
            logger.info(f"  Frames: {metadata.get('frame_count', 0)}")

    logger.info("=" * 60)


def cmd_process(pipeline, file_id, input_path, resume, logger):
    """Process a file."""
    logger.info("=" * 60)
    logger.info(f"PROCESSING: {file_id}")
    logger.info(f"Input: {input_path}")
    logger.info(f"Resume: {resume}")
    logger.info("=" * 60)

    result = pipeline.process_file(file_id, input_path, resume=resume)

    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info(f"Success: {result['success']}")

    for stage_name, stage_result in result["stages"].items():
        status = "✓" if stage_result.get("success") else "✗"
        skipped = " (skipped)" if stage_result.get("skipped") else ""
        placeholder = " (placeholder)" if stage_result.get("placeholder") else ""
        message = f" - {stage_result.get('message', '')}"
        logger.info(f"  {status} {stage_name}{skipped}{placeholder}{message}")

    if result.get("error"):
        logger.error(f"Error: {result['error']}")

    logger.info("=" * 60)

    return 0 if result["success"] else 1


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = 10 if args.verbose else 20  # DEBUG if verbose, else INFO
    logger = setup_logging(log_dir=Path("logs"), level=log_level)

    # Handle health check
    if args.health_check:
        cmd_health_check(logger)
        return 0

    # Setup pipeline
    if args.checkpoint_dir is None:
        args.checkpoint_dir = args.data_dir / "working" / "checkpoints"

    pipeline = Pipeline(args.checkpoint_dir, args.data_dir)

    # Handle list-files
    if args.list_files:
        cmd_list_files(pipeline, logger)
        return 0

    # Handle status check
    if args.status:
        cmd_status(pipeline, args.status, logger)
        return 0

    # Handle file processing
    if args.input:
        if not args.input.exists():
            logger.error(f"Input file not found: {args.input}")
            return 1

        # Generate file_id if not provided
        if not args.file_id:
            args.file_id = f"file_{args.input.stem}_{args.input.stat().st_mtime_ns}"

        return cmd_process(pipeline, args.file_id, args.input, args.resume, logger)

    # No command provided
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
