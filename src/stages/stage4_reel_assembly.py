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
        """Assemble optimal reel with clip length optimization."""
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

            # Optimize clip length if unlimited duration
            if self.max_duration_seconds <= 0:
                logger.info(f"[{file_id}] Running clip length optimization (5-30s)...")
                reel_plan = self._optimize_clip_length(usable_scenes, file_id)
            else:
                # Create reel plan with fixed duration
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
                "optimization": reel_plan.get("optimization"),
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

            # Build message with optimization info if available
            message = f"Assembled {len(reel_plan.get('clips', []))} clips into {total_duration:.1f}s reel"
            if reel_plan.get("optimization"):
                opt = reel_plan["optimization"]
                message += f" (optimized: {opt.get('optimal_duration', 0):.1f}s clips, score={opt.get('quality_score', 0):.2f})"

            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=message,
                data={
                    "clip_count": len(reel_plan.get("clips", [])),
                    "total_duration": total_duration,
                    "optimization": reel_plan.get("optimization"),
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

    def _optimize_clip_length(
        self, scenes: List[Dict[str, Any]], file_id: str
    ) -> Dict[str, Any]:
        """Optimize clip length by testing 5-30 second ranges."""
        logger.info(f"[{file_id}] Testing clip durations from 5-30 seconds...")

        test_durations = [5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0]
        best_plan = None
        best_score = 0.0

        for duration in test_durations:
            # Create plan with this duration
            plan = self._create_reel_with_duration(scenes, duration)

            if not plan.get("clips"):
                continue

            # Score this plan based on:
            # 1. Scene quality (average of selected scenes)
            # 2. Clip count (more scenes = more variety)
            # 3. Duration utilization (fill the reel well)

            scene_scores = [c.get("score", 5.0) for c in plan.get("clips", [])]
            avg_scene_score = sum(scene_scores) / len(scene_scores) if scene_scores else 0

            # Quality components
            quality_score = avg_scene_score  # Base: average scene quality
            quality_score += len(plan.get("clips", [])) * 0.2  # Bonus: more clips
            quality_score += (plan.get("total_duration", 0) / 30.0) * 0.5  # Bonus: reel fullness

            logger.debug(
                f"[{file_id}] Duration {duration}s: "
                f"clips={len(plan.get('clips', []))}, "
                f"total={plan.get('total_duration', 0):.1f}s, "
                f"score={quality_score:.2f}"
            )

            if quality_score > best_score:
                best_score = quality_score
                best_plan = plan
                logger.info(
                    f"[{file_id}] New best duration: {duration}s (score={quality_score:.2f})"
                )

        if best_plan:
            best_plan["optimization"] = {
                "method": "clip_length_optimization",
                "tested_durations": test_durations,
                "optimal_duration": best_plan.get("clip_duration", 5.0),
                "quality_score": best_score,
            }
            return best_plan
        else:
            # Fallback to default
            logger.warning(f"[{file_id}] Optimization failed, using default plan")
            return self._default_reel_plan(scenes)

    def _create_reel_with_duration(
        self, scenes: List[Dict[str, Any]], clip_duration_seconds: float
    ) -> Dict[str, Any]:
        """Create a reel plan with a specific clip duration."""
        clips = []
        total_duration = 0.0
        max_reel_duration = 300.0  # Max 5 minutes for unlimited

        for scene in scenes[:15]:  # Use top 15 scenes for optimization
            # Use exactly this clip duration (or less if scene is shorter)
            scene_duration = scene.get("duration_seconds", 5.0)
            actual_clip_duration = min(scene_duration, clip_duration_seconds)

            # Check if adding this clip exceeds max
            if total_duration + actual_clip_duration > max_reel_duration:
                break

            start_ms = scene.get("start_time_ms", 0)
            end_ms = int(start_ms + actual_clip_duration * 1000)

            if end_ms > start_ms:  # Valid timing
                clips.append({
                    "scene_id": scene.get("scene_id"),
                    "start_ms": int(start_ms),
                    "end_ms": int(end_ms),
                    "clip_duration": actual_clip_duration,
                    "score": scene.get("overall_score", 5.0),
                })
                total_duration += actual_clip_duration

        return {
            "total_duration": total_duration,
            "clip_duration": clip_duration_seconds,
            "reasoning": f"Optimized {len(clips)} clips at {clip_duration_seconds}s each, "
                        f"total {total_duration:.1f}s",
            "clips": clips,
        }

    def _default_reel_plan(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create reel plan with scene diversity checking."""
        clips = []
        total_duration = 0.0
        selected_scene_ids = set()

        # Handle max_duration: 0 means unlimited, >0 means limit
        max_duration = self.max_duration_seconds if self.max_duration_seconds > 0 else float('inf')

        # Use top scenes with diversity checking
        min_temporal_distance_ms = 15000  # Prefer scenes at least 15s apart

        for scene in scenes[:15]:  # Use top 15 scenes for better selection
            scene_id = scene.get("scene_id")
            start_ms = scene.get("start_time_ms", 0)

            # Diversity check: ensure clips are temporally spread out
            if clips:  # Only check if we already have clips
                # Check distance from last selected scene
                last_start = clips[-1].get("start_ms", 0)
                temporal_distance = abs(start_ms - last_start)

                # Skip if too close to previous scene (likely similar content)
                if temporal_distance < min_temporal_distance_ms:
                    logger.debug(
                        f"Skipping scene {scene_id} - too close to previous "
                        f"({temporal_distance}ms < {min_temporal_distance_ms}ms)"
                    )
                    continue

            scene_duration = scene.get("duration_seconds", 5.0)
            clip_duration = min(scene_duration, 3.0)  # Max 3 seconds per clip

            # Check if adding this clip exceeds limit
            if max_duration != float('inf') and total_duration + clip_duration > max_duration:
                # Trim last clip to fit
                clip_duration = max_duration - total_duration
                total_duration = max_duration
            else:
                total_duration += clip_duration

            # Get start time from scene (must have start_time_ms from stage 2)
            end_ms = int(start_ms + clip_duration * 1000)

            # Validate clip timing (end must be > start)
            if end_ms <= start_ms:
                logger.warning(
                    f"Invalid clip timing for {scene_id}: "
                    f"start_ms={start_ms}, end_ms={end_ms}. Skipping."
                )
                total_duration -= clip_duration  # Remove from total
                continue

            clips.append({
                "scene_id": scene_id,
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
                "clip_duration": clip_duration,
                "score": scene.get("overall_score", 5.0),
            })

            if max_duration != float('inf') and total_duration >= max_duration - 0.1:
                break

        if not clips:
            logger.warning("No valid clips generated, using fallback single-scene plan")
            if scenes:
                scene = scenes[0]
                start_ms = scene.get("start_time_ms", 0)
                scene_duration = scene.get("duration_seconds", 5.0)
                # Use min of scene duration and max_duration (unless unlimited)
                if max_duration == float('inf'):
                    clip_duration = scene_duration
                else:
                    clip_duration = min(scene_duration, max_duration)
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
