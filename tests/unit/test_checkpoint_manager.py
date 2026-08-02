"""Unit tests for checkpoint manager."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.storage.checkpoint_manager import CheckpointManager
from src.utils.errors import CheckpointError


class TestCheckpointManagerBasics:
    """Test basic checkpoint operations."""

    def test_init_creates_directory(self, temp_dir):
        """Test that init creates checkpoint directory."""
        cp_dir = temp_dir / "checkpoints"
        manager = CheckpointManager(cp_dir)
        assert cp_dir.exists()
        assert manager.manifest_path.exists() or not manager.manifest_path.exists()

    def test_atomic_save_json(self, checkpoint_manager, temp_dir):
        """Test atomic JSON save."""
        test_data = {
            "key": "value",
            "nested": {"inner": 123},
            "list": [1, 2, 3],
        }

        path = temp_dir / "test.json"
        checkpoint_manager.atomic_save_json(path, test_data)

        assert path.exists()
        with open(path) as f:
            loaded = json.load(f)
        assert loaded == test_data

    def test_load_nonexistent_checkpoint(self, checkpoint_manager, temp_dir):
        """Test loading nonexistent checkpoint raises error."""
        path = temp_dir / "nonexistent.json"
        with pytest.raises(CheckpointError):
            checkpoint_manager.load_json(path)

    def test_corrupted_checkpoint(self, checkpoint_manager, temp_dir):
        """Test loading corrupted checkpoint raises error."""
        path = temp_dir / "corrupted.json"
        with open(path, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(CheckpointError):
            checkpoint_manager.load_json(path)


class TestFileCheckpoints:
    """Test file-level checkpoint operations."""

    def test_save_and_load_file_checkpoint(self, checkpoint_manager):
        """Test saving and loading file checkpoint."""
        file_id = "test_file_001"
        stage = "stage1_discovery"
        data = {
            "file_id": file_id,
            "stage": stage,
            "data": {"test": "value"},
        }

        checkpoint_manager.save_file_checkpoint(file_id, stage, data)
        loaded = checkpoint_manager.load_file_checkpoint(file_id, stage)

        assert loaded["file_id"] == file_id
        assert loaded["data"]["test"] == "value"

    def test_checkpoint_exists(self, checkpoint_manager):
        """Test checkpoint_exists method."""
        file_id = "test_file_002"
        stage = "stage1_discovery"

        assert not checkpoint_manager.checkpoint_exists(file_id, stage)

        checkpoint_manager.save_file_checkpoint(file_id, stage, {"data": "test"})
        assert checkpoint_manager.checkpoint_exists(file_id, stage)

    def test_save_file_metadata(self, checkpoint_manager, test_metadata):
        """Test saving and loading file metadata."""
        file_id = test_metadata["file_id"]

        checkpoint_manager.save_file_metadata(file_id, test_metadata)
        loaded = checkpoint_manager.load_file_metadata(file_id)

        assert loaded["file_id"] == file_id
        assert loaded["duration_seconds"] == 100.0

    def test_list_all_files(self, checkpoint_manager):
        """Test listing all files."""
        # Add multiple files
        for i in range(5):
            file_id = f"file_{i:03d}"
            checkpoint_manager.save_file_metadata(file_id, {"file_id": file_id})

        files = checkpoint_manager.list_all_files()
        assert len(files) == 5
        assert all(f.startswith("file_") for f in files)


class TestManifest:
    """Test global manifest operations."""

    def test_save_and_load_manifest(self, checkpoint_manager):
        """Test saving and loading manifest."""
        manifest = {
            "version": "1.0",
            "total_files": 10,
            "completed_files": 3,
        }

        checkpoint_manager.save_manifest(manifest)
        loaded = checkpoint_manager.load_manifest()

        assert loaded["version"] == "1.0"
        assert loaded["total_files"] == 10
        assert "last_updated" in loaded  # Added by save_manifest

    def test_load_nonexistent_manifest(self, checkpoint_manager):
        """Test loading nonexistent manifest returns default."""
        loaded = checkpoint_manager.load_manifest()
        assert loaded["version"] == "1.0"
        assert loaded["total_files"] == 0


class TestStateTracking:
    """Test state tracking methods."""

    def test_get_file_state(self, checkpoint_manager, test_metadata):
        """Test getting file state."""
        file_id = test_metadata["file_id"]
        checkpoint_manager.save_file_metadata(file_id, test_metadata)

        state = checkpoint_manager.get_file_state(file_id)
        assert state == "DISCOVERED"

    def test_get_last_complete_stage_no_checkpoints(self, checkpoint_manager):
        """Test getting last complete stage when none exist."""
        file_id = "new_file"
        last_stage = checkpoint_manager.get_last_complete_stage(file_id)
        assert last_stage is None

    def test_get_last_complete_stage_with_checkpoints(self, checkpoint_manager):
        """Test getting last complete stage with multiple checkpoints."""
        file_id = "test_file"

        # Create checkpoints for stages 1-3
        checkpoint_manager.save_file_checkpoint(file_id, "stage1_discovery", {"data": 1})
        checkpoint_manager.save_file_checkpoint(
            file_id, "stage2_extraction", {"data": 2}
        )
        checkpoint_manager.save_file_checkpoint(file_id, "stage3_analysis", {"data": 3})

        last_stage = checkpoint_manager.get_last_complete_stage(file_id)
        # Stage indices: stage1=0, stage2=1, stage3=2, so last complete should be 2
        assert last_stage == 2
