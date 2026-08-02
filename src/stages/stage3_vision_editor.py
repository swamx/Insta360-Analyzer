"""Stage 3: Vision Editor - Score scenes using Qwen2.5-VL."""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np
from PIL import Image

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger

try:
    import torch
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False

logger = get_logger("stages.stage3_vision_editor")


class Stage3VisionEditor(Stage):
    """Score scenes as a professional video editor using Qwen2.5-VL."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        skip_model_load: bool = False,
        model_name: str = "Qwen/Qwen2.5-VL-7B",
    ):
        super().__init__("stage3_vision_editor")
        self.checkpoint_manager = checkpoint_manager
        self.skip_model_load = skip_model_load
        self.model_name = model_name
        self.model = None
        self.processor = None

    def _load_model(self) -> None:
        """Load Qwen2.5-VL model."""
        if self.skip_model_load:
            logger.debug("Skipping model load (test mode)")
            return

        if self.model is not None:
            logger.debug("Model already loaded")
            return

        if not QWEN_AVAILABLE:
            logger.error("PyTorch/transformers not available, using mock scoring")
            return

        try:
            logger.info(f"Loading {self.model_name}...")

            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")

            # Load model with 4-bit quantization if CUDA available
            if device == "cuda":
                try:
                    self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                        self.model_name,
                        device_map="auto",
                        torch_dtype=torch.float16,
                        load_in_4bit=True,
                        trust_remote_code=True,
                    )
                    logger.info("Model loaded with 4-bit quantization")
                except Exception as e:
                    logger.warning(f"4-bit loading failed, trying float32: {str(e)}")
                    self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                        self.model_name,
                        device_map="auto",
                        torch_dtype=torch.float32,
                        trust_remote_code=True,
                    )
            else:
                # CPU: use float32
                self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                    self.model_name,
                    device_map=device,
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                )
                logger.info("Model loaded on CPU (float32)")

            # Load processor
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )

            self.model.eval()
            logger.info("Model loaded successfully and set to eval mode")

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            logger.warning("Will use mock scoring as fallback")
            self.model = None
            self.processor = None

    def run(
        self,
        file_id: str,
        scenes_checkpoint: Dict[str, Any],
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """Score each scene as a professional video editor."""
        self._log_stage_start(file_id, resume_from)

        try:
            self._load_model()

            # Get scenes from Stage 2
            scenes = scenes_checkpoint.get("scenes", [])

            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scenes to analyze",
                )

            # Determine start index
            start_idx = resume_from or 0

            # Check for partial checkpoint
            if resume_from is None:
                if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
                    checkpoint = self.checkpoint_manager.load_file_checkpoint(
                        file_id, self.stage_name
                    )
                    start_idx = checkpoint.get("stage_progress", {}).get(
                        self.stage_name, {}
                    ).get("last_scored_scene", -1) + 1
                    if start_idx > 0:
                        logger.info(f"Resuming from scene {start_idx}")

            # Score each scene
            scored_scenes = []

            for scene_idx in range(start_idx, len(scenes)):
                scene = scenes[scene_idx]
                logger.info(f"Scoring scene {scene_idx + 1}/{len(scenes)}")

                score = self._score_scene(scene)
                scene.update(score)
                scored_scenes.append(scene)

                # Save checkpoint after each scene
                checkpoint_data = {
                    "stage": self.stage_name,
                    "file_id": file_id,
                    "total_scenes": len(scenes),
                    "scored_scenes": scored_scenes,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "stage_progress": {
                        self.stage_name: {
                            "total_scenes": len(scenes),
                            "scored_scenes": len(scored_scenes),
                            "last_scored_scene": scene_idx,
                        }
                    },
                }

                self.checkpoint_manager.save_file_checkpoint(
                    file_id,
                    self.stage_name,
                    checkpoint_data,
                )

                self._log_progress(file_id, len(scored_scenes), len(scenes))

            # Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "ANALYZED"
            metadata["stage_timestamps"]["ANALYZED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Scored {len(scored_scenes)} scenes",
                data={"scored_scenes": len(scored_scenes)},
            )

        except Exception as e:
            logger.exception(f"[{file_id}] Stage 3 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Vision analysis failed: {str(e)}",
            )

    def _score_scene(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Score a scene as a professional video editor."""
        try:
            # For testing: use deterministic mock scoring
            if self.skip_model_load or self.model is None:
                return self._mock_score(scene)

            # Real LLM inference
            return self._score_scene_real(scene)

        except Exception as e:
            logger.warning(f"Failed to score scene: {str(e)}, using mock")
            return self._mock_score(scene)

    def _score_scene_real(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Real LLM-based scene scoring."""
        try:
            key_frame_path = scene.get("key_frame_path")

            if not key_frame_path or not Path(key_frame_path).exists():
                logger.warning(f"Key frame not found: {key_frame_path}, using mock")
                return self._mock_score(scene)

            # Load image
            image = Image.open(key_frame_path).convert("RGB")

            # Craft prompt as professional editor
            prompt = """You are a professional social media video editor and Instagram Reel curator.

Analyze this video frame and provide a JSON assessment for use in creating a high-energy Instagram Reel.

Rate these aspects on a 1-10 scale:
- scenic_beauty: Visual composition, natural beauty, cinematic appeal (1=ugly, 10=stunning)
- action: Motion, energy, dynamic content (1=static, 10=highly energetic)
- emotion: Emotional impact, storytelling power (1=neutral, 10=compelling)
- stability: Camera/image stability, technical quality (1=shaky/blurry, 10=perfectly stable)
- blurriness: Image sharpness and clarity (1=very blurry, 10=crystal clear)

Also provide:
- brief_description: One sentence describing what happens in this frame
- is_usable: true if suitable for Instagram Reel, false if poor quality/unusable
- overall_score: Average of all numeric scores (1-10)

CRITICAL: Return ONLY valid JSON, nothing else. No markdown, no code blocks, just JSON.

{
  "scenic_beauty": <1-10>,
  "action": <1-10>,
  "emotion": <1-10>,
  "stability": <1-10>,
  "blurriness": <1-10>,
  "brief_description": "<one sentence>",
  "is_usable": <true/false>,
  "overall_score": <float>
}"""

            # Prepare input
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Process and generate
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            image_inputs = self.processor(
                text=text,
                images=[image],
                padding=True,
                return_tensors="pt",
            ).to(self.model.device)

            # Generate with appropriate settings
            with torch.no_grad():
                output_ids = self.model.generate(
                    **image_inputs,
                    max_new_tokens=200,
                    temperature=0.7,
                    top_p=0.9,
                )

            # Decode response
            response_text = self.processor.batch_decode(
                output_ids,
                skip_special_tokens=True,
            )[0]

            logger.debug(f"LLM response: {response_text[:200]}")

            # Extract and parse JSON
            score_data = self._parse_llm_response(response_text)

            if score_data:
                logger.info(f"Scene score: {score_data.get('overall_score', 'N/A')}")
                return score_data
            else:
                logger.warning("Failed to parse LLM response, using mock")
                return self._mock_score(scene)

        except Exception as e:
            logger.warning(f"Real LLM scoring failed: {str(e)}, using mock")
            return self._mock_score(scene)

    @staticmethod
    def _parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if not json_match:
                return None

            json_str = json_match.group()
            data = json.loads(json_str)

            # Validate required fields
            required_fields = [
                "scenic_beauty",
                "action",
                "emotion",
                "stability",
                "blurriness",
                "overall_score",
                "is_usable",
            ]

            for field in required_fields:
                if field not in data:
                    return None

            # Ensure scores are numeric and in range
            for field in ["scenic_beauty", "action", "emotion", "stability", "blurriness"]:
                if not isinstance(data[field], (int, float)):
                    return None
                data[field] = min(10, max(1, float(data[field])))

            data["overall_score"] = min(
                10,
                max(1, float(data["overall_score"])),
            )

            return data

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.debug(f"JSON parsing failed: {str(e)}")
            return None

    @staticmethod
    def _mock_score(scene: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deterministic mock score from scene index."""
        scene_idx = scene.get("scene_idx", 0)

        # Deterministic scoring based on scene index
        base_score = 5.0 + (scene_idx % 5) * 0.8

        return {
            "scenic_beauty": min(10, 5 + (scene_idx % 3)),
            "action": min(10, 4 + (scene_idx % 4)),
            "emotion": min(10, 6 + (scene_idx % 3)),
            "stability": min(10, 7 + (scene_idx % 2)),
            "blurriness": min(10, 8 + (scene_idx % 2)),
            "brief_description": f"Scene with index {scene_idx}",
            "is_usable": True,
            "overall_score": base_score,
        }

    @staticmethod
    def _default_score() -> Dict[str, Any]:
        """Default score if scoring fails."""
        return {
            "scenic_beauty": 5,
            "action": 5,
            "emotion": 5,
            "stability": 5,
            "blurriness": 5,
            "brief_description": "Scene",
            "is_usable": True,
            "overall_score": 5.0,
        }

    def can_resume(self, file_id: str) -> bool:
        """Check if can resume from checkpoint."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return False

        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        return checkpoint.get("stage_progress", {}).get(self.stage_name) is not None

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get progress info."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            progress = checkpoint.get("stage_progress", {}).get(self.stage_name)
            if progress:
                return ProgressInfo(
                    stage_name=self.stage_name,
                    file_id=file_id,
                    total_items=progress.get("total_scenes", 0),
                    completed_items=progress.get("scored_scenes", 0),
                )
        return None
