"""Atomic checkpoint save/load operations with integrity checking."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.errors import CheckpointError


logger = get_logger("checkpoint_manager")


class CheckpointManager:
    """Manages atomic checkpoint operations."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.checkpoint_dir / "manifest.json"
        self.file_manifest_path = self.checkpoint_dir / "file_manifest.json"

    def atomic_save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Save JSON data atomically using temp file + rename pattern."""
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp_path = tmp.name

        try:
            # Atomic rename (works on Windows NTFS)
            os.replace(tmp_path, path)
            logger.debug(f"Saved checkpoint: {path}")
        except Exception as e:
            # Clean up temp file if rename failed
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise CheckpointError(
                f"Failed to save checkpoint {path}: {str(e)}",
            )

    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON checkpoint, with corruption detection."""
        if not path.exists():
            raise CheckpointError(f"Checkpoint does not exist: {path}")

        try:
            with open(path, "r") as f:
                data = json.load(f)
            logger.debug(f"Loaded checkpoint: {path}")
            return data
        except json.JSONDecodeError as e:
            raise CheckpointError(
                f"Corrupted checkpoint (invalid JSON) at {path}: {str(e)}",
            )
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint {path}: {str(e)}")

    def save_file_checkpoint(
        self,
        file_id: str,
        stage: str,
        data: Dict[str, Any],
    ) -> None:
        """Save checkpoint for a specific file and stage."""
        checkpoint_path = (
            self.checkpoint_dir
            / file_id
            / f"{stage}"
            / "checkpoint.json"
        )
        self.atomic_save_json(checkpoint_path, data)

    def load_file_checkpoint(
        self,
        file_id: str,
        stage: str,
    ) -> Dict[str, Any]:
        """Load checkpoint for a specific file and stage."""
        checkpoint_path = (
            self.checkpoint_dir
            / file_id
            / f"{stage}"
            / "checkpoint.json"
        )
        return self.load_json(checkpoint_path)

    def checkpoint_exists(
        self,
        file_id: str,
        stage: str,
    ) -> bool:
        """Check if checkpoint exists for file and stage."""
        checkpoint_path = (
            self.checkpoint_dir
            / file_id
            / f"{stage}"
            / "checkpoint.json"
        )
        return checkpoint_path.exists()

    def save_manifest(self, data: Dict[str, Any]) -> None:
        """Save global manifest."""
        data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.atomic_save_json(self.manifest_path, data)

    def load_manifest(self) -> Dict[str, Any]:
        """Load global manifest."""
        if not self.manifest_path.exists():
            return {
                "version": "1.0",
                "total_files": 0,
                "completed_files": 0,
                "failed_files": 0,
            }
        return self.load_json(self.manifest_path)

    def save_file_metadata(
        self,
        file_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Save file-level metadata."""
        metadata_path = self.checkpoint_dir / file_id / "metadata.json"
        self.atomic_save_json(metadata_path, metadata)

    def load_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Load file-level metadata."""
        metadata_path = self.checkpoint_dir / file_id / "metadata.json"
        if not metadata_path.exists():
            return None
        return self.load_json(metadata_path)

    def list_all_files(self) -> list:
        """List all file_ids with checkpoints."""
        if not self.checkpoint_dir.exists():
            return []

        file_ids = []
        for item in self.checkpoint_dir.iterdir():
            if item.is_dir() and item.name not in ["manifest.json", "file_manifest.json"]:
                file_ids.append(item.name)
        return sorted(file_ids)

    def get_file_state(self, file_id: str) -> str:
        """Get current state of file (DISCOVERED, FRAMES_EXTRACTED, etc)."""
        metadata = self.load_file_metadata(file_id)
        if not metadata:
            return None
        return metadata.get("state")

    def get_last_complete_stage(self, file_id: str) -> Optional[int]:
        """Determine the last successfully completed stage (0-5)."""
        stages = [
            "stage1_discovery",
            "stage2_extraction",
            "stage3_analysis",
            "stage4_highlights",
            "stage5_encoding",
        ]

        last_complete = -1
        for idx, stage in enumerate(stages):
            if self.checkpoint_exists(file_id, stage):
                last_complete = idx

        return last_complete if last_complete >= 0 else None
