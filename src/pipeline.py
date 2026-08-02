"""Main pipeline orchestrator that sequences all stages."""

from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger, ContextualLogger
from src.storage.checkpoint_manager import CheckpointManager
from src.recovery import RecoveryManager
from src.stages.stage1_discovery import Stage1Discovery
from src.stages.stage2_extraction import Stage2Extraction


logger = get_logger("pipeline")


class Pipeline:
    """Orchestrates execution of all pipeline stages with checkpoint/resume support."""

    def __init__(
        self,
        checkpoint_dir: Path,
        data_dir: Path,
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.data_dir = Path(data_dir)
        self.working_dir = self.data_dir / "working"
        self.output_dir = self.data_dir / "output"

        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize managers
        self.checkpoint_manager = CheckpointManager(self.checkpoint_dir)
        self.recovery_manager = RecoveryManager(self.checkpoint_manager)

        # Initialize stages
        self.stage1 = Stage1Discovery(self.checkpoint_manager)
        self.stage2 = Stage2Extraction(self.checkpoint_manager, frame_interval=2.0)

        logger.info(
            f"Pipeline initialized (checkpoint_dir={self.checkpoint_dir}, "
            f"data_dir={self.data_dir})"
        )

    def process_file(
        self,
        file_id: str,
        input_path: Path,
        resume: bool = False,
    ) -> dict:
        """
        Process a single file through the pipeline.

        Args:
            file_id: Unique identifier for this file
            input_path: Path to input video/image
            resume: If True, resume from last checkpoint; if False, restart

        Returns:
            Dictionary with processing results and final state
        """
        ctx_logger = ContextualLogger(logger, file_id=file_id)
        ctx_logger.info(f"Starting processing (resume={resume})")

        results = {
            "file_id": file_id,
            "input_path": str(input_path),
            "stages": {},
            "success": False,
            "error": None,
        }

        try:
            # Determine recovery point if resuming
            recovery_state = None
            if resume:
                recovery_state = self.recovery_manager.scan_file_state(file_id)
                ctx_logger.info(
                    f"Resume mode: last_complete_stage={recovery_state.last_complete_stage}, "
                    f"next_to_run={recovery_state.next_stage_to_run}"
                )

            # Stage 1: Discovery
            if not resume or recovery_state.next_stage_to_run <= 0:
                ctx_logger.info("Running Stage 1: Discovery")
                result = self.stage1.run(file_id, input_path)
                results["stages"]["stage1_discovery"] = {
                    "success": result.success,
                    "message": result.message,
                }
                if not result.success:
                    results["error"] = f"Stage 1 failed: {result.message}"
                    return results
            else:
                ctx_logger.info("Stage 1: Discovery (skipped - already complete)")
                results["stages"]["stage1_discovery"] = {"success": True, "skipped": True}

            # Stage 2: Frame Extraction
            if not resume or recovery_state.next_stage_to_run <= 1:
                ctx_logger.info("Running Stage 2: Frame Extraction")
                result = self.stage2.run(
                    file_id,
                    input_path,
                    self.working_dir,
                )
                results["stages"]["stage2_extraction"] = {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
                if not result.success:
                    results["error"] = f"Stage 2 failed: {result.message}"
                    return results
            else:
                ctx_logger.info("Stage 2: Frame Extraction (skipped - already complete)")
                results["stages"]["stage2_extraction"] = {"success": True, "skipped": True}

            # Stages 3-5 placeholders
            # TODO: Implement in Phase 0
            ctx_logger.info("Stages 3-5: Placeholder (not yet implemented)")
            results["stages"]["stage3_analysis"] = {"success": True, "placeholder": True}
            results["stages"]["stage4_highlights"] = {"success": True, "placeholder": True}
            results["stages"]["stage5_encoding"] = {"success": True, "placeholder": True}

            results["success"] = True
            ctx_logger.info("Processing complete")

        except Exception as e:
            ctx_logger.exception(f"Pipeline error: {str(e)}")
            results["error"] = str(e)

        return results

    def get_file_status(self, file_id: str) -> dict:
        """Get current processing status for a file."""
        recovery_state = self.recovery_manager.scan_file_state(file_id)

        if recovery_state is None:
            return {"file_id": file_id, "status": "not_found"}

        metadata = self.checkpoint_manager.load_file_metadata(file_id)

        return {
            "file_id": file_id,
            "status": metadata.get("state", "unknown") if metadata else "unknown",
            "last_complete_stage": recovery_state.last_complete_stage,
            "next_stage_to_run": recovery_state.next_stage_to_run,
            "needs_processing": recovery_state.needs_processing(),
            "metadata": metadata,
        }

    def list_all_files(self) -> list:
        """List all files with checkpoints."""
        return self.checkpoint_manager.list_all_files()
