"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import json
from pathlib import Path
import numpy as np
from PIL import Image

from src.storage.checkpoint_manager import CheckpointManager
from src.pipeline import Pipeline


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def checkpoint_dir(temp_dir):
    """Create a checkpoint directory."""
    cp_dir = temp_dir / "checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    return cp_dir


@pytest.fixture
def checkpoint_manager(checkpoint_dir):
    """Create a checkpoint manager."""
    return CheckpointManager(checkpoint_dir)


@pytest.fixture
def data_dir(temp_dir):
    """Create a data directory structure."""
    data = temp_dir / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "input").mkdir(parents=True, exist_ok=True)
    (data / "output").mkdir(parents=True, exist_ok=True)
    (data / "working").mkdir(parents=True, exist_ok=True)
    (data / "models").mkdir(parents=True, exist_ok=True)
    return data


@pytest.fixture
def pipeline(checkpoint_dir, data_dir):
    """Create a pipeline instance."""
    return Pipeline(checkpoint_dir, data_dir)


@pytest.fixture
def test_frames(temp_dir):
    """Create test frame images (100 frames, 256x256)."""
    frames_dir = temp_dir / "test_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for i in range(100):
        # Create a simple test image with varying patterns
        img_array = np.zeros((256, 256, 3), dtype=np.uint8)
        # Add some pattern that changes per frame
        img_array[:, :, 0] = (i * 2) % 256  # Red channel varies
        img_array[:, :, 1] = (i * 3) % 256  # Green channel varies
        img_array[i % 256, :, 2] = 255       # Blue line moves

        img = Image.fromarray(img_array)
        frame_path = frames_dir / f"frame_{i:06d}.jpg"
        img.save(frame_path, quality=85)
        frames.append(frame_path)

    return frames_dir, frames


@pytest.fixture
def test_embeddings():
    """Create mock embeddings (1024-dim vectors)."""
    return np.random.randn(100, 1024).astype(np.float32)


@pytest.fixture
def test_metadata():
    """Create test file metadata."""
    return {
        "file_id": "test_file_001",
        "source_path": "/tmp/test_video.mp4",
        "state": "DISCOVERED",
        "file_type": "video",
        "file_size_gb": 2.5,
        "duration_seconds": 100.0,
        "frame_count": 100,
        "stage_timestamps": {
            "DISCOVERED": "2024-08-02T10:00:00Z",
            "FRAMES_EXTRACTED": "2024-08-02T10:05:00Z",
        },
    }
