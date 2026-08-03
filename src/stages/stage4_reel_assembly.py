"""Stage 4: Reel Assembly - Create optimal reel (configurable duration)."""

import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = get_logger("stages.stage4_reel_assembly")


class Stage4ReelAssembly(Stage):
    """Assemble optimal 15-second reel from scored scenes using LLM guidance."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        max_duration_seconds: float = 15.0,
        skip_model_load: bool = False,
        use_llm: bool = True,
    ):
        super().__init__("stage4_reel_assembly")
        self.checkpoint_manager = checkpoint_manager
        self.max_duration_seconds = max_duration_seconds
        self.skip_model_load = skip_model_load
        self.use_llm = use_llm
        self.model = None
        self.tokenizer = None

    def _load_model(self) -> None:
        """Load LLM for reel assembly guidance."""
        if self.skip_model_load or not self.use_llm:
            return

        if self.model is not None:
            return

        if not LLM_AVAILABLE:
            logger.warning("PyTorch/transformers not available, using heuristic")
            return

        try:
            # Use a smaller, efficient LLM for text-only reasoning
            logger.info("Loading LLM for reel assembly...")

            model_name = "gpt2"  # Fallback to GPT2 for assembly reasoning
            # Or use: "meta-llama/Llama-2-7b-hf" if available
            # Or: "mistralai/Mistral-7B-Instruct-v0.1"

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.float32,
            )

            if self.model:
                self.model.eval()
                logger.info(f"LLM loaded: {model_name}")

        except Exception as e:
            logger.warning(f"Failed to load LLM: {str(e)}, using heuristic")
            self.model = None
            self.tokenizer = None

    def run(
        self,
        file_id: str,
        scored_scenes_checkpoint: Dict[str, Any],
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """Assemble optimal 15-second reel."""
        self._log_stage_start(file_id)

        try:
            # Get scored scenes
            scenes = scored_scenes_checkpoint.get("scored_scenes", [])

            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scored scenes to assemble",
                )

            # Filter usable scenes and sort by score
            usable_scenes = [s for s in scenes if s.get("is_usable", True)]
            usable_scenes.sort(
                key=lambda x: x.get("overall_score", 0),
                reverse=True,
            )

            if not usable_scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No usable scenes found",
                )

            logger.info(f"[{file_id}] Assembling reel from {len(usable_scenes)} usable scenes")

            # Create reel plan
            reel_plan = self._assemble_reel(usable_scenes)

            if not reel_plan.get("clips"):
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="Failed to create reel plan",
                )

            # Verify duration
            total_duration = reel_plan.get("total_duration", 0)
            if total_duration > self.max_duration_seconds:
                logger.warning(
                    f"Reel duration {total_duration}s exceeds {self.max_duration_seconds}s"
                )

            # Save checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "reel_plan": reel_plan,
                "total_duration_seconds": total_duration,
                "clips_selected": len(reel_plan.get("clips", [])),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )

            # Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "REEL_ASSEMBLED"
            metadata["stage_timestamps"]["REEL_ASSEMBLED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)

            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Assembled {len(reel_plan.get('clips', []))} clips into {total_duration:.1f}s reel",
                data={
                    "clip_count": len(reel_plan.get("clips", [])),
                    "total_duration": total_duration,
                },
            )

        except Exception as e:
            logger.exception(f"[{file_id}] Stage 4 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Reel assembly failed: {str(e)}",
            )

    def _assemble_reel(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assemble optimal 15-second reel from scored scenes using LLM or heuristic."""
        if self.skip_model_load or not self.use_llm:
            return self._default_reel_plan(scenes)

        self._load_model()

        # Try LLM-based assembly
        if self.model is not None:
            try:
                return self._assemble_reel_with_llm(scenes)
            except Exception as e:
                logger.warning(f"LLM assembly failed: {str(e)}, using heuristic")

        # Fallback to heuristic
        return self._default_reel_plan(scenes)

    def _assemble_reel_with_llm(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to create optimal reel assembly plan."""
        try:
            # Prepare scene data for LLM
            scene_data = []
            for scene in scenes[:20]:  # Use top 20 scenes
                scene_data.append({
                    "scene_id": scene.get("scene_id", "unknown"),
                    "duration": scene.get("duration_seconds", 5.0),
                    "score": round(scene.get("overall_score", 5.0), 1),
                    "description": scene.get("brief_description", "Scene"),
                    "start_time_ms": scene.get("start_time_ms", 0),
                    "end_time_ms": scene.get("end_time_ms", 0),
                })

            prompt = f"""Create a 15-second Instagram Reel edit plan from these scenes:

Available scenes (sorted by quality score):
{json.dumps(scene_data[:10], indent=2)}

Requirements:
- Total duration must be ≤15 seconds
- Start strong (first 2-3 seconds should be high-impact)
- Clips should be 1.5-3 seconds each
- Avoid repetitive shots back-to-back
- End with the most impressive shot
- Prefer scenes with score > 7.0

Return a JSON edit plan like this:
{{
  "clips": [
    {{"scene_id": "...", "start_ms": 0, "end_ms": 3000, "duration_s": 3.0}},
    ...
  ],
  "total_duration": 14.8,
  "reasoning": "..."
}}

Respond with ONLY the JSON, no other text."""

            # Generate with LLM
            inputs = self.tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=400,
                    temperature=0.7,
                    top_p=0.9,
                )

            response = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    plan_data = json.loads(json_match.group())

                    # Validate and normalize
                    clips = plan_data.get("clips", [])
                    total_duration = plan_data.get("total_duration", 0)

                    if clips and total_duration > 0 and total_duration <= self.max_duration_seconds:
                        logger.info(f"LLM created {len(clips)} clips in {total_duration}s")
                        return {
                            "total_duration": total_duration,
                            "reasoning": plan_data.get("reasoning", "LLM assembly"),
                            "clips": clips,
                        }
                except (json.JSONDecodeError, KeyError):
                    pass

            logger.debug("LLM response not valid, falling back to heuristic")
            return self._default_reel_plan(scenes)

        except Exception as e:
            logger.warning(f"LLM assembly error: {str(e)}")
            return self._default_reel_plan(scenes)

    def _default_reel_plan(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create reel plan using heuristic approach."""
        clips = []
        total_duration = 0.0

        # Use top scenes in order, limiting each to 3 seconds
        for scene in scenes[:10]:  # Use top 10 scenes
            scene_duration = scene.get("duration_seconds", 5.0)
            clip_duration = min(scene_duration, 3.0)  # Max 3 seconds per clip

            # Check if adding this clip exceeds 15 seconds
            if total_duration + clip_duration > self.max_duration_seconds:
                # Trim last clip to fit
                clip_duration = self.max_duration_seconds - total_duration
                total_duration = self.max_duration_seconds
            else:
                total_duration += clip_duration

            # Get start time from scene (must have start_time_ms from stage 2)
            start_ms = scene.get("start_time_ms", 0)
            end_ms = int(start_ms + clip_duration * 1000)

            # Validate clip timing (end must be > start)
            if end_ms <= start_ms:
                logger.warning(
                    f"Invalid clip timing for {scene.get('scene_id')}: "
                    f"start_ms={start_ms}, end_ms={end_ms}. Skipping."
                )
                total_duration -= clip_duration  # Remove from total
                continue

            clips.append({
                "scene_id": scene.get("scene_id"),
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
                "clip_duration": clip_duration,
                "score": scene.get("overall_score", 5.0),
            })

            if total_duration >= self.max_duration_seconds - 0.1:
                break

        if not clips:
            logger.warning("No valid clips generated, using fallback single-scene plan")
            if scenes:
                scene = scenes[0]
                start_ms = scene.get("start_time_ms", 0)
                scene_duration = scene.get("duration_seconds", 5.0)
                clip_duration = min(scene_duration, self.max_duration_seconds)
                end_ms = int(start_ms + clip_duration * 1000)
                clips = [{
                    "scene_id": scene.get("scene_id"),
                    "start_ms": int(start_ms),
                    "end_ms": int(end_ms),
                    "clip_duration": clip_duration,
                    "score": scene.get("overall_score", 5.0),
                }]
                total_duration = clip_duration

        return {
            "total_duration": total_duration,
            "reasoning": f"Selected top {len(clips)} scenes, total {total_duration:.1f}s",
            "clips": clips,
        }

    def can_resume(self, file_id: str) -> bool:
        """Assembly is deterministic, not resumable."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)

    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """Get progress."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=1,
                completed_items=1,
            )
        return None
