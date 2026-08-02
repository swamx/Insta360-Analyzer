"""Adaptive reel generation using feedback and learned preferences."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from src.utils.logger import get_logger
from .feedback import FeedbackCollector, FeedbackAnalyzer, LearningEngine, UserFeedback
from .core import AnalysisInput, AnalysisOutput, AnalyticsConfig

logger = get_logger("analytics.adaptive_reel")


@dataclass
class ReelConfiguration:
    """Configuration for reel generation."""

    name: str
    description: str
    version: str = "1.0.0"

    # Scene selection
    scene_scores: List[Dict[str, Any]] = None  # Scenes with scores
    min_scene_score: float = 5.0
    max_scenes: int = 8
    prefer_high_action: bool = False

    # Perspective
    perspective: str = "forward"
    fov: int = 90
    prefer_subjects: bool = True

    # Duration
    max_duration_seconds: float = 15.0
    min_scene_duration: float = 1.5
    max_scene_duration: float = 5.0

    # Quality
    min_subject_confidence: float = 0.5
    min_scenery_quality: float = 5.0
    min_composition_score: float = 5.0

    # Weights (from learned preferences)
    scoring_weights: Dict[str, float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "min_scene_score": self.min_scene_score,
            "max_scenes": self.max_scenes,
            "perspective": self.perspective,
            "max_duration_seconds": self.max_duration_seconds,
            "scoring_weights": self.scoring_weights or {},
        }


class AdaptiveReelGenerator:
    """Generate reels adaptively based on feedback."""

    def __init__(
        self,
        feedback_dir: Path,
        analytics_config: AnalyticsConfig = None,
    ):
        """Initialize adaptive reel generator."""
        self.feedback_dir = Path(feedback_dir)
        self.analytics_config = analytics_config or AnalyticsConfig()

        # Initialize feedback system
        self.collector = FeedbackCollector(self.feedback_dir / "feedback")
        self.analyzer = FeedbackAnalyzer(self.collector)
        self.learning_engine = LearningEngine(self.collector, self.analyzer)

        # Load existing feedback
        self.collector.load_feedback_history()

        self.config_history: Dict[str, ReelConfiguration] = {}

    def collect_reel_feedback(
        self,
        feedback: UserFeedback,
    ) -> str:
        """Collect feedback on generated reel."""
        feedback_id = self.collector.collect_feedback(feedback)

        logger.info(
            f"Collected feedback on reel {feedback.file_id}: "
            f"Rating {feedback.rating}/5, Type: {feedback.feedback_type}"
        )

        return feedback_id

    def analyze_reel_feedback(self, file_id: str) -> Dict[str, Any]:
        """Analyze feedback for specific reel."""
        report = self.analyzer.analyze_feedback(file_id)

        logger.info(f"Feedback analysis for {file_id}: Avg rating {report.average_rating:.1f}/5")

        return {
            "summary": {
                "total_feedback": report.total_feedback,
                "positive": report.positive_count,
                "negative": report.negative_count,
                "average_rating": report.average_rating,
            },
            "patterns": [p.model_dump() for p in report.patterns],
            "recommendations": report.recommendations,
            "top_liked": report.top_liked_aspects,
            "top_disliked": report.top_disliked_aspects,
        }

    def learn_and_adapt(self, file_id: str) -> Dict[str, Any]:
        """
        Learn from feedback and adapt configuration.

        Args:
            file_id: File to learn from

        Returns:
            Updated preferences and suggestions
        """
        # Learn from feedback
        learned_prefs = self.learning_engine.learn_from_feedback(file_id)

        # Get suggestions for next reel
        suggestions = self.learning_engine.suggest_parameters(file_id)

        logger.info(f"Adaptation complete for {file_id}: {len(learned_prefs)} preferences learned")

        return {
            "learned_preferences": learned_prefs,
            "suggestions": suggestions,
        }

    def generate_adaptive_config(
        self,
        file_id: str,
        scenes: List[Dict[str, Any]],
        base_config: Optional[ReelConfiguration] = None,
    ) -> ReelConfiguration:
        """
        Generate reel configuration adapted to learned preferences.

        Args:
            file_id: File being processed
            scenes: Available scenes with scores
            base_config: Optional base configuration to adapt

        Returns:
            Adaptive ReelConfiguration
        """
        # Get base config
        if base_config is None:
            base_config = ReelConfiguration(
                name=f"{file_id}_adaptive",
                description="Adaptive reel based on feedback",
            )

        # Get learned weights
        learned_weights = self.learning_engine.get_learned_weights()

        # Adapt scene selection based on feedback
        adapted_scenes = self._select_scenes_adaptively(file_id, scenes)

        # Create adaptive configuration
        config = ReelConfiguration(
            name=base_config.name,
            description=base_config.description,
            scene_scores=adapted_scenes,
            min_scene_score=self.learning_engine.learned_preferences.get(
                "min_scene_score", 5.0
            ),
            perspective=self._get_preferred_perspective(file_id),
            scoring_weights=learned_weights,
            max_duration_seconds=base_config.max_duration_seconds,
        )

        self.config_history[file_id] = config
        logger.info(f"Generated adaptive config for {file_id}")

        return config

    def regenerate_reel(
        self,
        file_id: str,
        scenes: List[Dict[str, Any]],
        executor_callback,  # FlowExecutor to regenerate with new config
    ) -> Dict[str, Any]:
        """
        Regenerate reel with adaptive configuration.

        Args:
            file_id: File to regenerate
            scenes: Available scenes
            executor_callback: Function to execute reel generation

        Returns:
            Results from reel generation
        """
        # Generate adaptive config
        config = self.generate_adaptive_config(file_id, scenes)

        logger.info(f"Regenerating reel for {file_id} with adaptive config")

        # Execute reel generation with new config
        try:
            result = executor_callback(config)
            logger.info(f"Reel regenerated successfully for {file_id}")
            return {
                "success": True,
                "config": config.to_dict(),
                "result": result,
            }
        except Exception as e:
            logger.error(f"Failed to regenerate reel: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "config": config.to_dict(),
            }

    def _select_scenes_adaptively(
        self, file_id: str, scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Adaptively select scenes based on feedback."""
        # Get feedback analysis
        report = self.analyzer.analyze_feedback(file_id)

        # If negative feedback on scene selection, be more selective
        if len([p for p in report.patterns if p.category.value == "scene_selection"]) > 0:
            logger.info(f"Adjusting scene selection for {file_id} based on negative feedback")
            # Increase minimum score threshold
            min_score = 7.0
        else:
            min_score = 5.0

        # Filter and sort scenes
        filtered = [s for s in scenes if s.get("overall_score", 0) >= min_score]
        sorted_scenes = sorted(filtered, key=lambda s: s.get("overall_score", 0), reverse=True)

        # Prefer scenes with detected subjects if user liked that
        if "has_subjects" in report.top_liked_aspects:
            sorted_scenes.sort(
                key=lambda s: s.get("has_subjects", False), reverse=True
            )

        return sorted_scenes[:8]  # Top 8 scenes

    def _get_preferred_perspective(self, file_id: str) -> str:
        """Get preferred perspective from feedback."""
        feedback = self.collector.get_feedback_for_file(file_id)

        # Count perspective mentions
        perspective_positive = {}
        for f in feedback:
            if f.category.value == "perspective" and f.feedback_type.value == "positive":
                # Suggestions might contain preferred perspective
                for suggestion in f.suggestions:
                    if "forward" in suggestion:
                        perspective_positive["forward"] = \
                            perspective_positive.get("forward", 0) + 1
                    elif "backward" in suggestion:
                        perspective_positive["backward"] = \
                            perspective_positive.get("backward", 0) + 1

        # Return most mentioned, or default
        if perspective_positive:
            return max(perspective_positive, key=perspective_positive.get)

        return "forward"

    def get_comparison_report(
        self,
        file_id: str,
        first_reel_config: ReelConfiguration,
        second_reel_config: ReelConfiguration,
    ) -> Dict[str, Any]:
        """
        Compare two reel configurations (A/B test).

        Args:
            file_id: File ID
            first_reel_config: First reel configuration
            second_reel_config: Second reel configuration (usually adaptive)

        Returns:
            Comparison report
        """
        feedback = self.collector.get_feedback_for_file(file_id)

        # Split feedback by config preference
        first_pref = []
        second_pref = []
        neutral = []

        for f in feedback:
            if f.comment and "first" in f.comment.lower():
                first_pref.append(f)
            elif f.comment and ("second" in f.comment.lower() or "new" in f.comment.lower()):
                second_pref.append(f)
            else:
                neutral.append(f)

        report = {
            "file_id": file_id,
            "first_reel": first_reel_config.to_dict(),
            "second_reel": second_reel_config.to_dict(),
            "comparison": {
                "prefer_first": len(first_pref),
                "prefer_second": len(second_pref),
                "neutral": len(neutral),
                "total_feedback": len(feedback),
                "winner": "second" if len(second_pref) > len(first_pref) else "first",
            },
            "recommendation": (
                "Use adaptive configuration" if len(second_pref) > len(first_pref)
                else "Keep original configuration"
            ),
        }

        return report

    def save_config_history(self, file_id: str) -> Path:
        """Save configuration history."""
        history_file = self.feedback_dir / f"{file_id}_config_history.json"

        history_data = {
            "file_id": file_id,
            "configs": [
                {
                    "version": i,
                    "config": config.to_dict(),
                }
                for i, (_, config) in enumerate(self.config_history.items())
            ],
        }

        with open(history_file, "w") as f:
            json.dump(history_data, f, indent=2)

        logger.info(f"Saved config history to {history_file}")

        return history_file

    def get_performance_metrics(self, file_id: str) -> Dict[str, Any]:
        """Get performance metrics for reel."""
        feedback = self.collector.get_feedback_for_file(file_id)
        report = self.analyzer.analyze_feedback(file_id)

        metrics = {
            "file_id": file_id,
            "feedback_summary": {
                "total_feedback_items": len(feedback),
                "average_rating": report.average_rating,
                "positive_feedback_percent": (
                    (report.positive_count / len(feedback) * 100)
                    if feedback else 0
                ),
            },
            "engagement_metrics": {
                "average_watch_time": (
                    sum(f.watch_time_percent or 0 for f in feedback) / len(feedback)
                    if feedback else 0
                ),
                "average_engagement": (
                    sum(f.engagement_metric or 0 for f in feedback) / len(feedback)
                    if feedback else 0
                ),
            },
            "improvement_opportunity": len([
                p for p in report.patterns
                if p.pattern_type == "avoidance"
            ]),
        }

        return metrics


class AdaptiveFlowManager:
    """Manage adaptive flows using feedback."""

    def __init__(self, generator: AdaptiveReelGenerator):
        """Initialize adaptive flow manager."""
        self.generator = generator

    def create_adaptive_flow_config(
        self,
        file_id: str,
        scenes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create flow configuration adapted to feedback.

        Returns:
            Configuration for flow execution
        """
        # Generate adaptive config
        config = self.generator.generate_adaptive_config(file_id, scenes)

        # Create flow configuration
        flow_config = {
            "name": f"adaptive_flow_{file_id}",
            "file_id": file_id,
            "reel_config": config.to_dict(),
            "scene_selection": config.scene_scores,
            "weights": config.scoring_weights,
        }

        logger.info(f"Created adaptive flow config for {file_id}")

        return flow_config
