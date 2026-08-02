"""Abstract base classes and Pydantic models for analytics system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Generic, TypeVar
from pathlib import Path
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, validator


# ============================================================================
# Enums
# ============================================================================

class AnalysisStage(str, Enum):
    """Pipeline stage names."""
    STAGE_0_5 = "stage0_insta360_conversion"
    STAGE_3 = "stage3_vision_editor"
    CUSTOM = "custom"


class DecisionType(str, Enum):
    """Types of analytics decisions."""
    FORMAT_DETECTION = "360_detection"
    PERSPECTIVE_SELECTION = "perspective_selection"
    FORMAT_CONVERSION = "360_conversion"
    SUBJECT_DETECTION = "subject_detection"
    SCENERY_ANALYSIS = "scenery_analysis"
    SCENE_SCORING = "scene_scoring"


class ConfidenceLevel(str, Enum):
    """Confidence classification."""
    VERY_HIGH = "very_high"      # 0.90-1.00
    HIGH = "high"                 # 0.75-0.89
    MEDIUM = "medium"             # 0.50-0.74
    LOW = "low"                   # 0.25-0.49
    VERY_LOW = "very_low"         # 0.00-0.24


# ============================================================================
# Pydantic Models for Configuration
# ============================================================================

class AnalyticsConfig(BaseModel):
    """Configuration for analytics pipeline."""

    model_config = ConfigDict(frozen=False)

    enabled: bool = True
    save_reports: bool = True
    report_formats: List[str] = Field(default_factory=lambda: ["json", "markdown"])

    scene_analyzer_enabled: bool = True
    perspective_selector_enabled: bool = True
    traceability_enabled: bool = True

    # Scene analyzer config
    face_detection_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    min_sharpness_for_quality: float = Field(default=5.0, ge=0.0, le=10.0)

    # Perspective selector config
    perspective_scoring_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "subject": 0.40,
            "scenery": 0.20,
            "composition": 0.25,
            "motion": 0.15,
        }
    )
    prefer_subjects_in_360: bool = True
    fov_default: int = Field(default=90, ge=45, le=180)

    # Traceability config
    min_confidence_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    track_low_confidence: bool = True

    @validator("report_formats")
    def validate_formats(cls, v):
        """Validate report format choices."""
        valid = {"json", "markdown", "csv"}
        if not all(fmt in valid for fmt in v):
            raise ValueError(f"Report formats must be in {valid}")
        return v


class AnalysisInput(BaseModel):
    """Input data for analysis."""

    file_id: str
    file_path: Path
    scene_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisOutput(BaseModel):
    """Output data from analysis."""

    analysis_id: str
    stage: AnalysisStage
    decision_type: DecisionType
    decision: Any
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = self.model_dump(by_alias=False)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class FlowConfig(BaseModel):
    """Configuration for analytics flow."""

    model_config = ConfigDict(frozen=False)

    name: str
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True

    analytics_config: AnalyticsConfig = Field(default_factory=AnalyticsConfig)

    # Flow execution settings
    stop_on_error: bool = False
    timeout_seconds: int = Field(default=300, ge=1)
    retry_count: int = Field(default=0, ge=0)

    # Logging and traceability
    log_decisions: bool = True
    track_performance: bool = True


# ============================================================================
# Abstract Base Classes
# ============================================================================

class AnalyticsComponent(ABC):
    """Abstract base class for all analytics components."""

    def __init__(self, config: AnalyticsConfig):
        """Initialize component with configuration."""
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """
        Process analysis input and return output.

        Args:
            input_data: Input for analysis

        Returns:
            AnalysisOutput with decision and confidence
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input before processing."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get component information."""
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
        }


class Analyzer(AnalyticsComponent, ABC):
    """Abstract base class for analyzers (extract features)."""

    @abstractmethod
    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """
        Perform analysis and extract features.

        Args:
            input_data: Input for analysis

        Returns:
            Dictionary of extracted features
        """
        pass


