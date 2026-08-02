"""Integration tests for Stage 3 (Vision Analysis) with checkpoint/resume."""

import pytest
from pathlib import Path

from src.stages.stage3_analysis import Stage3Analysis
from src.utils.logger import get_logger


logger = get_logger("test_stage3_analysis")


class TestStage3BasicAnalysis:
    """Test basic Stage 3 functionality."""

    def test_analyze_frames(self, checkpoint_manager, test_frames):
        """Test analyzing a set of frames."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_video_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, frames_dir)

        assert result.success
        assert "frame_count" in result.data
        assert result.data["frame_count"] == 100

    def test_analysis_saves_checkpoint(self, checkpoint_manager, test_frames):
        """Test that analysis saves checkpoint."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_checkpoint_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, frames_dir)
        assert result.success

        # Verify checkpoint was saved
        assert checkpoint_manager.checkpoint_exists(file_id, "stage3_analysis")

    def test_can_resume_after_analysis(self, checkpoint_manager, test_frames):
        """Test that stage knows it can resume."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_resume_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # First run
        result = stage.run(file_id, frames_dir)
        assert result.success

        # Check if can resume
        assert stage.can_resume(file_id)

    def test_get_progress(self, checkpoint_manager, test_frames):
        """Test getting progress information."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_progress_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # Run analysis
        result = stage.run(file_id, frames_dir)
        assert result.success

        # Get progress
        progress = stage.get_progress(file_id)
        assert progress is not None
        assert progress.total_items == 100
        assert progress.completed_items == 100


class TestStage3Checkpoint:
    """Test Stage 3 checkpoint and recovery."""

    def test_checkpoint_contains_embeddings(self, checkpoint_manager, test_frames):
        """Test that checkpoint contains embeddings."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_embeddings_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, frames_dir)
        assert result.success

        # Load checkpoint and verify embeddings
        checkpoint = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        assert "embeddings" in checkpoint
        assert len(checkpoint["embeddings"]) == 100
        assert len(checkpoint["embeddings"][0]) == 1024  # Embedding dimension

    def test_checkpoint_contains_analysis(self, checkpoint_manager, test_frames):
        """Test that checkpoint contains analysis metadata."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_analysis_metadata_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, frames_dir)
        assert result.success

        # Load checkpoint and verify analysis
        checkpoint = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        assert "analysis" in checkpoint
        assert len(checkpoint["analysis"]) == 100
        assert "brightness" in checkpoint["analysis"][0]
        assert "objects" in checkpoint["analysis"][0]


class TestStage3Resume:
    """Test Stage 3 resume from checkpoint."""

    def test_resume_from_checkpoint(self, checkpoint_manager, test_frames):
        """Test resuming from saved checkpoint."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_resume_checkpoint_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # First run - complete
        result1 = stage.run(file_id, frames_dir)
        assert result1.success

        # Verify checkpoint exists
        assert checkpoint_manager.checkpoint_exists(file_id, "stage3_analysis")
        checkpoint1 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        frame_count_1 = checkpoint1["frame_count"]

        # Second run - should resume and complete without duplication
        result2 = stage.run(file_id, frames_dir)
        assert result2.success

        checkpoint2 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        frame_count_2 = checkpoint2["frame_count"]

        # Frame count should be same (no re-processing)
        assert frame_count_2 == frame_count_1 == 100

    def test_resume_from_specific_frame(self, checkpoint_manager, test_frames):
        """Test resuming from specific frame index."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_resume_from_frame_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # Run with resume from frame 50
        result = stage.run(file_id, frames_dir, resume_from=50)
        assert result.success

        # Should have analyzed frames 50-99
        progress = stage.get_progress(file_id)
        assert progress.completed_items >= 50

    def test_partial_run_and_resume(self, checkpoint_manager, test_frames):
        """Test partial run followed by resume."""
        frames_dir, frames = test_frames

        # Create stage with small batch size to force multiple checkpoints
        stage = Stage3Analysis(
            checkpoint_manager,
            batch_size=25,
            skip_model_load=True,
        )

        file_id = "test_partial_resume_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # First run - process only first 50 frames by resuming from 50
        result1 = stage.run(file_id, frames_dir, resume_from=0)
        # Let it run the first batch
        assert result1.success

        checkpoint1 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        last_frame_1 = (
            checkpoint1.get("stage_progress", {})
            .get("stage3_analysis", {})
            .get("last_completed_frame", -1)
        )

        # Second run - resume from where we left off
        result2 = stage.run(file_id, frames_dir)
        assert result2.success

        checkpoint2 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        last_frame_2 = (
            checkpoint2.get("stage_progress", {})
            .get("stage3_analysis", {})
            .get("last_completed_frame", -1)
        )

        # Should have progressed beyond first checkpoint
        assert last_frame_2 >= last_frame_1

    def test_no_duplicate_embeddings_on_resume(self, checkpoint_manager, test_frames):
        """Test that resuming doesn't create duplicate embeddings."""
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_no_duplication_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # First complete run
        result1 = stage.run(file_id, frames_dir)
        assert result1.success

        checkpoint1 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        embeddings_1 = checkpoint1["embeddings"]

        # Second resume run
        result2 = stage.run(file_id, frames_dir)
        assert result2.success

        checkpoint2 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        embeddings_2 = checkpoint2["embeddings"]

        # Should have exact same embeddings (no duplication)
        assert len(embeddings_2) == len(embeddings_1)
        assert len(embeddings_2) == 100


class TestStage3ErrorHandling:
    """Test Stage 3 error handling."""

    def test_missing_frames_directory(self, checkpoint_manager, temp_dir):
        """Test handling of missing frames directory."""
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_missing_frames_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # Try to run with nonexistent directory
        result = stage.run(file_id, temp_dir / "nonexistent")
        assert not result.success
        assert "No frames found" in result.message

    def test_progress_without_checkpoint(self, checkpoint_manager):
        """Test getting progress when no checkpoint exists."""
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        progress = stage.get_progress("nonexistent_file")
        assert progress is None

    def test_can_resume_without_checkpoint(self, checkpoint_manager):
        """Test can_resume returns False when no checkpoint."""
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        can_resume = stage.can_resume("nonexistent_file")
        assert not can_resume
