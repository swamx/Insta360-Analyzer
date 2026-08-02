"""Recovery logic for restoring to last checkpoint and resuming work."""

from pathlib import Path
from typing import Dict, Optional, Tuple

from src.utils.logger import get_logger
from src.storage.checkpoint_manager import CheckpointManager


logger = get_logger("recovery")


class RecoveryManager:
    """Determine recovery point and resume state for interrupted processing."""

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager

    def scan_file_state(self, file_id: str) -> "FileRecoveryState":
        """Scan checkpoints for a file and determine recovery state."""
        last_complete_stage = self.checkpoint_manager.get_last_complete_stage(file_id)
        metadata = self.checkpoint_manager.load_file_metadata(file_id)

        state = FileRecoveryState(
            file_id=file_id,
            last_complete_stage=last_complete_stage,
            metadata=metadata,
        )

        if last_complete_stage is not None:
            stage_names = [
                "stage1_discovery",
                "stage2_extraction",
                "stage3_analysis",
                "stage4_highlights",
                "stage5_encoding",
            ]
            state.next_stage_to_run = last_complete_stage + 1
            state.last_complete_stage_name = stage_names[last_complete_stage]

            if metadata:
                state.stage_progress = metadata.get("stage_progress", {})

        return state

    def get_frame_resume_point(
        self,
        file_id: str,
        stage: str,
    ) -> Optional[int]:
        """Get the frame index to resume from in a batch processing stage."""
        try:
            checkpoint = self.checkpoint_manager.load_file_checkpoint(file_id, stage)
            stage_progress = checkpoint.get("stage_progress", {})

            if stage in stage_progress:
                return stage_progress[stage].get("last_completed_frame", -1) + 1

        except Exception as e:
            logger.warning(
                f"Could not load resume point for {file_id}/{stage}: {str(e)}"
            )

        return None

    def scan_all_files(self) -> Dict[str, "FileRecoveryState"]:
        """Scan all checkpoints and determine recovery state for each file."""
        file_ids = self.checkpoint_manager.list_all_files()
        states = {}

        for file_id in file_ids:
            states[file_id] = self.scan_file_state(file_id)

        return states


class FileRecoveryState:
    """State information for recovering a single file's processing."""

    def __init__(self, file_id: str, last_complete_stage: Optional[int], metadata: dict):
        self.file_id = file_id
        self.last_complete_stage = last_complete_stage  # 0-4, or None if no stages complete
        self.next_stage_to_run = (last_complete_stage + 1) if last_complete_stage else 0
        self.last_complete_stage_name = None
        self.metadata = metadata
        self.stage_progress = {}

    def needs_processing(self) -> bool:
        """Check if file needs further processing."""
        return self.next_stage_to_run < 5

    def can_resume_current_stage(self) -> bool:
        """Check if current stage has partial completion."""
        if not self.metadata:
            return False
        return "stage_progress" in self.metadata and len(self.metadata["stage_progress"]) > 0

    def __repr__(self) -> str:
        return (
            f"FileRecoveryState(file_id={self.file_id}, "
            f"last_complete={self.last_complete_stage}, "
            f"next_to_run={self.next_stage_to_run})"
        )
