"""Detailed traceability and monitoring for analytics decisions."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

from src.utils.logger import get_logger

logger = get_logger("analytics.traceability")


@dataclass
class AnalyticsDecision:
    """Record of an analytics decision with full traceability."""
    timestamp: str
    stage: str  # stage0_insta360, stage2_scene, stage3_vision, etc.
    scene_id: str
    decision_type: str  # "perspective_selection", "scene_scoring", "subject_detection", etc.
    inputs: Dict[str, Any]
    analysis_results: Dict[str, Any]
    decision: Any
    confidence: float  # 0-1
    rationale: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class TraceabilityLogger:
    """Log and track all analytics decisions with full traceability."""

    def __init__(self, output_dir: Path):
        """
        Initialize traceability logger.

        Args:
            output_dir: Directory to store traceability logs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.decisions: List[AnalyticsDecision] = []

    def log_decision(
        self,
        stage: str,
        scene_id: str,
        decision_type: str,
        inputs: Dict[str, Any],
        analysis_results: Dict[str, Any],
        decision: Any,
        confidence: float,
        rationale: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsDecision:
        """
        Log an analytics decision.

        Args:
            stage: Pipeline stage (e.g., "stage0_insta360")
            scene_id: Unique scene identifier
            decision_type: Type of decision
            inputs: Input data used for decision
            analysis_results: Raw analysis results
            decision: Final decision made
            confidence: Confidence in decision (0-1)
            rationale: Explanation of decision
            metadata: Optional additional metadata

        Returns:
            AnalyticsDecision record
        """
        decision_record = AnalyticsDecision(
            timestamp=datetime.now().isoformat(),
            stage=stage,
            scene_id=scene_id,
            decision_type=decision_type,
            inputs=inputs,
            analysis_results=analysis_results,
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            metadata=metadata or {},
        )

        self.decisions.append(decision_record)

        logger.info(
            f"[{stage}] {decision_type}: {decision} "
            f"(confidence={confidence:.2f}, scene={scene_id})"
        )

        return decision_record

    def log_perspective_selection(
        self,
        scene_id: str,
        video_path: str,
        frame_analysis: Optional[Dict],
        perspective_scores: Dict[str, float],
        selected_perspective: str,
        rationale: str,
    ) -> AnalyticsDecision:
        """Log perspective selection decision."""
        return self.log_decision(
            stage="stage0_insta360_conversion",
            scene_id=scene_id,
            decision_type="perspective_selection",
            inputs={
                "video_path": video_path,
                "frame_analysis_available": frame_analysis is not None,
            },
            analysis_results={
                "frame_analysis": frame_analysis,
                "perspective_scores": perspective_scores,
            },
            decision=selected_perspective,
            confidence=min(1.0, max(perspective_scores.values()) / 10.0),
            rationale=rationale,
            metadata={
                "all_perspectives": list(perspective_scores.keys()),
                "top_3": sorted(perspective_scores.items(), key=lambda x: x[1], reverse=True)[:3],
            }
        )

    def log_subject_detection(
        self,
        scene_id: str,
        frame_path: str,
        has_subjects: bool,
        subject_count: int,
        confidence: float,
        quality_metrics: Dict[str, float],
    ) -> AnalyticsDecision:
        """Log subject/human detection."""
        return self.log_decision(
            stage="stage3_vision_editor",
            scene_id=scene_id,
            decision_type="subject_detection",
            inputs={
                "frame_path": frame_path,
                "detection_method": "opencv_cascades",
            },
            analysis_results=quality_metrics,
            decision={
                "has_subjects": has_subjects,
                "count": subject_count,
            },
            confidence=confidence,
            rationale=f"Detected {subject_count} subjects" if has_subjects else "No subjects detected",
        )

    def log_scenery_analysis(
        self,
        scene_id: str,
        frame_path: str,
        scenery_score: float,
        composition_score: float,
        dominant_colors: List[str],
        brightness: float,
        contrast: float,
    ) -> AnalyticsDecision:
        """Log scenery and composition analysis."""
        return self.log_decision(
            stage="stage3_vision_editor",
            scene_id=scene_id,
            decision_type="scenery_analysis",
            inputs={
                "frame_path": frame_path,
                "analysis_method": "cv2_analysis",
            },
            analysis_results={
                "brightness": brightness,
                "contrast": contrast,
                "dominant_colors": dominant_colors,
            },
            decision={
                "scenery_score": scenery_score,
                "composition_score": composition_score,
            },
            confidence=min(1.0, (scenery_score + composition_score) / 20.0),
            rationale=f"Scenery: {scenery_score:.1f}/10, Composition: {composition_score:.1f}/10. "
                     f"Brightness: {brightness:.0f}, Contrast: {contrast:.1f}",
        )

    def log_scene_scoring(
        self,
        scene_id: str,
        beauty_score: float,
        action_score: float,
        emotion_score: float,
        stability_score: float,
        clarity_score: float,
        overall_score: float,
        rationale: str,
    ) -> AnalyticsDecision:
        """Log scene quality scoring."""
        return self.log_decision(
            stage="stage3_vision_editor",
            scene_id=scene_id,
            decision_type="scene_scoring",
            inputs={
                "scoring_method": "professional_editor_model",
            },
            analysis_results={
                "beauty": beauty_score,
                "action": action_score,
                "emotion": emotion_score,
                "stability": stability_score,
                "clarity": clarity_score,
            },
            decision=overall_score,
            confidence=min(1.0, overall_score / 10.0),
            rationale=rationale,
            metadata={
                "dimension_breakdown": {
                    "beauty": beauty_score,
                    "action": action_score,
                    "emotion": emotion_score,
                    "stability": stability_score,
                    "clarity": clarity_score,
                }
            }
        )

    def save_report(self, file_id: str) -> Path:
        """
        Save complete traceability report.

        Args:
            file_id: Unique file identifier

        Returns:
            Path to saved report
        """
        report = {
            "file_id": file_id,
            "generated_at": datetime.now().isoformat(),
            "total_decisions": len(self.decisions),
            "decisions_by_stage": self._group_by_stage(),
            "decisions_by_type": self._group_by_type(),
            "all_decisions": [d.to_dict() for d in self.decisions],
            "summary": self._create_summary(),
        }

        report_path = self.output_dir / f"{file_id}_traceability_report.json"

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Traceability report saved: {report_path}")
        return report_path

    def _group_by_stage(self) -> Dict[str, int]:
        """Count decisions by pipeline stage."""
        counts = {}
        for decision in self.decisions:
            stage = decision.stage
            counts[stage] = counts.get(stage, 0) + 1
        return counts

    def _group_by_type(self) -> Dict[str, int]:
        """Count decisions by type."""
        counts = {}
        for decision in self.decisions:
            dtype = decision.decision_type
            counts[dtype] = counts.get(dtype, 0) + 1
        return counts

    def _create_summary(self) -> Dict[str, Any]:
        """Create summary statistics."""
        if not self.decisions:
            return {}

        confidences = [d.confidence for d in self.decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "total_decisions": len(self.decisions),
            "average_confidence": avg_confidence,
            "min_confidence": min(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "low_confidence_decisions": sum(1 for c in confidences if c < 0.5),
        }

    def generate_markdown_report(self, file_id: str) -> Path:
        """
        Generate human-readable markdown report.

        Args:
            file_id: Unique file identifier

        Returns:
            Path to markdown report
        """
        lines = [
            "# Analytics Traceability Report",
            f"**File ID**: {file_id}",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Total Decisions**: {len(self.decisions)}",
            "",
            "## Summary",
            "",
        ]

        summary = self._create_summary()
        lines.extend([
            f"- **Average Confidence**: {summary.get('average_confidence', 0):.2f}",
            f"- **Low Confidence Decisions** (<50%): {summary.get('low_confidence_decisions', 0)}",
            "",
            "## Decisions by Stage",
            "",
        ])

        for stage, count in sorted(self._group_by_stage().items()):
            lines.append(f"- **{stage}**: {count} decisions")

        lines.extend(["", "## Decisions by Type", ""])

        for dtype, count in sorted(self._group_by_type().items()):
            lines.append(f"- **{dtype}**: {count} decisions")

        lines.extend(["", "## Detailed Decisions", ""])

        for decision in self.decisions:
            lines.extend([
                f"### {decision.decision_type.replace('_', ' ').title()}",
                f"**Scene**: {decision.scene_id}",
                f"**Time**: {decision.timestamp}",
                f"**Stage**: {decision.stage}",
                f"**Decision**: {decision.decision}",
                f"**Confidence**: {decision.confidence:.2f}",
                f"**Rationale**: {decision.rationale}",
                "",
            ])

        report_path = self.output_dir / f"{file_id}_traceability_report.md"

        with open(report_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown report saved: {report_path}")
        return report_path

    def export_decisions(self, file_id: str, format: str = "json") -> Path:
        """
        Export decisions in specified format.

        Args:
            file_id: Unique file identifier
            format: Export format ("json" or "csv")

        Returns:
            Path to exported file
        """
        if format == "json":
            return self.save_report(file_id)
        elif format == "csv":
            return self._export_csv(file_id)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_csv(self, file_id: str) -> Path:
        """Export decisions as CSV."""
        import csv

        csv_path = self.output_dir / f"{file_id}_traceability.csv"

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "stage",
                    "scene_id",
                    "decision_type",
                    "decision",
                    "confidence",
                    "rationale",
                ]
            )

            writer.writeheader()
            for decision in self.decisions:
                writer.writerow({
                    "timestamp": decision.timestamp,
                    "stage": decision.stage,
                    "scene_id": decision.scene_id,
                    "decision_type": decision.decision_type,
                    "decision": str(decision.decision),
                    "confidence": f"{decision.confidence:.2f}",
                    "rationale": decision.rationale,
                })

        logger.info(f"CSV export saved: {csv_path}")
        return csv_path
