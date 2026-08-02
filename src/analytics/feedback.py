"""Feedback collection, analysis, and learning system for reel generation."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from pydantic import BaseModel, Field, validator

from src.utils.logger import get_logger

logger = get_logger("analytics.feedback")


# ============================================================================
# Enums & Data Models
# ============================================================================

class FeedbackType(str, Enum):
    """Types of user feedback."""
    POSITIVE = "positive"      # Good decision, keep similar
    NEGATIVE = "negative"      # Bad decision, avoid similar
    NEUTRAL = "neutral"        # Acceptable but not great
    PARTIAL = "partial"        # Some aspects good, others bad
    REDIRECT = "redirect"      # Suggest alternative


class FeedbackCategory(str, Enum):
    """What aspect of reel the feedback is about."""
    PERSPECTIVE = "perspective"        # Wrong viewing angle
    SCENE_SELECTION = "scene_selection" # Wrong scene included
    SUBJECT_DETECTION = "subject_detection" # Missed or wrong subjects
    SCENERY_QUALITY = "scenery_quality"    # Landscape/composition quality
    TIMING = "timing"                   # Reel pacing or duration
    OVERALL = "overall"                 # General reel quality


class FeedbackSource(str, Enum):
    """Where feedback comes from."""
    USER = "user"              # Direct user feedback
    ANALYTICS = "analytics"    # Automated metrics
    ENGAGEMENT = "engagement"  # Social media engagement
    COMPARISON = "comparison"  # A/B test comparison


class UserFeedback(BaseModel):
    """User feedback on a reel or decision."""

    file_id: str
    scene_id: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    source: FeedbackSource = FeedbackSource.USER

    # Rating and comment
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    comment: str = ""

    # What was good/bad
    positive_aspects: List[str] = Field(default_factory=list)
    negative_aspects: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    # Related decision
    related_decision_id: Optional[str] = None
    related_decision_type: Optional[str] = None

    # Metrics
    engagement_metric: Optional[float] = None  # 0-100, from social media
    watch_time_percent: Optional[float] = None  # % watched before skip
    click_through_rate: Optional[float] = None

    timestamp: datetime = Field(default_factory=datetime.now)

    @validator("rating")
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be 1-5")
        return v


class FeedbackPattern(BaseModel):
    """Pattern learned from feedback."""

    pattern_id: str
    category: FeedbackCategory
    pattern_type: str  # "preference", "avoidance", "threshold"

    # Pattern definition
    condition: Dict[str, Any]  # What triggers this pattern
    action: Dict[str, Any]     # What to do when triggered
    confidence: float = Field(ge=0.0, le=1.0)  # How confident in pattern

    # Support
    occurrences: int  # How many times observed
    positive_feedback_count: int
    negative_feedback_count: int

    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_used: datetime = Field(default_factory=datetime.now)


class FeedbackReport(BaseModel):
    """Analysis report from feedback."""

    file_id: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Summary
    total_feedback: int
    positive_count: int
    negative_count: int
    average_rating: float

    # Patterns discovered
    patterns: List[FeedbackPattern] = Field(default_factory=list)

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)

    # Insights
    top_liked_aspects: List[str] = Field(default_factory=list)
    top_disliked_aspects: List[str] = Field(default_factory=list)


# ============================================================================
# Feedback Collector
# ============================================================================

class FeedbackCollector:
    """Collect and store user feedback."""

    def __init__(self, storage_dir: Path):
        """Initialize collector."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_list: List[UserFeedback] = []

    def collect_feedback(self, feedback: UserFeedback) -> str:
        """
        Collect user feedback.

        Args:
            feedback: UserFeedback object

        Returns:
            Feedback ID
        """
        feedback_id = f"{feedback.file_id}_{feedback.scene_id}_{datetime.now().timestamp()}"

        self.feedback_list.append(feedback)

        logger.info(
            f"Collected feedback: {feedback.category} - "
            f"{feedback.feedback_type} (rating: {feedback.rating}/5)"
        )

        # Save to file
        self._save_feedback(feedback_id, feedback)

        return feedback_id

    def get_feedback_for_file(self, file_id: str) -> List[UserFeedback]:
        """Get all feedback for a file."""
        return [f for f in self.feedback_list if f.file_id == file_id]

    def get_feedback_for_scene(self, file_id: str, scene_id: str) -> List[UserFeedback]:
        """Get feedback for specific scene."""
        return [
            f for f in self.feedback_list
            if f.file_id == file_id and f.scene_id == scene_id
        ]

    def get_feedback_by_category(self, category: FeedbackCategory) -> List[UserFeedback]:
        """Get feedback by category."""
        return [f for f in self.feedback_list if f.category == category]

    def get_positive_feedback(self) -> List[UserFeedback]:
        """Get positive feedback."""
        return [
            f for f in self.feedback_list
            if f.feedback_type == FeedbackType.POSITIVE
        ]

    def get_negative_feedback(self) -> List[UserFeedback]:
        """Get negative feedback."""
        return [
            f for f in self.feedback_list
            if f.feedback_type == FeedbackType.NEGATIVE
        ]

    def load_feedback_history(self) -> None:
        """Load feedback from storage."""
        feedback_files = list(self.storage_dir.glob("feedback_*.json"))

        for feedback_file in feedback_files:
            try:
                with open(feedback_file, "r") as f:
                    data = json.load(f)
                    feedback = UserFeedback(**data)
                    self.feedback_list.append(feedback)
            except Exception as e:
                logger.error(f"Failed to load feedback: {str(e)}")

        logger.info(f"Loaded {len(self.feedback_list)} feedback records")

    def _save_feedback(self, feedback_id: str, feedback: UserFeedback) -> None:
        """Save feedback to file."""
        feedback_file = self.storage_dir / f"feedback_{feedback_id}.json"

        try:
            data = feedback.model_dump(mode="json")
            data["timestamp"] = feedback.timestamp.isoformat()

            with open(feedback_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save feedback: {str(e)}")


# ============================================================================
# Feedback Analyzer
# ============================================================================

class FeedbackAnalyzer:
    """Analyze feedback patterns and generate insights."""

    def __init__(self, collector: FeedbackCollector):
        """Initialize analyzer."""
        self.collector = collector

    def analyze_feedback(self, file_id: str) -> FeedbackReport:
        """
        Analyze all feedback for a file.

        Args:
            file_id: File to analyze

        Returns:
            FeedbackReport with insights and patterns
        """
        feedback_list = self.collector.get_feedback_for_file(file_id)

        if not feedback_list:
            logger.warning(f"No feedback found for {file_id}")
            return self._create_empty_report(file_id)

        # Calculate summaries
        positive = len([f for f in feedback_list if f.feedback_type == FeedbackType.POSITIVE])
        negative = len([f for f in feedback_list if f.feedback_type == FeedbackType.NEGATIVE])
        avg_rating = sum(f.rating for f in feedback_list) / len(feedback_list)

        # Extract patterns
        patterns = self._extract_patterns(feedback_list)

        # Generate recommendations
        recommendations = self._generate_recommendations(feedback_list, patterns)

        # Get top liked/disliked aspects
        top_liked = self._get_top_aspects(feedback_list, "positive_aspects")
        top_disliked = self._get_top_aspects(feedback_list, "negative_aspects")

        report = FeedbackReport(
            file_id=file_id,
            total_feedback=len(feedback_list),
            positive_count=positive,
            negative_count=negative,
            average_rating=avg_rating,
            patterns=patterns,
            recommendations=recommendations,
            top_liked_aspects=top_liked,
            top_disliked_aspects=top_disliked,
        )

        logger.info(
            f"Analyzed {len(feedback_list)} feedback items - "
            f"Avg rating: {avg_rating:.1f}/5, Patterns: {len(patterns)}"
        )

        return report

    def _extract_patterns(self, feedback_list: List[UserFeedback]) -> List[FeedbackPattern]:
        """Extract patterns from feedback."""
        patterns = []

        # Count by category and type
        category_counts = {}
        for feedback in feedback_list:
            key = (feedback.category, feedback.feedback_type)
            category_counts[key] = category_counts.get(key, 0) + 1

        # Create patterns for significant feedback
        for (category, ftype), count in category_counts.items():
            if count >= 2:  # Minimum 2 occurrences to be a pattern
                pos_count = len([
                    f for f in feedback_list
                    if f.category == category and f.feedback_type == FeedbackType.POSITIVE
                ])
                neg_count = len([
                    f for f in feedback_list
                    if f.category == category and f.feedback_type == FeedbackType.NEGATIVE
                ])

                confidence = pos_count / count if count > 0 else 0.5

                pattern = FeedbackPattern(
                    pattern_id=f"{category}_{ftype}_{datetime.now().timestamp()}",
                    category=category,
                    pattern_type="preference" if ftype == FeedbackType.POSITIVE else "avoidance",
                    condition={"category": category},
                    action={
                        "if_positive": "replicate",
                        "if_negative": "avoid",
                    },
                    confidence=confidence,
                    occurrences=count,
                    positive_feedback_count=pos_count,
                    negative_feedback_count=neg_count,
                )

                patterns.append(pattern)

        return patterns

    @staticmethod
    def _generate_recommendations(
        feedback_list: List[UserFeedback],
        patterns: List[FeedbackPattern],
    ) -> List[str]:
        """Generate recommendations from feedback."""
        recommendations = []

        # If negative feedback on perspective, recommend trying other angles
        perspective_negative = len([
            f for f in feedback_list
            if f.category == FeedbackCategory.PERSPECTIVE
            and f.feedback_type == FeedbackType.NEGATIVE
        ])
        if perspective_negative >= 2:
            recommendations.append(
                "Try alternative perspective angles - current selection may not match user preference"
            )

        # If scene selection negative, recommend manual review
        scene_negative = len([
            f for f in feedback_list
            if f.category == FeedbackCategory.SCENE_SELECTION
            and f.feedback_type == FeedbackType.NEGATIVE
        ])
        if scene_negative >= 2:
            recommendations.append(
                "Manual scene selection recommended - algorithm selections not matching expectations"
            )

        # If subject detection issues, recommend annotation
        subject_negative = len([
            f for f in feedback_list
            if f.category == FeedbackCategory.SUBJECT_DETECTION
            and f.feedback_type == FeedbackType.NEGATIVE
        ])
        if subject_negative >= 2:
            recommendations.append(
                "Train subject detector with annotated frames to improve accuracy"
            )

        # High rating positive feedback
        high_ratings = len([f for f in feedback_list if f.rating >= 4])
        if high_ratings >= 3:
            recommendations.append(
                "Successful reel generation - consider using similar parameters for similar videos"
            )

        return recommendations

    @staticmethod
    def _get_top_aspects(
        feedback_list: List[UserFeedback], aspect_type: str
    ) -> List[str]:
        """Get most mentioned aspects."""
        aspect_counts = {}

        for feedback in feedback_list:
            aspects = getattr(feedback, aspect_type, [])
            for aspect in aspects:
                aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1

        # Return top 5
        sorted_aspects = sorted(
            aspect_counts.items(), key=lambda x: x[1], reverse=True
        )
        return [aspect for aspect, _ in sorted_aspects[:5]]

    @staticmethod
    def _create_empty_report(file_id: str) -> FeedbackReport:
        """Create empty report."""
        return FeedbackReport(
            file_id=file_id,
            total_feedback=0,
            positive_count=0,
            negative_count=0,
            average_rating=0.0,
        )


# ============================================================================
# Learning Engine
# ============================================================================

class LearningEngine:
    """Learn from feedback and adapt decisions."""

    def __init__(self, collector: FeedbackCollector, analyzer: FeedbackAnalyzer):
        """Initialize learning engine."""
        self.collector = collector
        self.analyzer = analyzer
        self.learned_preferences: Dict[str, Any] = {}
        self.pattern_history: List[FeedbackPattern] = []

    def learn_from_feedback(self, file_id: str) -> Dict[str, Any]:
        """
        Learn from feedback and update preferences.

        Args:
            file_id: File to learn from

        Returns:
            Updated preferences/weights
        """
        # Analyze feedback
        report = self.analyzer.analyze_feedback(file_id)

        # Update preferences based on patterns
        for pattern in report.patterns:
            self._update_preference(pattern)
            self.pattern_history.append(pattern)

        logger.info(f"Learning complete: Updated {len(report.patterns)} patterns")

        return self.learned_preferences

    def apply_learned_preferences(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply learned preferences to configuration.

        Args:
            config: Original configuration

        Returns:
            Updated configuration with learned adjustments
        """
        updated_config = config.copy()

        # Adjust weights based on learned preferences
        if "perspective_scoring_weights" in updated_config:
            weights = updated_config["perspective_scoring_weights"]

            # If perspective preference learned
            if "perspective_preference" in self.learned_preferences:
                pref = self.learned_preferences["perspective_preference"]
                weights["subject"] += pref.get("subject_adjustment", 0)
                weights["scenery"] += pref.get("scenery_adjustment", 0)

        # Adjust thresholds
        if "min_confidence_threshold" in self.learned_preferences:
            threshold = self.learned_preferences["min_confidence_threshold"]
            updated_config["min_confidence_threshold"] = threshold

        logger.info(f"Applied {len(self.learned_preferences)} learned preferences")

        return updated_config

    def get_learned_weights(self) -> Dict[str, float]:
        """Get adaptive weights based on learned feedback."""
        weights = {
            "subject": 0.40,
            "scenery": 0.20,
            "composition": 0.25,
            "motion": 0.15,
        }

        # Adjust based on learned preferences
        if "perspective_preference" in self.learned_preferences:
            pref = self.learned_preferences["perspective_preference"]
            weights.update(pref)

        return weights

    def _update_preference(self, pattern: FeedbackPattern) -> None:
        """Update preference from pattern."""
        if pattern.confidence < 0.5:
            return  # Only update with confident patterns

        if pattern.category == FeedbackCategory.PERSPECTIVE:
            if "perspective_preference" not in self.learned_preferences:
                self.learned_preferences["perspective_preference"] = {}

            # Increase weight for patterns that worked well
            if pattern.pattern_type == "preference":
                self.learned_preferences["perspective_preference"]["subject"] = \
                    self.learned_preferences["perspective_preference"].get("subject", 0.40) + 0.05

        elif pattern.category == FeedbackCategory.SCENERY_QUALITY:
            self.learned_preferences["min_scenery_quality"] = 6.0

        elif pattern.category == FeedbackCategory.SUBJECT_DETECTION:
            if pattern.pattern_type == "avoidance":
                self.learned_preferences["subject_detection_confidence_threshold"] = 0.8

        logger.info(f"Updated preference from pattern: {pattern.pattern_id}")

    def suggest_parameters(self, file_id: str) -> Dict[str, Any]:
        """
        Suggest parameters for next reel based on learned preferences.

        Args:
            file_id: File to generate suggestions for

        Returns:
            Suggested parameters
        """
        suggestions = {
            "description": "Suggested parameters based on learned feedback",
            "parameters": self.learned_preferences.copy(),
        }

        # Add recommendations from feedback
        feedback = self.collector.get_feedback_for_file(file_id)
        report = self.analyzer.analyze_feedback(file_id)

        if report.recommendations:
            suggestions["recommendations"] = report.recommendations

        if report.top_liked_aspects:
            suggestions["emphasize"] = report.top_liked_aspects

        if report.top_disliked_aspects:
            suggestions["avoid"] = report.top_disliked_aspects

        return suggestions
