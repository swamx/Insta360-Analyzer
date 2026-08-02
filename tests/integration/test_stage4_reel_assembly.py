"""Integration tests for Stage 4: Reel Assembly."""

import pytest
import json

from src.stages.stage4_reel_assembly import Stage4ReelAssembly
from src.utils.logger import get_logger


logger = get_logger("test_stage4_reel_assembly")


class TestStage4ReelAssembly:
    """Test reel assembly."""

    def test_assemble_reel_basic(self, checkpoint_manager):
        """Test basic reel assembly."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_reel_001"

        # Create scored scenes
        scored_scenes = [
            {
                "scene_id": f"scene_{i:03d}",
                "overall_score": 9.0 - (i * 0.5),
                "start_time_ms": i * 5000,
                "end_time_ms": (i + 1) * 5000,
                "duration_seconds": 5.0,
                "is_usable": True,
            }
            for i in range(10)
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)

        assert result.success
        assert result.data["clip_count"] > 0
        assert result.data["total_duration"] <= 15.1

    def test_reel_duration_limit(self, checkpoint_manager):
        """Test that reel respects 15-second limit."""
        stage = Stage4ReelAssembly(checkpoint_manager, max_duration_seconds=15.0, skip_model_load=True)

        file_id = "test_duration_001"

        # Create long scenes
        scored_scenes = [
            {
                "scene_id": f"scene_{i:03d}",
                "overall_score": 9.0,
                "start_time_ms": i * 10000,
                "end_time_ms": (i + 1) * 10000,
                "duration_seconds": 10.0,
                "is_usable": True,
            }
            for i in range(5)
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)

        assert result.success

        # Load and check duration
        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
        duration = cp.get("total_duration_seconds", 0)

        assert duration <= 15.1  # Allow small tolerance

    def test_reel_plan_structure(self, checkpoint_manager):
        """Test reel plan has correct structure."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_structure_001"

        scored_scenes = [
            {
                "scene_id": "scene_001",
                "overall_score": 9.0,
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
            {
                "scene_id": "scene_002",
                "overall_score": 8.5,
                "start_time_ms": 5000,
                "end_time_ms": 10000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)
        assert result.success

        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
        reel_plan = cp.get("reel_plan", {})

        # Verify structure
        assert "total_duration" in reel_plan
        assert "clips" in reel_plan
        assert "reasoning" in reel_plan

        # Verify clips structure
        for clip in reel_plan["clips"]:
            assert "scene_id" in clip
            assert "start_ms" in clip
            assert "end_ms" in clip
            assert "clip_duration" in clip

    def test_clips_ordered_by_score(self, checkpoint_manager):
        """Test that clips are selected from highest-scored scenes."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_score_order_001"

        # Create scenes with different scores
        scored_scenes = [
            {
                "scene_id": "scene_low",
                "overall_score": 3.0,
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
            {
                "scene_id": "scene_high",
                "overall_score": 9.5,
                "start_time_ms": 5000,
                "end_time_ms": 10000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
            {
                "scene_id": "scene_mid",
                "overall_score": 6.0,
                "start_time_ms": 10000,
                "end_time_ms": 15000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)
        assert result.success

        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
        reel_plan = cp.get("reel_plan", {})
        clips = reel_plan.get("clips", [])

        # Highest scored scene should be first
        if len(clips) > 0:
            first_scene = clips[0]["scene_id"]
            assert first_scene == "scene_high"

    def test_no_usable_scenes(self, checkpoint_manager):
        """Test handling of no usable scenes."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_no_usable_001"

        # All scenes marked unusable
        scored_scenes = [
            {
                "scene_id": "scene_001",
                "overall_score": 9.0,
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
                "is_usable": False,
            },
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)

        assert not result.success
        assert "no usable" in result.message.lower()

    def test_empty_scenes(self, checkpoint_manager):
        """Test handling of empty scene list."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_empty_001"

        checkpoint = {"scored_scenes": []}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)

        assert not result.success
        assert "no scored scenes" in result.message.lower()

    def test_reel_checkpoint_saved(self, checkpoint_manager):
        """Test that reel checkpoint is properly saved."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_checkpoint_reel_001"

        scored_scenes = [
            {
                "scene_id": "scene_001",
                "overall_score": 9.0,
                "start_time_ms": 0,
                "end_time_ms": 5000,
                "duration_seconds": 5.0,
                "is_usable": True,
            },
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)
        assert result.success

        # Verify checkpoint exists and has correct structure
        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")

        assert "reel_plan" in cp
        assert "total_duration_seconds" in cp
        assert "clips_selected" in cp
        assert "timestamp" in cp


class TestStage4ClipDurations:
    """Test clip duration calculations."""

    def test_clip_duration_calculation(self, checkpoint_manager):
        """Test that clip durations are calculated correctly."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_duration_calc_001"

        scored_scenes = [
            {
                "scene_id": "scene_001",
                "overall_score": 9.0,
                "start_time_ms": 1000,
                "end_time_ms": 8000,
                "duration_seconds": 7.0,
                "is_usable": True,
            },
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)
        assert result.success

        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
        clips = cp.get("reel_plan", {}).get("clips", [])

        if len(clips) > 0:
            clip = clips[0]
            # Clip should be trimmed to max 3 seconds
            assert clip["clip_duration"] <= 3.0
            # Start and end should be valid
            assert clip["end_ms"] > clip["start_ms"]

    def test_total_duration_sums_clips(self, checkpoint_manager):
        """Test that total duration is sum of clip durations."""
        stage = Stage4ReelAssembly(checkpoint_manager, skip_model_load=True)

        file_id = "test_duration_sum_001"

        scored_scenes = [
            {
                "scene_id": f"scene_{i:03d}",
                "overall_score": 9.0 - (i * 0.1),
                "start_time_ms": i * 5000,
                "end_time_ms": (i + 1) * 5000,
                "duration_seconds": 5.0,
                "is_usable": True,
            }
            for i in range(6)
        ]

        checkpoint = {"scored_scenes": scored_scenes}

        checkpoint_manager.save_file_metadata(
            file_id,
            {
                "file_id": file_id,
                "state": "ANALYZED",
                "stage_timestamps": {},
            },
        )

        result = stage.run(file_id, checkpoint)
        assert result.success

        cp = checkpoint_manager.load_file_checkpoint(file_id, "stage4_reel_assembly")
        reel_plan = cp.get("reel_plan", {})
        total_duration = reel_plan.get("total_duration", 0)
        clips = reel_plan.get("clips", [])

        # Sum individual clip durations
        clip_sum = sum(clip.get("clip_duration", 0) for clip in clips)

        # Should match total duration (within rounding)
        assert abs(total_duration - clip_sum) < 0.1