class Scorer(AnalyticsComponent, ABC):
    """Abstract base class for scorers (evaluate quality)."""

    @abstractmethod
    def score(self, input_data: AnalysisInput, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score based on analysis results.

        Args:
            input_data: Original input
            analysis_results: Results from analyzer

        Returns:
            Dictionary with scores
        """
        pass


class Selector(AnalyticsComponent, ABC):
    """Abstract base class for selectors (choose best option)."""

    @abstractmethod
    def select(self, input_data: AnalysisInput, candidates: List[str], scores: Dict[str, float]) -> str:
        """
        Select best option from candidates.

        Args:
            input_data: Input for selection
            candidates: List of candidate options
            scores: Scores for each candidate

        Returns:
            Selected candidate
        """
        pass


class Detector(Analyzer, ABC):
    """Abstract base class for object/subject detection."""

    @abstractmethod
    def detect(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """
        Detect objects/subjects in input.

        Returns:
            Detection results with counts and confidence
        """
        pass


class Reporter(ABC):
    """Abstract base class for report generation."""

    def __init__(self, output_dir: Path):
        """Initialize reporter."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self, data: Dict[str, Any], file_id: str) -> Path:
        """
        Generate report from data.

        Args:
            data: Data to report
            file_id: File identifier for naming

        Returns:
            Path to generated report
        """
        pass

    @abstractmethod
    def validate(self, report_path: Path) -> bool:
        """Validate generated report."""
        pass


# ============================================================================
# Flow Orchestration
# ============================================================================

T = TypeVar("T", bound=AnalyticsComponent)


class AnalyticsNode(BaseModel):
    """Node in analytics flow."""

    name: str
    component_type: str  # "analyzer", "scorer", "selector", "detector"
    enabled: bool = True
    input_from: Optional[str] = None  # Name of previous node or None for start
    config: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsFlow(BaseModel):
    """DAG-based analytics flow configuration."""

    name: str
    description: str = ""
    version: str = "1.0.0"
    nodes: List[AnalyticsNode]

    flow_config: FlowConfig = Field(default_factory=FlowConfig)

    def get_execution_order(self) -> List[str]:
        """Get topological sort of nodes for execution."""
        # Build dependency graph
        graph = {node.name: node.input_from for node in self.nodes}

        # Topological sort
        visited = set()
        order = []

        def visit(node_name):
            if node_name in visited:
                return
            visited.add(node_name)

            # Visit dependencies first
            for name, depends_on in graph.items():
                if depends_on == node_name:
                    visit(name)

            order.append(node_name)

        for node in self.nodes:
            if node.enabled:
                visit(node.name)

        return order

    def get_node(self, name: str) -> Optional[AnalyticsNode]:
        """Get node by name."""
        return next((n for n in self.nodes if n.name == name), None)


class FlowExecutor(ABC):
    """Abstract base class for flow execution."""

    def __init__(self, flow: AnalyticsFlow):
        """Initialize executor with flow."""
        self.flow = flow
        self.components: Dict[str, AnalyticsComponent] = {}
        self.results: Dict[str, AnalysisOutput] = {}

    @abstractmethod
    def register_component(self, name: str, component: AnalyticsComponent) -> None:
        """Register component for execution."""
        pass

    @abstractmethod
    def execute(self, input_data: AnalysisInput) -> Dict[str, AnalysisOutput]:
        """Execute flow and return results."""
        pass

    @abstractmethod
    def validate_flow(self) -> bool:
        """Validate flow configuration."""
        pass


# ============================================================================
# Performance Monitoring
# ============================================================================

class PerformanceMetrics(BaseModel):
    """Performance metrics for components."""

    component_name: str
    execution_time_ms: float
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    memory_used_mb: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def throughput_items_per_second(self, items: int = 1) -> float:
        """Calculate throughput."""
        if self.execution_time_ms == 0:
            return 0.0
        return items / (self.execution_time_ms / 1000.0)


class ExecutionStats(BaseModel):
    """Execution statistics for flow."""

    flow_name: str
    start_time: datetime
    end_time: datetime
    total_items_processed: int = 0
    successful_items: int = 0
    failed_items: int = 0
    component_metrics: List[PerformanceMetrics] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Total execution duration."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        if self.total_items_processed == 0:
            return 0.0
        return (self.successful_items / self.total_items_processed) * 100
