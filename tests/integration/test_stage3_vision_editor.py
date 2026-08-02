"""Integration tests for Stage 3: Vision Editor."""

import pytest
import json
from datetime import datetime

from src.stages.stage3_vision_editor import Stage3VisionEditor
from src.utils.logger import get_logger


logger = get_logger("test_stage3_vision_editor")


class TestStage3BasicScoring:
    """Test basic scene scoring."""

    def test_score_single_scene(self, checkpoint_manager):
        """Test scoring a single scene."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_score_001"
        scene = {
            "scene_id": "scene_001",
            "scene_idx": 0,
            "start_time_ms": 0,
            "end_time_ms": 5000,
            "duration_seconds": 5.0,
            "key_frame_path": "data/working/scenes/scene_001.jpg",
        }

        scenes_checkpoint = {"scenes": [scene]}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)

        assert result.success
        assert result.data["scored_scenes"] == 1

    def test_score_multiple_scenes(self, checkpoint_manager):
        """Test scoring multiple scenes."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_score_multi_001"

        scenes = []
        for i in range(5):
            scenes.append({
                "scene_id": f"scene_{i:03d}",
                "scene_idx": i,
                "start_time_ms": i * 5000,
                "end_time_ms": (i + 1) * 5000,
                "duration_seconds": 5.0,
                "key_frame_path": f"data/working/scenes/scene_{i:03d}.jpg",
            })

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)

        assert result.success
        assert result.data["scored_scenes"] == 5

    def test_scene_scoring_structure(self, checkpoint_manager):
        """Test that scene scores have correct structure."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_score_struct_001"

        # Create scene with scoring
        scene = {
            "scene_id": "scene_001",
            "scene_idx": 0,
            "start_time_ms": 0,
            "end_time_ms": 5000,
        }

        scenes_checkpoint = {"scenes": [scene]}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        # Load checkpoint
        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        scored_scenes = checkpoint.get("scored_scenes", [])

        assert len(scored_scenes) > 0
        scored_scene = scored_scenes[0]

        # Verify scoring fields
        assert "scenic_beauty" in scored_scene
        assert "action" in scored_scene
        assert "emotion" in scored_scene
        assert "stability" in scored_scene
        assert "blurriness" in scored_scene
        assert "overall_score" in scored_scene
        assert "is_usable" in scored_scene
        assert "brief_description" in scored_scene


class TestStage3Scoring:
    """Test scene scoring logic."""

    def test_score_values_in_range(self, checkpoint_manager):
        """Test that scores are in valid range (1-10)."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_score_range_001"

        scenes = []
        for i in range(10):
            scenes.append({
                "scene_id": f"scene_{i:03d}",
                "scene_idx": i,
                "start_time_ms": i * 5000,
                "end_time_ms": (i + 1) * 5000,
            })

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        scored_scenes = checkpoint.get("scored_scenes", [])

        for scene in scored_scenes:
            assert 1 <= scene["scenic_beauty"] <= 10
            assert 1 <= scene["action"] <= 10
            assert 1 <= scene["emotion"] <= 10
            assert 1 <= scene["stability"] <= 10
            assert 1 <= scene["blurriness"] <= 10
            assert 0 <= scene["overall_score"] <= 10

    def test_overall_score_calculation(self, checkpoint_manager):
        """Test that overall score is calculated."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_overall_score_001"

        scene = {
            "scene_id": "scene_001",
            "scene_idx": 2,
            "start_time_ms": 0,
            "end_time_ms": 5000,
        }

        scenes_checkpoint = {"scenes": [scene]}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        scored_scene = checkpoint.get("scored_scenes", [{}])[0]

        # Overall score should be calculated
        assert "overall_score" in scored_scene
        assert scored_scene["overall_score"] > 0

    def test_all_scenes_usable(self, checkpoint_manager):
        """Test that all scenes are marked usable (in test mode)."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_usable_001"

        scenes = [
            {"scene_id": f"scene_{i:03d}", "scene_idx": i, "start_time_ms": i * 5000}
            for i in range(5)
        ]

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        scored_scenes = checkpoint.get("scored_scenes", [])

        for scene in scored_scenes:
            assert scene["is_usable"] is True


