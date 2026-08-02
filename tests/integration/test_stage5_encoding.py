"""Integration tests for Stage 5: Encoding."""

import pytest
from pathlib import Path

from src.stages.stage5_encoding import Stage5Encoding
from src.utils.logger import get_logger


logger = get_logger("test_stage5_encoding")


class TestStage5BasicEncoding:
    """Test basic encoding."""

    def test_encode_reel_basic(self, checkpoint_manager, temp_dir):
        """Test basic reel encoding."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_encode_001"

        # Create mock video file
        video_path = temp_dir / "test_video.mp4"
        video_path.write_bytes(b"mock video")

        reel_plan = {
            "clips": [
                {
                    "scene_id": "scene_001",
                    "start_ms": 0,
                    "end_ms": 5000,
                    "clip_duration": 5.0,
                },
                {
                    "scene_id": "scene_002",
                    "start_ms": 5000,
                    "end_ms": 10000,
                    "clip_duration": 5.0,
                },
            ],
            "total_duration": 10.0,
        }

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)

        assert result.success
        assert "output_path" in result.data
        assert result.data["duration"] == 10.0

    def test_encoding_checkpoint_structure(self, checkpoint_manager, temp_dir):
        """Test checkpoint structure."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_checkpoint_encode_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        reel_plan = {
            "clips": [{"scene_id": "scene_001", "start_ms": 0, "end_ms": 3000}],
            "total_duration": 3.0,
        }

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)
        assert result.success

        # Verify checkpoint
        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage5_encoding")

        assert "source_video" in cp
        assert "clips_encoded" in cp
        assert "output_path" in cp
        assert "final_duration_seconds" in cp
        assert "status" in cp
        assert cp["status"] == "ENCODED"

    def test_can_resume_after_encoding(self, checkpoint_manager, temp_dir):
        """Test resume capability."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_resume_encode_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        reel_plan = {
            "clips": [{"scene_id": "scene_001", "start_ms": 0, "end_ms": 3000}],
            "total_duration": 3.0,
        }

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)
        assert result.success

        # Check can resume
        assert stage.can_resume(file_id)

    def test_get_progress(self, checkpoint_manager, temp_dir):
        """Test progress tracking."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_progress_encode_001"

        # No checkpoint
        assert stage.get_progress(file_id) is None

        # With checkpoint
        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        reel_plan = {"clips": [{"scene_id": "s1"}], "total_duration": 5.0}
        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        stage.run(file_id, video_path, checkpoint)

        progress = stage.get_progress(file_id)
        assert progress is not None
        assert progress.total_items > 0


class TestStage5OutputVerification:
    """Test output verification."""

    def test_output_path_set(self, checkpoint_manager, temp_dir):
        """Test output path is set correctly."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_output_path_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        reel_plan = {
            "clips": [{"scene_id": "scene_001", "start_ms": 0, "end_ms": 5000}],
            "total_duration": 5.0,
        }

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)

        assert result.success
        assert f"{file_id}_reel.mp4" in result.data["output_path"]

    def test_duration_preserved(self, checkpoint_manager, temp_dir):
        """Test duration is preserved from reel plan."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_duration_preserve_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        expected_duration = 14.8

        reel_plan = {
            "clips": [
                {"scene_id": "s1", "start_ms": 0, "end_ms": 5000, "clip_duration": 5.0},
                {"scene_id": "s2", "start_ms": 5000, "end_ms": 9800, "clip_duration": 4.8},
            ],
            "total_duration": expected_duration,
        }

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)

        assert result.success
        assert result.data["duration"] == expected_duration


class TestStage5ErrorHandling:
    """Test error handling."""

    def test_no_clips_in_plan(self, checkpoint_manager, temp_dir):
        """Test handling of no clips."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_no_clips_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        reel_plan = {"clips": []}

        checkpoint = {"reel_plan": reel_plan}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)

        assert not result.success
        assert "no clips" in result.message.lower()

    def test_missing_reel_plan(self, checkpoint_manager, temp_dir):
        """Test handling of missing reel plan."""
        stage = Stage5Encoding(checkpoint_manager)

        file_id = "test_no_plan_001"

        video_path = temp_dir / "test.mp4"
        video_path.write_bytes(b"test")

        checkpoint = {}  # No reel plan

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "REEL_ASSEMBLED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, video_path, checkpoint)

        assert not result.success
        assert "no clips" in result.message.lower()
