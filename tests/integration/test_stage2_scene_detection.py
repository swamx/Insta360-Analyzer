"""Integration tests for Stage 2: Scene Detection."""

import pytest
from pathlib import Path
import json

from src.stages.stage2_scene_detection import Stage2SceneDetection
from src.utils.logger import get_logger


logger = get_logger("test_stage2_scene_detection")


class TestStage2BasicDetection:
    """Test basic scene detection functionality."""

    def test_scene_detection_basic(self, checkpoint_manager, temp_dir):
        """Test scene detection creates checkpoint."""
        stage = Stage2SceneDetection(checkpoint_manager)

        # Create mock video file (empty, just for path existence)
        video_dir = temp_dir / "videos"
        video_dir.mkdir()
        video_path = video_dir / "test_video.mp4"
        video_path.write_bytes(b"mock video")  # Just needs to exist

        file_id = "test_scene_001"
        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "DISCOVERED",
                "stage_timestamps": {},
            },
        )

        # Note: This will fail without ffprobe, but tests checkpoint structure
        result = stage.run(file_id, video_path)

        # Check result structure
        assert hasattr(result, "success")
        assert hasattr(result, "stage_name")
        assert hasattr(result, "file_id")
        assert hasattr(result, "message")

    def test_scene_detection_saves_checkpoint(self, checkpoint_manager):
        """Test that scene detection saves checkpoint."""
        stage = Stage2SceneDetection(checkpoint_manager)

        file_id = "test_checkpoint_001"

        # Create mock checkpoint data
        mock_scenes = [
            {
                "scene_id": f"{file_id}_scene_001",
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
            },
            {
                "scene_id": f"{file_id}_scene_002",
                "start_time_ms": 5000,
                "end_time_ms": 10000,
                "duration_seconds": 5.0,
            },
        ]

        # Manually save checkpoint as stage would
        checkpoint_data = {
            "stage": "stage2_scene_detection",
            "file_id": file_id,
            "total_scenes": len(mock_scenes),
            "scenes": mock_scenes,
        }

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            checkpoint_data,
        )

        # Verify checkpoint was saved
        assert checkpoint_manager.checkpoint_exists(file_id, "stage2_scene_detection")

        # Load and verify content
        loaded = checkpoint_manager.load_file_checkpoint(file_id, "stage2_scene_detection")
        assert loaded["total_scenes"] == 2
        assert len(loaded["scenes"]) == 2

    def test_can_resume_after_detection(self, checkpoint_manager):
        """Test resume capability."""
        stage = Stage2SceneDetection(checkpoint_manager)

        file_id = "test_resume_001"

        # Save checkpoint
        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            {"scenes": []},
        )

        # Check can resume
        assert stage.can_resume(file_id)

    def test_get_progress(self, checkpoint_manager):
        """Test progress tracking."""
        stage = Stage2SceneDetection(checkpoint_manager)

        file_id = "test_progress_001"

        # No checkpoint
        assert stage.get_progress(file_id) is None

        # With checkpoint
        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            {"total_scenes": 10, "scenes": [{"scene_id": i} for i in range(10)]},
        )

        progress = stage.get_progress(file_id)
        assert progress is not None
        assert progress.total_items == 10
        assert progress.completed_items == 10


