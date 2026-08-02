"""Unit tests for recovery manager."""

import pytest
from src.recovery import RecoveryManager


class TestRecoveryManager:
    """Test recovery manager functionality."""

    def test_scan_file_state_no_checkpoints(self, checkpoint_manager):
        """Test scanning file with no checkpoints."""
        recovery = RecoveryManager(checkpoint_manager)
        state = recovery.scan_file_state("nonexistent_file")

        assert state.file_id == "nonexistent_file"
        assert state.last_complete_stage is None
        assert state.next_stage_to_run == 0
        assert state.needs_processing()

    def test_scan_file_state_with_stages(self, checkpoint_manager):
        """Test scanning file with multiple completed stages."""
        file_id = "test_file"
        recovery = RecoveryManager(checkpoint_manager)

        # Create checkpoints for stages 1-2
        checkpoint_manager.save_file_checkpoint(file_id, "stage1_discovery", {"data": 1})
        checkpoint_manager.save_file_checkpoint(
            file_id, "stage2_extraction", {"data": 2}
        )
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_progress": {
                    "stage2_extraction": {"last_completed_frame": 50}
                },
            },
        )

        state = recovery.scan_file_state(file_id)

        assert state.last_complete_stage == 1
        assert state.next_stage_to_run == 2
        assert state.needs_processing()

    def test_scan_all_files(self, checkpoint_manager):
        """Test scanning all files."""
        recovery = RecoveryManager(checkpoint_manager)

        # Create checkpoints for multiple files
        for i in range(3):
            file_id = f"file_{i}"
            checkpoint_manager.save_file_metadata(file_id, {"file_id": file_id})

        states = recovery.scan_all_files()
        assert len(states) == 3

    def test_get_frame_resume_point_no_checkpoint(self, checkpoint_manager):
        """Test getting resume point when no checkpoint exists."""
        recovery = RecoveryManager(checkpoint_manager)
        resume_point = recovery.get_frame_resume_point("nonexistent", "stage3_analysis")
        assert resume_point is None

    def test_get_frame_resume_point_with_progress(self, checkpoint_manager):
        """Test getting resume point from checkpoint."""
        file_id = "test_file"
        recovery = RecoveryManager(checkpoint_manager)

        # Create checkpoint with progress
        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage3_analysis",
            {
                "stage": "stage3_analysis",
                "stage_progress": {
                    "stage3_analysis": {"last_completed_frame": 47}
                },
            },
        )

        resume_point = recovery.get_frame_resume_point(file_id, "stage3_analysis")
        assert resume_point == 48  # Should resume from next frame after 47


class TestFileRecoveryState:
    """Test FileRecoveryState dataclass."""

    def test_needs_processing_no_stages(self, checkpoint_manager):
        """Test file needing processing."""
        recovery = RecoveryManager(checkpoint_manager)
        state = recovery.scan_file_state("new_file")
        assert state.needs_processing()

    def test_needs_processing_all_complete(self, checkpoint_manager):
        """Test file that is fully processed."""
        file_id = "complete_file"
        recovery = RecoveryManager(checkpoint_manager)

        # Create checkpoints for all 5 stages
        for i, stage in enumerate(
            [
                "stage1_discovery",
                "stage2_extraction",
                "stage3_analysis",
                "stage4_highlights",
                "stage5_encoding",
            ]
        ):
            checkpoint_manager.save_file_checkpoint(file_id, stage, {"data": i})

        state = recovery.scan_file_state(file_id)
        assert not state.needs_processing()
        assert state.next_stage_to_run == 5

    def test_can_resume_current_stage(self, checkpoint_manager):
        """Test detecting if current stage can resume."""
        file_id = "test_file"
        recovery = RecoveryManager(checkpoint_manager)

        # Create file metadata with progress
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_progress": {"stage3_analysis": {"last_completed_frame": 100}},
            },
        )

        state = recovery.scan_file_state(file_id)
        assert state.can_resume_current_stage()

    def test_state_repr(self, checkpoint_manager):
        """Test state string representation."""
        recovery = RecoveryManager(checkpoint_manager)
        state = recovery.scan_file_state("test_file")

        repr_str = repr(state)
        assert "test_file" in repr_str
        assert "FileRecoveryState" in repr_str
