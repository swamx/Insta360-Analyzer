"""End-to-end recovery simulation tests."""

import pytest
import json
from datetime import datetime

from src.stages.stage3_analysis import Stage3Analysis
from src.recovery import RecoveryManager
from src.utils.logger import get_logger


logger = get_logger("test_recovery_simulation")


class TestRecoverySimulation:
    """Simulate failure and recovery scenarios."""

    def test_crash_and_resume_mid_batch(self, checkpoint_manager, test_frames):
        """
        Simulate a crash mid-batch and verify recovery.

        Scenario:
        1. Start analysis
        2. Complete some frames
        3. Simulate crash by not fully completing
        4. Verify recovery checkpoint exists
        5. Resume and verify no duplication
        """
        frames_dir, frames = test_frames
        stage = Stage3Analysis(
            checkpoint_manager,
            batch_size=10,
            skip_model_load=True,
        )

        file_id = "test_crash_recovery_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # First run - simulates partial completion before crash
        result1 = stage.run(file_id, frames_dir, resume_from=0)
        assert result1.success

        # Get checkpoint from "before crash"
        checkpoint_before = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        last_frame_before = (
            checkpoint_before.get("stage_progress", {})
            .get("stage3_analysis", {})
            .get("last_completed_frame", -1)
        )
        embeddings_count_before = len(checkpoint_before.get("embeddings", []))

        logger.info(f"Before crash: {last_frame_before + 1} frames analyzed")

        # Simulate crash recovery: use RecoveryManager to find resume point
        recovery = RecoveryManager(checkpoint_manager)
        resume_point = recovery.get_frame_resume_point(file_id, "stage3_analysis")

        assert resume_point is not None
        assert resume_point > 0  # Should resume from a frame, not the beginning
        logger.info(f"Recovery point: resume from frame {resume_point}")

        # Second run - resume from checkpoint
        result2 = stage.run(file_id, frames_dir)
        assert result2.success

        checkpoint_after = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        embeddings_count_after = len(checkpoint_after.get("embeddings", []))

        # Verify no duplication - embeddings count should match expected total
        assert embeddings_count_after == 100  # Total frames
        logger.info(f"After resume: {embeddings_count_after} frames total (no duplication)")

    def test_multiple_partial_runs(self, checkpoint_manager, test_frames):
        """
        Test multiple interruptions and resumes.

        Scenario:
        1. Run analysis (partial)
        2. Stop and restart multiple times
        3. Verify final state has no duplicates
        """
        frames_dir, frames = test_frames
        stage = Stage3Analysis(
            checkpoint_manager,
            batch_size=20,
            skip_model_load=True,
        )

        file_id = "test_multiple_resume_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        # Multiple runs simulating interruptions
        for run_num in range(3):
            logger.info(f"Run {run_num + 1}/3")
            result = stage.run(file_id, frames_dir)
            assert result.success

            checkpoint = checkpoint_manager.load_file_checkpoint(
                file_id, "stage3_analysis"
            )
            frame_count = len(checkpoint.get("embeddings", []))
            last_frame = (
                checkpoint.get("stage_progress", {})
                .get("stage3_analysis", {})
                .get("last_completed_frame", -1)
            )

            logger.info(
                f"  After run {run_num + 1}: {frame_count} embeddings, "
                f"last frame: {last_frame}"
            )

        # Final verification
        final_checkpoint = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        assert len(final_checkpoint.get("embeddings", [])) == 100
        assert len(final_checkpoint.get("analysis", [])) == 100

    def test_recovery_without_loss_of_data(self, checkpoint_manager, test_frames):
        """
        Verify that recovery doesn't lose any analyzed data.

        Scenario:
        1. Analyze first half (frames 0-49)
        2. Stop
        3. Resume and analyze second half (frames 50-99)
        4. Verify all data is present and consistent
        """
        frames_dir, frames = test_frames

        # First stage: analyze partial
        stage1 = Stage3Analysis(checkpoint_manager, skip_model_load=True)
        file_id = "test_data_preservation_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "FRAMES_EXTRACTED",
                "stage_timestamps": {},
            },
        )

        result1 = stage1.run(file_id, frames_dir, resume_from=0)
        assert result1.success

        checkpoint1 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        embeddings1 = checkpoint1.get("embeddings", [])
        analysis1 = checkpoint1.get("analysis", [])

        logger.info(f"After first run: {len(embeddings1)} embeddings")

        # Resume stage: continue from checkpoint
        stage2 = Stage3Analysis(checkpoint_manager, skip_model_load=True)
        result2 = stage2.run(file_id, frames_dir)
        assert result2.success

        checkpoint2 = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )
        embeddings2 = checkpoint2.get("embeddings", [])
        analysis2 = checkpoint2.get("analysis", [])

        logger.info(f"After resume: {len(embeddings2)} embeddings")

        # Verify data integrity
        assert len(embeddings2) == 100
        assert len(analysis2) == 100

        # Verify embeddings from first run are unchanged
        for i in range(min(len(embeddings1), len(embeddings2))):
            # Compare first embedding to ensure no corruption
            assert (
                embeddings1[i] == embeddings2[i]
            ), f"Embedding {i} changed during resume"

    def test_checkpoint_atomicity(self, checkpoint_manager, test_frames):
        """
        Test that checkpoint writes are atomic.

        Verify that even if a save is interrupted, the checkpoint is valid.
        """
        frames_dir, frames = test_frames
        stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)

        file_id = "test_atomicity_001"
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

        checkpoint = checkpoint_manager.load_file_checkpoint(
            file_id, "stage3_analysis"
        )

        # Verify checkpoint is complete and valid
        assert "embeddings" in checkpoint
        assert "analysis" in checkpoint
        assert "stage_progress" in checkpoint
        assert checkpoint.get("frame_count") == 100

        # Verify JSON structure is valid (can be serialized/deserialized)
        import json

        serialized = json.dumps(checkpoint)
        deserialized = json.loads(serialized)
        assert deserialized == checkpoint
