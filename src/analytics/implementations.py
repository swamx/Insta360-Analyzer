"""Concrete implementations of analytics components."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json

from src.utils.logger import get_logger
from .core import (
    AnalysisInput,
    AnalysisOutput,
    AnalyticsConfig,
    AnalysisStage,
    DecisionType,
    Analyzer,
    Detector,
    Selector,
    Scorer,
)
from .scene_analyzer import SceneAnalyzer as LegacySceneAnalyzer
from .perspective_selector import PerspectiveSelector as LegacyPerspectiveSelector

logger = get_logger("analytics.implementations")


# ============================================================================
# Format Detection (360° Detector)
# ============================================================================

class Insta360FormatDetector(Detector):
    """Detects Insta360 format and projection type."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize detector."""
        super().__init__(config)
        self.legacy_detector = None

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input is a video file."""
        if not input_data.file_path.exists():
            logger.warning(f"File not found: {input_data.file_path}")
            return False
        return True

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and detect format."""
        if not self.validate_input(input_data):
            return self._create_error_output(
                input_data,
                "File not found",
                0.0,
            )

        try:
            analysis = self.detect(input_data)

            is_insta360 = analysis.get("is_insta360", False)
            projection = analysis.get("projection", "unknown")
            confidence = analysis.get("confidence", 0.9)

            decision = {
                "is_insta360": is_insta360,
                "projection": projection,
                "needs_conversion": is_insta360 and projection == "equirectangular",
            }

            rationale = f"Detected {projection} projection. "
            if is_insta360:
                rationale += "File is Insta360 format. "
                if decision["needs_conversion"]:
                    rationale += "360° video detected - conversion required."
                else:
                    rationale += "Single-perspective video - no conversion needed."
            else:
                rationale += "File is not Insta360 format."

            return AnalysisOutput(
                analysis_id=f"{input_data.file_id}_format_detection",
                stage=AnalysisStage.STAGE_0_5,
                decision_type=DecisionType.FORMAT_DETECTION,
                decision=decision,
                confidence=confidence,
                rationale=rationale,
                inputs={"file_path": str(input_data.file_path)},
                results=analysis,
            )

        except Exception as e:
            logger.error(f"Format detection failed: {str(e)}")
            return self._create_error_output(input_data, str(e), 0.0)

    def detect(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Detect format and projection."""
        try:
            from src.insta360 import Insta360Detector

            is_insta360 = Insta360Detector.is_insta360_format(input_data.file_path)

            if is_insta360:
                metadata = Insta360Detector.get_insta360_metadata(input_data.file_path)
                projection = metadata.get("projection", "unknown")
            else:
                metadata = {}
                projection = "unknown"

            return {
                "is_insta360": is_insta360,
                "projection": projection,
                "confidence": 0.95 if is_insta360 else 0.85,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Detection error: {str(e)}")
            return {
                "is_insta360": False,
                "projection": "unknown",
                "confidence": 0.0,
                "error": str(e),
            }

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Alias for detect."""
        return self.detect(input_data)

    def _create_error_output(
        self, input_data: AnalysisInput, error: str, confidence: float
    ) -> AnalysisOutput:
        """Create error output."""
        return AnalysisOutput(
            analysis_id=f"{input_data.file_id}_format_detection_error",
            stage=AnalysisStage.STAGE_0_5,
            decision_type=DecisionType.FORMAT_DETECTION,
            decision={"is_insta360": False, "projection": "unknown"},
            confidence=confidence,
            rationale=f"Error during format detection: {error}",
            inputs={"file_path": str(input_data.file_path)},
            results={},
        )


# ============================================================================
# Subject Detection (Subject Detector)
# ============================================================================

class SubjectDetector(Detector):
    """Detects humans and subjects in frames."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize detector."""
        super().__init__(config)
        self.legacy_analyzer = LegacySceneAnalyzer()

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input is a frame file."""
        keyframe = Path(input_data.metadata.get("frame_path", ""))
        if not keyframe.exists():
            logger.warning(f"Frame not found: {keyframe}")
            return False
        return True

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and detect subjects."""
        if not self.validate_input(input_data):
            return self._create_output(
                input_data,
                {"detected": False, "count": 0},
                0.0,
                "Frame not found",
            )

        try:
            detection = self.detect(input_data)

            return AnalysisOutput(
                analysis_id=f"{input_data.scene_id}_subject_detection",
                stage=AnalysisStage.STAGE_3,
                decision_type=DecisionType.SUBJECT_DETECTION,
                decision={
                    "has_subjects": detection.get("has_humans", False),
                    "count": detection.get("human_count", 0),
                },
                confidence=detection.get("human_confidence", 0.0),
                rationale=self._generate_rationale(detection),
                inputs={"frame_path": input_data.metadata.get("frame_path")},
                results=detection,
            )

        except Exception as e:
            logger.error(f"Subject detection failed: {str(e)}")
            return self._create_output(input_data, {"error": str(e)}, 0.0, f"Error: {str(e)}")

    def detect(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Detect subjects in frame."""
        frame_path = Path(input_data.metadata.get("frame_path", ""))

        if not frame_path.exists():
            return {"has_humans": False, "human_count": 0, "human_confidence": 0.0}

        try:
            result = self.legacy_analyzer.analyze_frame(frame_path)

            if result is None:
                return {"has_humans": False, "human_count": 0, "human_confidence": 0.0}

            return {
                "has_humans": result.has_humans,
                "human_count": result.human_count,
                "human_confidence": result.human_confidence,
                "scenery_quality": result.scenery_quality,
                "composition_score": result.composition_score,
            }

        except Exception as e:
            logger.error(f"Detection error: {str(e)}")
            return {"has_humans": False, "human_count": 0, "human_confidence": 0.0}

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Alias for detect."""
        return self.detect(input_data)

    @staticmethod
    def _generate_rationale(detection: Dict[str, Any]) -> str:
        """Generate rationale for detection."""
        if detection.get("has_humans"):
            count = detection.get("human_count", 0)
            confidence = detection.get("human_confidence", 0.0)
            return f"Detected {count} subjects with {confidence:.2f} confidence"
        else:
            return "No subjects detected in frame"

    def _create_output(
        self,
        input_data: AnalysisInput,
        decision: Dict[str, Any],
        confidence: float,
        rationale: str,
    ) -> AnalysisOutput:
        """Create output."""
        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_subject_detection",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.SUBJECT_DETECTION,
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            inputs={"frame_path": input_data.metadata.get("frame_path")},
            results={},
        )


# ============================================================================
# Scenery Analysis (Scenery Analyzer)
# ============================================================================

class SceneryAnalyzer(Analyzer):
    """Analyzes scenery quality and composition."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize analyzer."""
        super().__init__(config)
        self.legacy_analyzer = LegacySceneAnalyzer()

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input."""
        return True

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and analyze scenery."""
        try:
            analysis = self.analyze(input_data)

            scenery_score = analysis.get("scenery_quality", 5.0)
            composition_score = analysis.get("composition_score", 5.0)

            return AnalysisOutput(
                analysis_id=f"{input_data.scene_id}_scenery_analysis",
                stage=AnalysisStage.STAGE_3,
                decision_type=DecisionType.SCENERY_ANALYSIS,
                decision={
                    "scenery_score": scenery_score,
                    "composition_score": composition_score,
                },
                confidence=min(1.0, (scenery_score + composition_score) / 20.0),
                rationale=self._generate_rationale(analysis),
                inputs={"frame_path": input_data.metadata.get("frame_path")},
                results=analysis,
            )

        except Exception as e:
            logger.error(f"Scenery analysis failed: {str(e)}")
            return self._create_error_output(input_data, str(e))

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Analyze scenery from frame."""
        frame_path = Path(input_data.metadata.get("frame_path", ""))

        if not frame_path.exists():
            return {
                "scenery_quality": 5.0,
                "composition_score": 5.0,
                "brightness": 128,
                "contrast": 50,
            }

        try:
            result = self.legacy_analyzer.analyze_frame(frame_path)

            if result is None:
                return self._default_analysis()

            return {
                "scenery_quality": result.scenery_quality,
                "composition_score": result.composition_score,
                "brightness": result.brightness,
                "contrast": result.contrast,
                "motion_level": result.motion_level,
                "dominant_colors": result.dominant_colors,
            }

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return self._default_analysis()

    @staticmethod
    def _generate_rationale(analysis: Dict[str, Any]) -> str:
        """Generate rationale."""
        scenery = analysis.get("scenery_quality", 5.0)
        composition = analysis.get("composition_score", 5.0)
        brightness = analysis.get("brightness", 128)

        rationale = f"Scenery: {scenery:.1f}/10, Composition: {composition:.1f}/10. "
        rationale += f"Brightness: {brightness:.0f}/255"

        return rationale

    @staticmethod
    def _default_analysis() -> Dict[str, Any]:
        """Return default analysis."""
        return {
            "scenery_quality": 5.0,
            "composition_score": 5.0,
            "brightness": 128,
            "contrast": 50,
            "motion_level": 50,
            "dominant_colors": ["#808080"],
        }

    def _create_error_output(self, input_data: AnalysisInput, error: str) -> AnalysisOutput:
        """Create error output."""
        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_scenery_analysis_error",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.SCENERY_ANALYSIS,
            decision={"error": error},
            confidence=0.0,
            rationale=f"Error during scenery analysis: {error}",
            inputs={},
            results={},
        )


# ============================================================================
# Perspective Selection (Perspective Selector)
# ============================================================================

class PerspectiveSelectorComponent(Selector):
    """Selects best perspective for 360° videos."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize selector."""
        super().__init__(config)
        self.legacy_selector = LegacyPerspectiveSelector()

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input."""
        return True

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and select perspective."""
        try:
            candidates = list(self.legacy_selector.PERSPECTIVES.keys())
            scores = self._score_perspectives(input_data)

            selected = self.select(input_data, candidates, scores)

            return AnalysisOutput(
                analysis_id=f"{input_data.scene_id}_perspective_selection",
                stage=AnalysisStage.STAGE_0_5,
                decision_type=DecisionType.PERSPECTIVE_SELECTION,
                decision=selected,
                confidence=min(1.0, scores.get(selected, 5.0) / 10.0),
                rationale=self._generate_rationale(selected, scores),
                inputs={"candidates": candidates},
                results={"all_scores": scores},
            )

        except Exception as e:
            logger.error(f"Perspective selection failed: {str(e)}")
            return self._create_error_output(input_data, str(e))

    def select(
        self, input_data: AnalysisInput, candidates: List[str], scores: Dict[str, float]
    ) -> str:
        """Select best perspective."""
        if not scores:
            return "forward"

        return max(scores.items(), key=lambda x: x[1])[0]

    def _score_perspectives(self, input_data: AnalysisInput) -> Dict[str, float]:
        """Score all perspectives."""
        try:
            frame_path = Path(input_data.metadata.get("frame_path", ""))
            perspective_scores = self.legacy_selector.get_all_perspective_scores(
                Path(input_data.file_path),
                frame_path if frame_path.exists() else None,
            )

            return {
                name: score.overall_score
                for name, score in perspective_scores.items()
            }

        except Exception as e:
            logger.error(f"Scoring error: {str(e)}")
            # Return heuristic scores
            return {
                "forward": 7.5,
                "backward": 6.0,
                "left": 7.0,
                "right": 7.0,
                "up": 5.0,
                "down": 5.0,
                "left_down": 6.5,
                "right_down": 6.5,
            }

    @staticmethod
    def _generate_rationale(selected: str, scores: Dict[str, float]) -> str:
        """Generate rationale."""
        score = scores.get(selected, 5.0)
        top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

        rationale = f"Selected {selected} (score: {score:.2f}/10). "
        rationale += f"Top alternatives: {', '.join(f'{name} ({s:.1f})' for name, s in top_3[1:])}"

        return rationale

    def _create_error_output(self, input_data: AnalysisInput, error: str) -> AnalysisOutput:
        """Create error output."""
        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_perspective_error",
            stage=AnalysisStage.STAGE_0_5,
            decision_type=DecisionType.PERSPECTIVE_SELECTION,
            decision="forward",  # Default
            confidence=0.5,
            rationale=f"Using default perspective due to error: {error}",
            inputs={},
            results={},
        )
