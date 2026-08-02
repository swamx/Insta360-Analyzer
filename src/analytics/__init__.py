"""Analytics module for scene understanding and perspective selection."""

# Legacy implementations
from .scene_analyzer import SceneAnalyzer, DetectionResult
from .perspective_selector import PerspectiveSelector, PerspectiveScore
from .traceability import TraceabilityLogger, AnalyticsDecision

# Abstract base classes and core types
from .core import (
    AnalyticsComponent,
    Analyzer,
    Scorer,
    Selector,
    Detector,
    Reporter,
    AnalysisInput,
    AnalysisOutput,
    AnalyticsConfig,
    FlowConfig,
    AnalyticsFlow,
    AnalyticsNode,
    FlowExecutor,
    PerformanceMetrics,
    ExecutionStats,
    AnalysisStage,
    DecisionType,
    ConfidenceLevel,
)

# Flow orchestration
from .flow import (
    FlowExecutorImpl,
    FlowBuilder,
    FlowRegistry,
    create_insta360_perspective_flow,
    create_scene_analytics_flow,
    create_full_analytics_flow,
)

# Concrete implementations
from .implementations import (
    Insta360FormatDetector,
    SubjectDetector,
    SceneryAnalyzer,
    PerspectiveSelectorComponent,
)

# Feedback and learning
from .feedback import (
    UserFeedback,
    FeedbackType,
    FeedbackCategory,
    FeedbackSource,
    FeedbackPattern,
    FeedbackReport,
    FeedbackCollector,
    FeedbackAnalyzer,
    LearningEngine,
)

# Adaptive reel generation
from .adaptive_reel import (
    ReelConfiguration,
    AdaptiveReelGenerator,
    AdaptiveFlowManager,
)

__all__ = [
    # Legacy
    "SceneAnalyzer",
    "DetectionResult",
    "PerspectiveSelector",
    "PerspectiveScore",
    "TraceabilityLogger",
    "AnalyticsDecision",
    # Core abstractions
    "AnalyticsComponent",
    "Analyzer",
    "Scorer",
    "Selector",
    "Detector",
    "Reporter",
    # Data models
    "AnalysisInput",
    "AnalysisOutput",
    "AnalyticsConfig",
    "FlowConfig",
    "AnalyticsFlow",
    "AnalyticsNode",
    "PerformanceMetrics",
    "ExecutionStats",
    # Enums
    "AnalysisStage",
    "DecisionType",
    "ConfidenceLevel",
    # Flow orchestration
    "FlowExecutor",
    "FlowExecutorImpl",
    "FlowBuilder",
    "FlowRegistry",
    "create_insta360_perspective_flow",
    "create_scene_analytics_flow",
    "create_full_analytics_flow",
    # Implementations
    "Insta360FormatDetector",
    "SubjectDetector",
    "SceneryAnalyzer",
    "PerspectiveSelectorComponent",
    # Feedback and learning
    "UserFeedback",
    "FeedbackType",
    "FeedbackCategory",
    "FeedbackSource",
    "FeedbackPattern",
    "FeedbackReport",
    "FeedbackCollector",
    "FeedbackAnalyzer",
    "LearningEngine",
    # Adaptive reel generation
    "ReelConfiguration",
    "AdaptiveReelGenerator",
    "AdaptiveFlowManager",
]