class TestStage3Checkpoint:
    """Test checkpointing and resume."""

    def test_checkpoint_saves_all_scores(self, checkpoint_manager):
        """Test that checkpoint saves all scene scores."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_checkpoint_all_001"

        scenes = [
            {"scene_id": f"scene_{i:03d}", "scene_idx": i, "start_time_ms": i * 5000}
            for i in range(3)
        ]

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        # Load checkpoint
        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")

        assert checkpoint["total_scenes"] == 3
        assert len(checkpoint["scored_scenes"]) == 3

    def test_can_resume_after_scoring(self, checkpoint_manager):
        """Test resume capability."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_resume_scoring_001"

        scenes = [
            {"scene_id": "scene_001", "scene_idx": 0, "start_time_ms": 0},
            {"scene_id": "scene_002", "scene_idx": 1, "start_time_ms": 5000},
        ]

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)
        assert result.success

        # Check resume capability
        assert stage.can_resume(file_id)

    def test_resume_without_duplication(self, checkpoint_manager):
        """Test that resume doesn't duplicate scores."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_no_dup_001"

        scenes = [
            {"scene_id": "scene_001", "scene_idx": 0, "start_time_ms": 0},
            {"scene_id": "scene_002", "scene_idx": 1, "start_time_ms": 5000},
            {"scene_id": "scene_003", "scene_idx": 2, "start_time_ms": 10000},
        ]

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        # First run
        result1 = stage.run(file_id, scenes_checkpoint)
        assert result1.success

        checkpoint1 = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        count1 = len(checkpoint1.get("scored_scenes", []))

        # Second run (resume)
        result2 = stage.run(file_id, scenes_checkpoint)
        assert result2.success

        checkpoint2 = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        count2 = len(checkpoint2.get("scored_scenes", []))

        # Should be same count (no duplication)
        assert count1 == count2 == 3

    def test_resume_from_partial(self, checkpoint_manager):
        """Test resuming from partial completion."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_partial_001"

        scenes = [
            {"scene_id": f"scene_{i:03d}", "scene_idx": i, "start_time_ms": i * 5000}
            for i in range(5)
        ]

        scenes_checkpoint = {"scenes": scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        # Run with resume from frame 2
        result = stage.run(file_id, scenes_checkpoint, resume_from=2)
        assert result.success

        checkpoint = checkpoint_manager.load_file_checkpoint(file_id, "stage3_vision_editor")
        scored_scenes = checkpoint.get("scored_scenes", [])

        # Should have scenes starting from index 2
        assert len(scored_scenes) >= 3


class TestStage3Progress:
    """Test progress tracking."""

    def test_get_progress_no_checkpoint(self, checkpoint_manager):
        """Test progress when no checkpoint exists."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        progress = stage.get_progress("nonexistent_file")
        assert progress is None

    def test_get_progress_with_checkpoint(self, checkpoint_manager):
        """Test progress with checkpoint."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_progress_001"

        # Create checkpoint
        checkpoint_manager.save_file_checkpoint(
            file_id,
            "stage3_vision_editor",
            {
                "total_scenes": 10,
                "scored_scenes": [{"score": i} for i in range(10)],
                "stage_progress": {
                    "stage3_vision_editor": {
                        "total_scenes": 10,
                        "scored_scenes": 10,
                    }
                },
            },
        )

        progress = stage.get_progress(file_id)
        assert progress is not None
        assert progress.total_items == 10
        assert progress.completed_items == 10


class TestStage3ErrorHandling:
    """Test error handling."""

    def test_no_scenes_to_analyze(self, checkpoint_manager):
        """Test handling of no scenes."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_no_scenes_001"
        scenes_checkpoint = {"scenes": []}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)

        assert not result.success
        assert "no scenes" in result.message.lower()

    def test_missing_scene_fields(self, checkpoint_manager):
        """Test handling of incomplete scene data."""
        stage = Stage3VisionEditor(checkpoint_manager, skip_model_load=True)

        file_id = "test_incomplete_scene_001"

        # Scene missing key_frame_path
        scene = {"scene_id": "scene_001", "scene_idx": 0}
        scenes_checkpoint = {"scenes": [scene]}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "SCENES_DETECTED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, scenes_checkpoint)

        # Should still succeed (use defaults)
        assert result.success
