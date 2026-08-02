"""Stage 4: Reel Assembly - Create optimal 15-second reel."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.stages.base import Stage, StageResult, ProgressInfo
from src.storage.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger


logger = get_logger("stages.stage4_reel_assembly")


class Stage4ReelAssembly(Stage):
    """Assemble optimal 15-second reel from scored scenes."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        max_duration_seconds: float = 15.0,
        skip_model_load: bool = False,
    ):
        super().__init__("stage4_reel_assembly")
        self.checkpoint_manager = checkpoint_manager
        self.max_duration_seconds = max_duration_seconds
        self.skip_model_load = skip_model_load
        self.model = None

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
        """Assemble optimal 15-second reel from scored scenes."""
        if self.skip_model_load:
            return self._default_reel_plan(scenes)

        # TODO: Call LLM to create reel plan
        # For now, use heuristic approach

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

            start_ms = scene.get("start_time_ms", 0)
            end_ms = int(start_ms + clip_duration * 1000)

            clips.append({
                "scene_id": scene.get("scene_id"),
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
                "clip_duration": clip_duration,
                "score": scene.get("overall_score", 5.0),
            })

            if total_duration >= self.max_duration_seconds - 0.1:
                break

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
