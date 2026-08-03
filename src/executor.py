"""Main executor - runs complete pipeline with QA agent."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.utils.logger import get_logger, setup_logging
from src.pipeline import Pipeline
from src.analytics import (
    create_full_analytics_flow,
    FlowExecutorImpl,
    Insta360FormatDetector,
    SubjectDetector,
    SceneryAnalyzer,
    PerspectiveSelectorComponent,
    AnalysisInput,
    AnalyticsConfig,
    AdaptiveReelGenerator,
)
from src.agents import (
    ExecutionContext,
    PipelineOrchestrator,
    QAReasonerAgent,
    QAActorAgent,
    QAAssessmentAgent,
)

logger = get_logger("executor")


class ReelExecutor:
    """Main executor for reel generation with QA."""

    def __init__(
        self,
        video_path: Path,
        data_dir: Path = Path("data"),
        max_duration: float = 15.0,
    ):
        """Initialize executor."""
        self.video_path = Path(video_path)
        self.data_dir = Path(data_dir)
        self.max_duration = max_duration

        # Initialize pipeline
        self.pipeline = Pipeline(
            checkpoint_dir=self.data_dir / "working" / "checkpoints",
            data_dir=self.data_dir,
            max_reel_duration_seconds=max_duration,
        )

        # Initialize QA agents
        feedback_dir = self.data_dir / "feedback"
        self.qa_reasoner = QAReasonerAgent(feedback_dir)
        self.qa_actor = QAActorAgent(feedback_dir)
        self.qa_assessor = QAAssessmentAgent(feedback_dir)

        # Initialize orchestrator
        self.orchestrator = PipelineOrchestrator(
            reasoner=self.qa_reasoner,
            actor=self.qa_actor,
            cache_dir=self.data_dir / "cache",
        )

        self.results = {}

    def run(self) -> Dict[str, Any]:
        """Execute complete pipeline."""
        logger.info("=" * 80)
        logger.info("REEL GENERATION PIPELINE")
        logger.info("=" * 80)

        try:
            # Step 1: Process with main pipeline
            logger.info("\n[1/3] Running main analytics pipeline...")
            pipeline_result = self._run_analytics_pipeline()

            # Step 2: Run QA with ReACT
            logger.info("\n[2/3] Running QA assessment with ReACT agent...")
            qa_result = self._run_qa_assessment()

            # Step 3: Generate report
            logger.info("\n[3/3] Generating final report...")
            report = self._generate_report(pipeline_result, qa_result)

            self.results = {
                "success": True,
                "pipeline": pipeline_result,
                "qa": qa_result,
                "report": report,
            }

            return self.results

        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _run_analytics_pipeline(self) -> Dict[str, Any]:
        """Run main analytics pipeline."""
        logger.info(f"Input video: {self.video_path}")
        logger.info(f"Video exists: {self.video_path.exists()}")

        # Generate file ID
        file_id = f"file_{self.video_path.stem}_{int(datetime.now().timestamp() * 1e9)}"
        logger.info(f"File ID: {file_id}")

        # Run pipeline
        result = self.pipeline.process_file(
            file_id=file_id,
            input_path=self.video_path,
            resume=False,
        )

        if not result["success"]:
            logger.error(f"Pipeline failed: {result.get('error')}")
            raise RuntimeError(f"Pipeline failed: {result.get('error')}")

        logger.info("Pipeline execution complete")
        logger.info(f"Stages completed: {list(result.get('stages', {}).keys())}")

        return {
            "file_id": file_id,
            "status": "success",
            "stages": result.get("stages", {}),
        }

    def _run_qa_assessment(self) -> Dict[str, any]:
        """Run QA assessment with ReACT."""
        logger.info("Initializing QA assessment context...")

        # Create execution context
        context = ExecutionContext(
            file_id=self.results["pipeline"]["file_id"],
            video_path=str(self.video_path),
            stage="qa_assessment",
        )

        # Run ReACT orchestrator
        logger.info("Starting ReACT orchestration...")
        qa_result = self.orchestrator.run_pipeline(context)

        logger.info("ReACT orchestration complete")

        return {
            "status": "complete",
            "react_result": qa_result.get("react_result", {}),
            "pipeline_state": qa_result.get("pipeline_state", {}),
            "cache_stats": qa_result.get("cache_stats", {}),
        }

    def _generate_report(
        self,
        pipeline_result: Dict[str, any],
        qa_result: Dict[str, any],
    ) -> Dict[str, any]:
        """Generate final report."""
        logger.info("Generating final report...")

        # Extract key metrics
        react_result = qa_result.get("react_result", {})
        quality_score = react_result.get("quality_score", 0)
        iterations = react_result.get("iterations", 0)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "video": str(self.video_path.name),
                "file_id": pipeline_result.get("file_id"),
                "quality_score": quality_score,
                "qa_iterations": iterations,
                "status": "success" if quality_score >= 7.0 else "needs_improvement",
            },
            "pipeline": {
                "stages_executed": list(pipeline_result.get("stages", {}).keys()),
                "all_stages_passed": all(
                    v.get("success") for v in pipeline_result.get("stages", {}).values()
                ),
            },
            "qa": {
                "iterations": iterations,
                "quality_score": quality_score,
                "cache_stats": qa_result.get("cache_stats", {}),
            },
            "recommendations": self._generate_recommendations(quality_score),
        }

        return report

    @staticmethod
    def _generate_recommendations(quality_score: float) -> List[str]:
        """Generate recommendations based on quality score."""
        recommendations = []

        if quality_score >= 8.0:
            recommendations.append("Reel quality is excellent - ready for publishing")
        elif quality_score >= 7.0:
            recommendations.append("Reel quality is good - can be published with minor review")
        elif quality_score >= 5.0:
            recommendations.append("Reel quality is acceptable - recommend feedback collection and regeneration")
        else:
            recommendations.append("Reel quality needs significant improvement - collect user feedback and regenerate")

        return recommendations

    def save_results(self, output_path: Optional[Path] = None) -> Path:
        """Save results to JSON."""
        if output_path is None:
            output_path = self.data_dir / "output" / "execution_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to: {output_path}")
        return output_path

    def print_summary(self) -> None:
        """Print execution summary."""
        if not self.results or not self.results.get("success"):
            logger.error("No successful execution to summarize")
            return

        report = self.results.get("report", {})
        summary = report.get("summary", {})

        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Video: {summary.get('video')}")
        logger.info(f"File ID: {summary.get('file_id')}")
        logger.info(f"Quality Score: {summary.get('quality_score'):.1f}/10")
        logger.info(f"QA Iterations: {summary.get('qa_iterations')}")
        logger.info(f"Status: {summary.get('status')}")
        logger.info("")
        logger.info("Recommendations:")
        for rec in report.get("recommendations", []):
            logger.info(f"  - {rec}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    import logging
    setup_logging(level=logging.DEBUG)

    # Test video path
    video_path = Path("C:/Users/swamx/OneDrive/Documents/Camera01/VID_20250727_170303_00_033.insv")

    if not video_path.exists():
        logger.error(f"Video not found: {video_path}")
        return

    # Create executor
    executor = ReelExecutor(
        video_path=video_path,
        data_dir=Path("data"),
        max_duration=0,  # Unlimited
    )

    # Run pipeline
    results = executor.run()

    # Print summary
    if results.get("success"):
        executor.print_summary()
        executor.save_results()
    else:
        logger.error(f"Execution failed: {results.get('error')}")


if __name__ == "__main__":
    main()