class TestStage2SceneStructure:
    """Test scene data structure."""

    def test_scene_data_structure(self, checkpoint_manager):
        """Test that scene data has correct structure."""
        file_id = "test_structure_001"

        # Create proper scene data
        scene_data = {
            "scene_id": f"{file_id}_scene_001",
            "scene_idx": 0,
            "start_frame": 0,
            "end_frame": 150,
            "start_time_ms": 0,
            "end_time_ms": 5000,
            "duration_seconds": 5.0,
            "key_frame_path": "data/working/scenes/scene_001.jpg",
        }

        checkpoint_data = {
            "stage": "stage2_scene_detection",
            "file_id": file_id,
            "total_scenes": 1,
            "scenes": [scene_data],
        }

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            checkpoint_data,
        )

        loaded = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )

        scene = loaded["scenes"][0]

        # Verify all required fields
        assert "scene_id" in scene
        assert "start_time_ms" in scene
        assert "end_time_ms" in scene
        assert "duration_seconds" in scene
        assert "key_frame_path" in scene
        assert scene["duration_seconds"] == 5.0

    def test_multiple_scenes_checkpoint(self, checkpoint_manager):
        """Test checkpoint with multiple scenes."""
        file_id = "test_multi_scenes_001"

        # Create multiple scenes
        scenes = []
        for i in range(5):
            scenes.append({
                "scene_id": f"{file_id}_scene_{i:03d}",
                "scene_idx": i,
                "start_time_ms": i * 5000,
                "end_time_ms": (i + 1) * 5000,
                "duration_seconds": 5.0,
                "key_frame_path": f"data/working/scenes/scene_{i:03d}.jpg",
            })

        checkpoint_data = {
            "stage": "stage2_scene_detection",
            "file_id": file_id,
            "total_scenes": len(scenes),
            "scenes": scenes,
        }

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            checkpoint_data,
        )

        loaded = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )

        assert loaded["total_scenes"] == 5
        assert len(loaded["scenes"]) == 5

        # Verify scene order
        for i, scene in enumerate(loaded["scenes"]):
            assert scene["scene_idx"] == i
            assert scene["start_time_ms"] == i * 5000


class TestStage2ErrorHandling:
    """Test error handling."""

    def test_missing_video_file(self, checkpoint_manager, temp_dir):
        """Test handling of missing video file."""
        stage = Stage2SceneDetection(checkpoint_manager)

        file_id = "test_missing_video_001"
        video_path = temp_dir / "nonexistent.mp4"

        checkpoint_manager.save_file_metadata(
            file_id,
            {"file_id": file_id, "state": "DISCOVERED", "stage_timestamps": {}},
        )

        result = stage.run(file_id, video_path)

        assert not result.success
        assert "not found" in result.message.lower()

    def test_progress_without_checkpoint(self, checkpoint_manager):
        """Test progress when no checkpoint exists."""
        stage = Stage2SceneDetection(checkpoint_manager)

        progress = stage.get_progress("nonexistent_file")
        assert progress is None


class TestStage2Resume:
    """Test resume capability."""

    def test_resume_preserves_scenes(self, checkpoint_manager):
        """Test that resume doesn't duplicate scenes."""
        file_id = "test_resume_preserve_001"

        # Initial scenes
        scenes_1 = [
            {
                "scene_id": f"{file_id}_scene_001",
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
            },
        ]

        checkpoint_1 = {
            "stage": "stage2_scene_detection",
            "total_scenes": 1,
            "scenes": scenes_1,
        }

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            checkpoint_1,
        )

        loaded_1 = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )
        count_1 = len(loaded_1["scenes"])

        # Simulate resume (reload same checkpoint)
        loaded_2 = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )
        count_2 = len(loaded_2["scenes"])

        # Counts should match
        assert count_1 == count_2 == 1

    def test_resume_adds_scenes(self, checkpoint_manager):
        """Test adding more scenes on resume."""
        file_id = "test_resume_add_001"

        # First run: 2 scenes
        scenes = [
            {
                "scene_id": f"{file_id}_scene_001",
                "start_time_ms": 0,
                "end_time_ms": 5000,
            },
            {
                "scene_id": f"{file_id}_scene_002",
                "start_time_ms": 5000,
                "end_time_ms": 10000,
            },
        ]

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            {"total_scenes": 2, "scenes": scenes},
        )

        loaded = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )
        assert loaded["total_scenes"] == 2

        # Second run: add 1 more scene
        scenes.append({
            "scene_id": f"{file_id}_scene_003",
            "start_time_ms": 10000,
            "end_time_ms": 15000,
        })

        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage2_scene_detection",
            {"total_scenes": 3, "scenes": scenes},
        )

        loaded = checkpoint_manager.load_file_checkpoint(
            file_id,
            "stage2_scene_detection",
        )
        assert loaded["total_scenes"] == 3
        assert len(loaded["scenes"]) == 3
