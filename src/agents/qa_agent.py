"""QA Agent implementations using ReACT pattern."""

from typing import Dict, Any, List
from pathlib import Path

from src.utils.logger import get_logger
from src.analytics import (
    FeedbackCollector,
    FeedbackAnalyzer,
    LearningEngine,
    UserFeedback,
    FeedbackType,
    FeedbackCategory,
    AdaptiveReelGenerator,
)

from .contracts import (
    ReasonerContract,
    ActorContract,
    ExecutionContext,
    ActionType,
    QualityMetrics,
    QualityAssuranceContract,
)

logger = get_logger("agents.qa_agent")


# ============================================================================
# QA Reasoner Agent
# ============================================================================

class QAReasonerAgent(ReasonerContract):
    """QA agent that reasons about reel quality."""

    def __init__(self, feedback_dir: Path):
        """Initialize QA reasoner."""
        self.feedback_dir = Path(feedback_dir)
        self.collector = FeedbackCollector(self.feedback_dir / "feedback")
        self.analyzer = FeedbackAnalyzer(self.collector)
        self.collector.load_feedback_history()

    def reason(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Reason about quality issues.

        ReACT Thought phase:
        - Analyze current state
        - Identify quality gaps
        - Diagnose root causes
        """
        logger.info(f"ReACT Reasoning: Analyzing {context.file_id}")

        # Gather observations
        context.reasoner_memory.add_thought("Starting quality analysis")

        # Analyze existing feedback
        feedback = self.collector.get_feedback_for_file(context.file_id)
        context.reasoner_memory.add_observation("feedback_count", len(feedback))

        if feedback:
            report = self.analyzer.analyze_feedback(context.file_id)
            avg_rating = report.average_rating

            context.reasoner_memory.add_observation("average_rating", avg_rating)
            context.reasoner_memory.add_observation("patterns", len(report.patterns))
            context.reasoner_memory.add_observation("recommendations", report.recommendations)

            # Diagnose issues
            issues = []
            confidence = 0.5

            if avg_rating < 3.0:
                issues.append("Low user satisfaction")
                confidence = 0.9

            if report.patterns:
                for pattern in report.patterns:
                    if pattern.pattern_type == "avoidance":
                        issues.append(f"Avoid {pattern.category.value}")
                        confidence = pattern.confidence

            diagnosis = " | ".join(issues) if issues else "No critical issues"
            next_step = report.recommendations[0] if report.recommendations else "Monitor quality"

        else:
            diagnosis = "No feedback collected yet - need baseline assessment"
            avg_rating = context.quality_score
            confidence = 0.3
            next_step = "Collect initial feedback"

        context.reasoner_memory.add_thought(f"Diagnosis: {diagnosis}")
        context.reasoner_memory.add_thought(f"Next action: {next_step}")

        return {
            "thoughts": context.reasoner_memory.thoughts[-3:],  # Last 3 thoughts
            "observations": context.reasoner_memory.observations,
            "diagnosis": diagnosis,
            "confidence": confidence,
            "next_step": next_step,
            "quality_baseline": avg_rating,
        }

    def evaluate(self, context: ExecutionContext, results: Dict[str, Any]) -> float:
        """
        Evaluate quality of results.

        Score based on:
        - User feedback ratings (40%)
        - Pattern resolution (30%)
        - Content metrics (30%)
        """
        logger.info("ReACT Evaluation: Scoring quality")

        score = 5.0  # Base score

        # Component 1: Feedback score (40%)
        feedback = self.collector.get_feedback_for_file(context.file_id)
        if feedback:
            avg_rating = sum(f.rating for f in feedback) / len(feedback)
            feedback_score = (avg_rating / 5.0) * 10.0  # Convert to 1-10 scale
            score += feedback_score * 0.4
        else:
            score += 5.0 * 0.4  # Neutral if no feedback

        # Component 2: Pattern resolution (30%)
        report = self.analyzer.analyze_feedback(context.file_id)
        resolved_patterns = len([p for p in report.patterns if p.positive_feedback_count > p.negative_feedback_count])
        total_patterns = len(report.patterns)
        resolution_rate = (resolved_patterns / total_patterns) if total_patterns > 0 else 0.5
        pattern_score = resolution_rate * 10.0
        score += pattern_score * 0.3

        # Component 3: Content metrics (30%)
        metrics_score = context.quality_score
        score += metrics_score * 0.3

        # Normalize to 0-10
        final_score = min(10.0, max(0.0, score))

        context.reasoner_memory.add_observation("evaluation_score", final_score)
        logger.info(f"Quality score: {final_score:.1f}/10")

        return final_score


# ============================================================================
# QA Actor Agent
# ============================================================================

class QAActorAgent(ActorContract):
    """QA agent that takes corrective actions."""

    def __init__(self, feedback_dir: Path):
        """Initialize QA actor."""
        self.feedback_dir = Path(feedback_dir)
        self.generator = AdaptiveReelGenerator(self.feedback_dir)
        self.learning_engine = self.generator.learning_engine

    def act(self, context: ExecutionContext, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take corrective action.

        ReACT Action phase:
        - Execute improvements
        - Collect feedback
        - Learn from results
        """
        logger.info(f"ReACT Acting: Taking corrective action")

        next_step = reasoning.get("next_step", "Monitor")
        diagnosis = reasoning.get("diagnosis", "")

        # Determine action type
        action_type = self._map_to_action(next_step)

        try:
            if action_type == ActionType.ANALYZE:
                result = self._analyze_action(context)

            elif action_type == ActionType.LEARN:
                result = self._learn_action(context)

            elif action_type == ActionType.REGENERATE:
                result = self._regenerate_action(context, diagnosis)

            elif action_type == ActionType.FEEDBACK_COLLECT:
                result = self._feedback_action(context)

            elif action_type == ActionType.COMPARE:
                result = self._compare_action(context)

            else:
                result = {"action": "monitor", "result": "No action needed", "success": True}

            context.actor_memory.add_action(action_type.value, {"diagnosis": diagnosis})

            return {
                "action_type": action_type.value,
                "action": result.get("action"),
                "result": result.get("result"),
                "success": result.get("success", True),
                "feedback": result.get("feedback", ""),
            }

        except Exception as e:
            logger.error(f"Action failed: {str(e)}")
            context.actor_memory.add_error(str(e))

            return {
                "action_type": action_type.value,
                "action": "error",
                "result": str(e),
                "success": False,
                "feedback": "Action execution failed",
            }

    def can_act(self, action_type: ActionType) -> bool:
        """Check if agent can perform action."""
        supported = {
            ActionType.ANALYZE,
            ActionType.LEARN,
            ActionType.REGENERATE,
            ActionType.FEEDBACK_COLLECT,
            ActionType.COMPARE,
        }
        return action_type in supported

    def _map_to_action(self, step: str) -> ActionType:
        """Map reasoning step to action type."""
        step_lower = step.lower()

        if "collect" in step_lower or "feedback" in step_lower:
            return ActionType.FEEDBACK_COLLECT
        elif "learn" in step_lower or "adapt" in step_lower:
            return ActionType.LEARN
        elif "regenerate" in step_lower or "improve" in step_lower:
            return ActionType.REGENERATE
        elif "compare" in step_lower or "test" in step_lower:
            return ActionType.COMPARE
        else:
            return ActionType.ANALYZE

    def _analyze_action(self, context: ExecutionContext) -> Dict[str, Any]:
        """Analyze current state."""
        analysis = self.generator.analyze_reel_feedback(context.file_id)

        return {
            "action": "analyze",
            "result": "Quality analysis complete",
            "success": True,
            "feedback": f"Found {len(analysis.get('patterns', []))} patterns",
            "data": analysis,
        }

    def _learn_action(self, context: ExecutionContext) -> Dict[str, Any]:
        """Learn from feedback."""
        adaptation = self.generator.learn_and_adapt(context.file_id)

        return {
            "action": "learn",
            "result": "Learning complete",
            "success": True,
            "feedback": f"Updated {len(adaptation.get('learned_preferences', {}))} preferences",
            "data": adaptation,
        }

    def _regenerate_action(self, context: ExecutionContext, diagnosis: str) -> Dict[str, Any]:
        """Regenerate reel with improvements."""
        try:
            # Generate adaptive config
            config = self.generator.generate_adaptive_config(
                context.file_id,
                context.analysis_results.get("scenes", []),
            )

            return {
                "action": "regenerate",
                "result": "Reel regeneration prepared",
                "success": True,
                "feedback": f"New config ready: {config.perspective} perspective",
                "data": {"config": config.to_dict()},
            }

        except Exception as e:
            logger.error(f"Regeneration failed: {str(e)}")
            return {
                "action": "regenerate",
                "result": "Regeneration failed",
                "success": False,
                "feedback": str(e),
            }

    def _feedback_action(self, context: ExecutionContext) -> Dict[str, Any]:
        """Collect feedback."""
        current_feedback = self.generator.collector.get_feedback_for_file(context.file_id)

        return {
            "action": "collect_feedback",
            "result": "Feedback collection status",
            "success": True,
            "feedback": f"Collected {len(current_feedback)} feedback items",
            "data": {"feedback_count": len(current_feedback)},
        }

    def _compare_action(self, context: ExecutionContext) -> Dict[str, Any]:
        """Compare versions (A/B test)."""
        return {
            "action": "compare",
            "result": "Comparison ready",
            "success": True,
            "feedback": "A/B test metrics prepared",
            "data": {"comparison_ready": True},
        }


# ============================================================================
# QA Assessment Agent
# ============================================================================

class QAAssessmentAgent(QualityAssuranceContract):
    """Comprehensive QA assessment agent."""

    def __init__(self, feedback_dir: Path):
        """Initialize QA assessment agent."""
        self.feedback_dir = Path(feedback_dir)
        self.analyzer = FeedbackAnalyzer(
            FeedbackCollector(feedback_dir / "feedback")
        )

    def assess_quality(self, context: ExecutionContext) -> QualityMetrics:
        """Assess overall quality."""
        logger.info("QA Assessment: Assessing reel quality")

        criteria_scores = {
            "perspective": self._score_perspective(context),
            "scene_selection": self._score_scenes(context),
            "subject_detection": self._score_subjects(context),
            "scenery_quality": self._score_scenery(context),
            "overall_engagement": self._score_engagement(context),
        }

        issues = self.identify_issues(context)
        recommendations = self.recommend_improvements(context)

        overall_score = sum(criteria_scores.values()) / len(criteria_scores)

        return QualityMetrics(
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            issues_found=issues,
            recommendations=recommendations,
            confidence=0.85,
        )

    def identify_issues(self, context: ExecutionContext) -> List[str]:
        """Identify quality issues."""
        issues = []

        if context.quality_score < 5.0:
            issues.append("Overall quality below acceptable threshold")

        # Check specific issues
        if context.analysis_results.get("has_perspective_issues"):
            issues.append("Perspective selection not optimal")

        if context.analysis_results.get("has_subject_issues"):
            issues.append("Subject detection confidence low")

        return issues

    def recommend_improvements(self, context: ExecutionContext) -> List[str]:
        """Recommend improvements."""
        recommendations = []

        if context.quality_score < 7.0:
            recommendations.append("Regenerate reel with adaptive configuration")

        if context.analysis_results.get("low_engagement"):
            recommendations.append("Increase scene action/motion content")

        if len(context.feedback_collected) < 3:
            recommendations.append("Collect more user feedback for accurate assessment")

        return recommendations

    @staticmethod
    def _score_perspective(context: ExecutionContext) -> float:
        """Score perspective quality."""
        return context.analysis_results.get("perspective_score", 5.0)

    @staticmethod
    def _score_scenes(context: ExecutionContext) -> float:
        """Score scene selection."""
        return context.analysis_results.get("scene_score", 5.0)

    @staticmethod
    def _score_subjects(context: ExecutionContext) -> float:
        """Score subject detection."""
        return context.analysis_results.get("subject_score", 5.0)

    @staticmethod
    def _score_scenery(context: ExecutionContext) -> float:
        """Score scenery quality."""
        return context.analysis_results.get("scenery_score", 5.0)

    @staticmethod
    def _score_engagement(context: ExecutionContext) -> float:
        """Score engagement potential."""
        engagement_metrics = context.analysis_results.get("engagement", {})
        watch_time = engagement_metrics.get("avg_watch_time", 50)
        return (watch_time / 100) * 10.0
