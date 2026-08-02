"""Intelligent perspective selection for 360° videos."""

import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json

from src.utils.logger import get_logger
from .scene_analyzer import SceneAnalyzer, DetectionResult

logger = get_logger("analytics.perspective_selector")


@dataclass
class PerspectiveScore:
    """Score for a specific perspective/direction."""
    perspective: str  # forward, backward, left, right, up, down
    yaw: float  # -180 to 180
    pitch: float  # -90 to 90
    roll: float  # 0 (fixed)
    fov: int  # Field of view in degrees

    # Scoring metrics
    subject_score: float  # 0-10, based on human detection
    scenery_score: float  # 0-10, based on landscape beauty
    composition_score: float  # 0-10, based on framing
    motion_score: float  # 0-10, based on action
    overall_score: float  # Weighted average

    rationale: str  # Why this perspective was selected

    def to_dict(self) -> Dict:
        return asdict(self)


class PerspectiveSelector:
    """Select optimal viewing direction for 360° videos."""

    # Standard perspectives to sample
    PERSPECTIVES = {
        "forward": {"yaw": 0, "pitch": 0, "roll": 0},
        "backward": {"yaw": 180, "pitch": 0, "roll": 0},
        "left": {"yaw": -90, "pitch": 0, "roll": 0},
        "right": {"yaw": 90, "pitch": 0, "roll": 0},
        "up": {"yaw": 0, "pitch": -45, "roll": 0},
        "down": {"yaw": 0, "pitch": 45, "roll": 0},
        "left_down": {"yaw": -90, "pitch": 30, "roll": 0},
        "right_down": {"yaw": 90, "pitch": 30, "roll": 0},
    }

    def __init__(self):
        """Initialize perspective selector."""
        self.analyzer = SceneAnalyzer()

    def select_best_perspective(
        self,
        video_path: Path,
        keyframe_path: Optional[Path] = None,
        prefer_subjects: bool = True,
    ) -> Tuple[str, PerspectiveScore]:
        """
        Select best perspective for a 360° video.

        Args:
            video_path: Input 360° video
            keyframe_path: Optional keyframe to analyze
            prefer_subjects: Prioritize perspectives with humans

        Returns:
            (best_perspective, detailed_score)
        """
        try:
            logger.info(f"Selecting perspective for {video_path.name}")

            # Extract sample frames from different angles if needed
            if keyframe_path and keyframe_path.exists():
                frame_analysis = self.analyzer.analyze_frame(keyframe_path)
                if frame_analysis:
                    logger.info(f"Frame analysis: humans={frame_analysis.has_humans}, "
                               f"scenery={frame_analysis.scenery_quality:.1f}")

            # Score each perspective
            perspective_scores = self._score_perspectives(frame_analysis if keyframe_path else None)

            # Select best based on content
            if prefer_subjects:
                # Find perspectives where humans are visible
                best = self._select_by_subjects(perspective_scores)
            else:
                # Select based on overall composition
                best = self._select_by_composition(perspective_scores)

            logger.info(f"Selected perspective: {best.perspective} "
                       f"(score={best.overall_score:.1f}) - {best.rationale}")

            return best.perspective, best

        except Exception as e:
            logger.error(f"Perspective selection failed: {str(e)}")
            # Default to forward
            return "forward", PerspectiveScore(
                perspective="forward",
                yaw=0, pitch=0, roll=0, fov=90,
                subject_score=5.0, scenery_score=5.0,
                composition_score=5.0, motion_score=5.0,
                overall_score=5.0,
                rationale="Default forward perspective (selection failed)"
            )

    def _score_perspectives(self, frame_analysis: Optional[DetectionResult]) -> Dict[str, PerspectiveScore]:
        """Score each standard perspective."""
        scores = {}

        if frame_analysis is None:
            # No specific frame data, use heuristics
            for name, angles in self.PERSPECTIVES.items():
                scores[name] = self._create_heuristic_score(name, angles)
        else:
            # Score based on frame analysis
            for name, angles in self.PERSPECTIVES.items():
                scores[name] = self._score_perspective_for_frame(name, angles, frame_analysis)

        return scores

    def _score_perspective_for_frame(
        self,
        perspective: str,
        angles: Dict,
        frame_analysis: DetectionResult
    ) -> PerspectiveScore:
        """Score a perspective given frame analysis."""

        # Subject score: prioritize perspectives where humans face camera
        subject_score = 0.0
        subject_rationale = ""
        if frame_analysis.has_humans:
            # Forward and left/right tend to face subjects
            if perspective in ["forward", "left", "right", "left_down", "right_down"]:
                subject_score = frame_analysis.composition_score + 2.0
                subject_rationale = f"{perspective} shows {frame_analysis.human_count} subjects"
            else:
                subject_score = frame_analysis.composition_score - 1.0
                subject_rationale = f"{perspective} away from subjects"
        else:
            subject_score = 5.0
            subject_rationale = "No subjects detected"

        subject_score = min(10.0, subject_score)

        # Scenery score: prefer landscapes over direct overhead
        scenery_score = frame_analysis.scenery_quality
        if perspective in ["up", "down"]:
            scenery_score *= 0.8  # Slight penalty for overhead angles
            scenery_rationale = f"Overhead angle reduces scenery impact"
        else:
            scenery_rationale = f"Horizontal angle good for scenery"

        # Composition score: balance of all factors
        composition_score = frame_analysis.composition_score
        if frame_analysis.has_humans:
            if perspective == "forward":
                composition_score += 1.0
                composition_rationale = "Forward: ideal for frontal subjects"
            elif perspective in ["left", "right"]:
                composition_score += 0.5
                composition_rationale = f"{perspective}: good for profile shots"
        else:
            if perspective == "forward":
                composition_score += 0.5
                composition_rationale = "Forward: good default for landscapes"

        composition_score = min(10.0, composition_score)

        # Motion score: based on motion detection
        motion_score = frame_analysis.motion_level / 10.0  # Convert 0-100 to 0-10
        if perspective == "forward" and frame_analysis.motion_level > 50:
            motion_score += 1.0  # Forward angle better captures frontal motion
            motion_rationale = "Forward captures frontal motion well"
        else:
            motion_rationale = f"Motion level: {frame_analysis.motion_level:.0f}%"

        # Overall score: weighted average
        overall_score = (
            subject_score * 0.4 +  # Subject detection is most important
            scenery_score * 0.2 +  # Scenery quality
            composition_score * 0.25 +  # Composition
            motion_score * 0.15  # Motion
        )

        rationale = f"{subject_rationale}; {scenery_rationale}; {composition_rationale}; {motion_rationale}"

        return PerspectiveScore(
            perspective=perspective,
            yaw=angles["yaw"],
            pitch=angles["pitch"],
            roll=angles["roll"],
            fov=90,
            subject_score=subject_score,
            scenery_score=scenery_score,
            composition_score=composition_score,
            motion_score=motion_score,
            overall_score=overall_score,
            rationale=rationale
        )

    @staticmethod
    def _create_heuristic_score(perspective: str, angles: Dict) -> PerspectiveScore:
        """Create heuristic score when no frame data available."""
        heuristic_scores = {
            "forward": (8.0, 7.0, 8.5, 6.0, "Primary shooting direction - most content"),
            "backward": (6.0, 6.0, 6.0, 5.0, "Alternative angle for variety"),
            "left": (7.0, 7.5, 7.0, 5.5, "Profile angle, good for side compositions"),
            "right": (7.0, 7.5, 7.0, 5.5, "Profile angle, good for side compositions"),
            "up": (5.0, 6.0, 5.5, 4.0, "Overhead perspective - limited use"),
            "down": (5.0, 5.5, 5.0, 4.0, "Downward perspective - limited use"),
            "left_down": (6.5, 7.0, 6.5, 5.0, "Angled composition"),
            "right_down": (6.5, 7.0, 6.5, 5.0, "Angled composition"),
        }

        subj, scenery, comp, motion, rationale = heuristic_scores.get(
            perspective, (5.0, 5.0, 5.0, 5.0, "Unknown perspective")
        )

        overall = (subj * 0.4 + scenery * 0.2 + comp * 0.25 + motion * 0.15)

        return PerspectiveScore(
            perspective=perspective,
            yaw=angles["yaw"],
            pitch=angles["pitch"],
            roll=angles["roll"],
            fov=90,
            subject_score=subj,
            scenery_score=scenery,
            composition_score=comp,
            motion_score=motion,
            overall_score=overall,
            rationale=rationale
        )

    @staticmethod
    def _select_by_subjects(scores: Dict[str, PerspectiveScore]) -> PerspectiveScore:
        """Select perspective prioritizing subject detection."""
        return max(scores.values(), key=lambda s: s.subject_score * 0.5 + s.overall_score * 0.5)

    @staticmethod
    def _select_by_composition(scores: Dict[str, PerspectiveScore]) -> PerspectiveScore:
        """Select perspective prioritizing composition."""
        return max(scores.values(), key=lambda s: s.overall_score)

    def get_all_perspective_scores(
        self,
        video_path: Path,
        keyframe_path: Optional[Path] = None,
    ) -> Dict[str, PerspectiveScore]:
        """Get scores for all perspectives (for analysis/debugging)."""
        frame_analysis = None
        if keyframe_path and keyframe_path.exists():
            frame_analysis = self.analyzer.analyze_frame(keyframe_path)

        scores = self._score_perspectives(frame_analysis)
        return scores

    def create_perspective_report(
        self,
        video_path: Path,
        keyframe_path: Optional[Path] = None,
    ) -> Dict:
        """Create detailed perspective analysis report."""
        logger.info(f"Creating perspective report for {video_path.name}")

        all_scores = self.get_all_perspective_scores(video_path, keyframe_path)
        best_perspective, best_score = self.select_best_perspective(
            video_path, keyframe_path, prefer_subjects=True
        )

        # Frame analysis if available
        frame_analysis = None
        if keyframe_path and keyframe_path.exists():
            frame_analysis = self.analyzer.analyze_frame(keyframe_path)

        report = {
            "video": str(video_path.name),
            "selected_perspective": best_perspective,
            "best_score": best_score.to_dict(),
            "all_perspectives": {name: score.to_dict() for name, score in all_scores.items()},
            "frame_analysis": frame_analysis.to_dict() if frame_analysis else None,
            "reasoning": best_score.rationale,
        }

        return report
