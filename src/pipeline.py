"""Main pipeline orchestrator that sequences all stages."""

from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger, ContextualLogger
from src.storage.checkpoint_manager import CheckpointManager
from src.stages.stage0_insta360_conversion import Stage0Insta360Conversion
from src.stages.stage1_discovery import Stage1Discovery
from src.stages.stage2_scene_detection import Stage2SceneDetection
from src.stages.stage3_vision_editor import Stage3VisionEditor
from src.stages.stage4_reel_assembly import Stage4ReelAssembly
from src.stages.stage5_encoding import Stage5Encoding


logger = get_logger("pipeline")


class Pipeline:
    """Orchestrates execution of all pipeline stages with checkpoint/resume support."""

    def __init__(
        self,
        checkpoint_dir: Path,
        data_dir: Path,
        max_reel_duration_seconds: float = 15.0,
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.data_dir = Path(data_dir)
        self.working_dir = self.data_dir / "working"
        self.output_dir = self.data_dir / "output"
        self.max_reel_duration_seconds = max_reel_duration_seconds

        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize managers
        self.checkpoint_manager = CheckpointManager(self.checkpoint_dir)

        # Initialize stages
        self.stage0 = None  # Initialized per-file since it needs video_path
        self.stage1 = Stage1Discovery(self.checkpoint_manager)
        self.stage2 = Stage2SceneDetection(self.checkpoint_manager)
        self.stage3 = Stage3VisionEditor(self.checkpoint_manager)
        self.stage4 = Stage4ReelAssembly(
            self.checkpoint_manager,
            max_duration_seconds=max_reel_duration_seconds,
        )
        self.stage5 = Stage5Encoding(self.checkpoint_manager)

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
            next_stage_to_run = 0
            if resume:
                metadata = self.checkpoint_manager.load_file_metadata(file_id)
                if metadata:
                    state = metadata.get("state", "UNKNOWN")
                    # Map state to next stage
                    state_to_stage = {
                        "UNKNOWN": 0,
                        "CREATED": 0,
                        "CONVERTED": 0,
                        "DISCOVERED": 1,
                        "SCENES_DETECTED": 2,
                        "ANALYZED": 3,
                        "REEL_ASSEMBLED": 4,
                        "COMPLETED": 5,
                    }
                    next_stage_to_run = state_to_stage.get(state, 0)
                    ctx_logger.info(f"Resume mode: state={state}, next_stage={next_stage_to_run}")

            # Stage 0.5: Insta360 Conversion
            processed_input_path = input_path
            if not resume or next_stage_to_run <= 0:
                ctx_logger.info("Running Stage 0.5: Insta360 Conversion")
                self.stage0 = Stage0Insta360Conversion(input_path, self.working_dir)
                result = self.stage0.run()
                results["stages"]["stage0_insta360_conversion"] = {
                    "success": True,
                    "was_360": result.get("was_360", False),
                    "conversion_applied": result.get("conversion_applied", False),
                }
                processed_input_path = Path(result.get("output_video", input_path))
                ctx_logger.info(
                    f"Stage 0.5 complete: was_360={result.get('was_360')}, "
                    f"converted={result.get('conversion_applied')}"
                )
            else:
                ctx_logger.info("Stage 0.5: Insta360 Conversion (skipped - already complete)")
                results["stages"]["stage0_insta360_conversion"] = {"success": True, "skipped": True}

            # Stage 1: Discovery
            if not resume or next_stage_to_run <= 0:
                ctx_logger.info("Running Stage 1: Discovery")
                result = self.stage1.run(file_id, processed_input_path)
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

            # Stage 2: Scene Detection
            if not resume or next_stage_to_run <= 1:
                ctx_logger.info("Running Stage 2: Scene Detection")
                result = self.stage2.run(file_id, processed_input_path)
                results["stages"]["stage2_scene_detection"] = {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
                if not result.success:
                    results["error"] = f"Stage 2 failed: {result.message}"
                    return results
                stage2_data = result.data
            else:
                ctx_logger.info("Stage 2: Scene Detection (skipped - already complete)")
                results["stages"]["stage2_scene_detection"] = {"success": True, "skipped": True}
                # Load checkpoint for next stage
                stage2_cp = self.checkpoint_manager.load_file_checkpoint(file_id, "stage2_scene_detection")
                stage2_data = {"scene_count": stage2_cp.get("total_scenes", 0)}

            # Stage 3: Vision Editor
            if not resume or next_stage_to_run <= 2:
                ctx_logger.info("Running Stage 3: Vision Editor")
                stage2_cp = self.checkpoint_manager.load_file_checkpoint(file_id, "stage2_scene_detection")
                result = self.stage3.run(file_id, stage2_cp)
                results["stages"]["stage3_vision_editor"] = {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
                if not result.success:
                    results["error"] = f"Stage 3 failed: {result.message}"
                    return results
            else:
                ctx_logger.info("Stage 3: Vision Editor (skipped - already complete)")
                results["stages"]["stage3_vision_editor"] = {"success": True, "skipped": True}

            # Stage 4: Reel Assembly
            if not resume or next_stage_to_run <= 3:
                ctx_logger.info("Running Stage 4: Reel Assembly")
                stage3_cp = self.checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
                result = self.stage4.run(file_id, stage3_cp)
                results["stages"]["stage4_reel_assembly"] = {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
                if not result.success:
                    results["error"] = f"Stage 4 failed: {result.message}"
                    return results
            else:
                ctx_logger.info("Stage 4: Reel Assembly (skipped - already complete)")
                results["stages"]["stage4_reel_assembly"] = {"success": True, "skipped": True}

            # Stage 5: Encoding
            if not resume or next_stage_to_run <= 4:
                ctx_logger.info("Running Stage 5: Encoding")
                stage4_cp = self.checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
                result = self.stage5.run(file_id, processed_input_path, stage4_cp)
                results["stages"]["stage5_encoding"] = {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
                if not result.success:
                    results["error"] = f"Stage 5 failed: {result.message}"
                    return results
            else:
                ctx_logger.info("Stage 5: Encoding (skipped - already complete)")
                results["stages"]["stage5_encoding"] = {"success": True, "skipped": True}

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
            "last_complete_stage": next_stage_to_run,
            "next_stage_to_run": next_stage_to_run,
            "needs_processing": recovery_state.needs_processing(),
            "metadata": metadata,
        }

    def list_all_files(self) -> list:
        """List all files with checkpoints."""
        return self.checkpoint_manager.list_all_files()
