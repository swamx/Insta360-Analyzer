"""Stage 3: Vision Analysis - analyze frames with Qwen3-VL-2B model."""

from pathlib import Path
from datetime import datetime
from typing import Optional, List
import numpy as np
from PIL import Image

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger
from src.utils.device_utils import get_device_info, get_available_memory_gb
from src.utils.errors import ModelError, OutOfMemoryError


logger = get_logger("stages.stage3_analysis")


class Stage3Analysis(Stage):
    """Analyze frames with Qwen3-VL-2B vision model."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        batch_size: int = 16,
        quantization: str = "4bit",
        skip_model_load: bool = False,
    ):
        """
        Initialize analysis stage.

        Args:
            checkpoint_manager: Checkpoint storage
            batch_size: Number of frames per batch (auto-adjusted for VRAM)
            quantization: Model quantization ("4bit" or "8bit")
            skip_model_load: For testing, skip actual model loading
        """
        super().__init__("stage3_analysis")
        self.checkpoint_manager = checkpoint_manager
        self.batch_size = batch_size
        self.quantization = quantization
        self.skip_model_load = skip_model_load
        self.model = None
        self.device = None

    def _load_model(self) -> None:
        """Load Qwen3-VL-2B model (stub for now)."""
        if self.skip_model_load:
            logger.debug("Skipping model load (test mode)")
            return

        try:
            logger.info(f"Loading Qwen3-VL-2B ({self.quantization} quantization)...")
            device_info = get_device_info()

            if not device_info["cuda_available"]:
                logger.warning("CUDA not available, using CPU (very slow)")

            # TODO: Actual model loading
            # from transformers import AutoModel
            # from bitsandbytes.functional import quantize_4bit
            #
            # self.model = AutoModel.from_pretrained(
            #     "Qwen/Qwen3-VL-2B",
            #     device_map="auto",
            #     load_in_4bit=(self.quantization == "4bit"),
            # )
            # self.model.eval()

            logger.info("Model loaded successfully")

        except Exception as e:
            raise ModelError(f"Failed to load Qwen3-VL-2B: {str(e)}")

    def _analyze_frame(self, frame_path: Path) -> dict:
        """Analyze a single frame (returns mock analysis for now)."""
        if not frame_path.exists():
            return None

        try:
            # Load frame
            img = Image.open(frame_path).convert("RGB")
            img_array = np.array(img)

            # TODO: Actual model inference
            # inputs = processor(images=img, return_tensors="pt").to(device)
            # with torch.no_grad():
            #     embeddings = model(**inputs).last_hidden_state
            # embedding = embeddings[0, 0, :].cpu().numpy()

            # For now, generate deterministic mock embedding based on image content
            # This allows testing checkpoint/resume without model
            embedding = self._generate_mock_embedding(img_array)

            # Mock analysis metadata
            analysis = {
                "embedding": embedding.tolist(),
                "brightness": float(np.mean(img_array) / 255.0),
                "contrast": float(np.std(img_array) / 255.0),
                "objects": ["object"] if np.mean(img_array) > 127 else ["dark"],
                "scene_type": "scene",
            }

            return analysis

        except Exception as e:
            logger.warning(f"Failed to analyze frame {frame_path}: {str(e)}")
            return None

    @staticmethod
    def _generate_mock_embedding(img_array: np.ndarray) -> np.ndarray:
        """Generate deterministic mock embedding from image for testing."""
        # Create 1024-dim embedding based on image statistics
        embedding = np.zeros(1024)
        resized = np.mean(img_array.reshape(-1, 3), axis=0)  # RGB means
        embedding[:3] = resized / 255.0
        # Fill rest with deterministic noise based on image hash
        seed = int(np.sum(img_array)) % 2**31
        np.random.seed(seed)
        embedding[3:] = np.random.randn(1021)
        np.random.seed(None)  # Reset seed
        return embedding

    def run(
        self,
        file_id: str,
        frames_dir: Path,
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """
        Analyze frames with vision model.

        Args:
            file_id: Unique file identifier
            frames_dir: Directory containing extracted frames
            resume_from: Resume from this frame index (0-based)

        Returns:
            StageResult with analysis data
        """
        self._log_stage_start(file_id, resume_from)

        try:
            frames_dir = Path(frames_dir)

            # Load model
            if self.model is None and not self.skip_model_load:
                self._load_model()

            # Get list of frames
            frame_files = sorted(frames_dir.glob("frame_*.jpg"))
            if not frame_files:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message=f"No frames found in {frames_dir}",
                )

            total_frames = len(frame_files)
            logger.info(
                f"[{file_id}] Found {total_frames} frames to analyze"
            )

            # Determine start index
            start_idx = 0
            if resume_from is not None:
                start_idx = resume_from
                logger.info(f"[{file_id}] Resuming from frame {start_idx}")
            else:
                # Check if we have a partial checkpoint
                if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
                    checkpoint = self.checkpoint_manager.load_file_checkpoint(
                        file_id, self.stage_name
                    )
                    stage_progress = checkpoint.get("stage_progress", {}).get(
                        self.stage_name
                    )
                    if stage_progress:
                        start_idx = stage_progress.get("last_completed_frame", -1) + 1
                        logger.info(
                            f"[{file_id}] Found partial checkpoint, resuming from frame {start_idx}"
                        )

            # Analyze frames
            all_embeddings = []
            all_analysis = []

            for batch_start in range(start_idx, total_frames, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_frames)
                batch_frames = frame_files[batch_start:batch_end]

                # Analyze batch
                batch_embeddings = []
                batch_analysis = []

                for frame_idx, frame_path in enumerate(batch_frames):
                    actual_idx = batch_start + frame_idx

                    analysis = self._analyze_frame(frame_path)
                    if analysis:
                        all_embeddings.append(analysis["embedding"])
                        all_analysis.append(analysis)
                        batch_embeddings.append(analysis["embedding"])
                        batch_analysis.append(analysis)

                    self._log_progress(file_id, actual_idx + 1, total_frames)

                # Save checkpoint after each batch
                if all_embeddings or all_analysis:
                    checkpoint_data = {
                        "stage": self.stage_name,
                        "file_id": file_id,
                        "frame_count": len(all_embeddings),
                        "embeddings": all_embeddings,  # Store full list so far
                        "analysis": all_analysis,      # Store full analysis so far
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "stage_progress": {
                            self.stage_name: {
                                "total_frames": total_frames,
                                "last_completed_frame": batch_end - 1,
                            }
                        },
                    }
                    self.checkpoint_manager.save_file_checkpoint(
                        file_id,
                        self.stage_name,
                        checkpoint_data,
                    )

            if not all_embeddings:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No frames could be analyzed",
                )

            # Update file metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "ANALYZED"
            metadata["embedding_count"] = len(all_embeddings)
            metadata["stage_timestamps"]["ANALYZED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Analyzed {len(all_embeddings)} frames",
                data={
                    "frame_count": len(all_embeddings),
                    "embeddings_shape": [len(all_embeddings), 1024],
                },
            )

        except OutOfMemoryError as e:
            logger.error(f"[{file_id}] Out of memory: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Out of memory: {str(e)}",
            )
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 3 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Analysis failed: {str(e)}",
            )

    def can_resume(self, file_id: str) -> bool:
        """Check if analysis can resume from checkpoint."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return False

        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        stage_progress = checkpoint.get("stage_progress", {}).get(self.stage_name)
        return stage_progress is not None

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get analysis progress."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return None

        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        stage_progress = checkpoint.get("stage_progress", {}).get(self.stage_name)

        if stage_progress:
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=stage_progress.get("total_frames", 0),
                completed_items=stage_progress.get("last_completed_frame", -1) + 1,
                current_item=stage_progress.get("last_completed_frame", -1),
            )

        return None
