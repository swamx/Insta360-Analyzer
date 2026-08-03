# Flow Architecture Guide - Abstract Classes & Flow Orchestration

**Overview**: Modern, extensible analytics framework using abstract base classes, Pydantic validation, and DAG-based flow orchestration.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AnalyticsComponent (ABC)                  │
│                  (Base for all components)                   │
└──────────────┬──────────────┬────────────────┬───────────────┘
               │              │                │
         ┌─────▼──┐    ┌──────▼──┐    ┌───────▼───┐
         │Analyzer │    │ Scorer  │    │ Selector  │
         └────┬────┘    └────┬────┘    └────┬──────┘
              │              │             │
         ┌────▼────┐    ┌────▼────┐   ┌───▼──────┐
         │ Detector │    │ Reporter │   │ (Scorer) │
         └─────┬────┘    └─────────┘   └──────────┘
              │
         Concrete Impls:
         - Insta360FormatDetector
         - SubjectDetector
         - SceneryAnalyzer
         - PerspectiveSelectorComponent
```

---

## Core Abstractions

### 1. AnalyticsComponent (Base Class)

All analytics components inherit from this abstract base.

```python
class AnalyticsComponent(ABC):
    """Base class for all analytics components."""

    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process input and return output."""
        pass

    @abstractmethod
    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input before processing."""
        pass
```

**Key Methods**:
- `process()` - Main execution method
- `validate_input()` - Input validation
- `get_info()` - Component metadata

**Example Usage**:
```python
config = AnalyticsConfig(...)
component = MyAnalyzer(config)
output = component.process(input_data)
```

### 2. Analyzer (Extract Features)

Analyzes input to extract features/metrics.

```python
class Analyzer(AnalyticsComponent, ABC):
    """Extract features from input."""

    @abstractmethod
    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Perform analysis and extract features."""
        pass
```

**Concrete Implementations**:
- `SceneryAnalyzer` - Analyzes frame composition
- Custom analyzers for specific metrics

### 3. Detector (Find Objects/Subjects)

Detects objects, subjects, or specific elements.

```python
class Detector(Analyzer, ABC):
    """Detect objects/subjects in input."""

    @abstractmethod
    def detect(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Detect objects and return results."""
        pass
```

**Concrete Implementations**:
- `Insta360FormatDetector` - Detects 360° format
- `SubjectDetector` - Detects humans in frames

### 4. Scorer (Evaluate Quality)

Scores quality or effectiveness of content.

```python
class Scorer(AnalyticsComponent, ABC):
    """Score quality based on analysis."""

    @abstractmethod
    def score(self, input_data: AnalysisInput, 
              analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Score based on analysis results."""
        pass
```

**Concrete Implementations**:
- Scene quality scorer
- Composition scorer
- Motion scorer

### 5. Selector (Choose Best Option)

Selects best option from candidates.

```python
class Selector(AnalyticsComponent, ABC):
    """Select best option from candidates."""

    @abstractmethod
    def select(self, input_data: AnalysisInput,
               candidates: List[str],
               scores: Dict[str, float]) -> str:
        """Select best candidate."""
        pass
```

**Concrete Implementations**:
- `PerspectiveSelectorComponent` - Selects best perspective

---

## Flow Orchestration

### AnalyticsFlow (DAG Configuration)

Defines a directed acyclic graph of components to execute.

```python
from src.analytics import AnalyticsFlow, AnalyticsNode, FlowConfig

# Define flow
flow = AnalyticsFlow(
    name="scene_analytics",
    description="Analyze scene for quality metrics",
    nodes=[
        AnalyticsNode(
            name="subject_detector",
            component_type="detector",
            input_from=None  # Start node
        ),
        AnalyticsNode(
            name="scenery_analyzer",
            component_type="analyzer",
            input_from="subject_detector"  # Chains from detector
        ),
        AnalyticsNode(
            name="quality_scorer",
            component_type="scorer",
            input_from="scenery_analyzer"  # Chains from analyzer
        ),
    ],
    flow_config=FlowConfig(...)
)

# Execute
executor = FlowExecutorImpl(flow)
executor.register_component("subject_detector", SubjectDetector(config))
executor.register_component("scenery_analyzer", SceneryAnalyzer(config))
executor.register_component("quality_scorer", QualityScorer(config))

results = executor.execute(input_data)
```

### FlowBuilder (Fluent API)

Build flows with fluent interface.

```python
from src.analytics import FlowBuilder

flow = (FlowBuilder("scene_analytics")
    .with_description("Analyze scene for quality")
    .add_node("subject_detector", "detector")
    .add_node("scenery_analyzer", "analyzer", input_from="subject_detector")
    .add_node("quality_scorer", "scorer", input_from="scenery_analyzer")
    .build())
```

### FlowRegistry (Manage Multiple Flows)

Registry for managing and executing multiple flows.

```python
from src.analytics import FlowRegistry

registry = FlowRegistry()

# Register flows
registry.register_flow(scene_analytics_flow)
registry.register_flow(perspective_flow)

# Execute flow by name
results = registry.execute_flow("scene_analytics", input_data)
```

---

## Predefined Flows

### Insta360 Perspective Selection Flow

```python
from src.analytics import create_insta360_perspective_flow

flow = create_insta360_perspective_flow()

# Nodes:
# - format_detector: Detect if video is Insta360 format
# - frame_analyzer: Analyze keyframe
# - perspective_selector: Select best viewing angle
```

### Scene Analytics Flow

```python
from src.analytics import create_scene_analytics_flow

flow = create_scene_analytics_flow()

# Nodes:
# - subject_detector: Detect humans in scene
# - scenery_analyzer: Analyze landscape quality
# - composition_scorer: Score composition
```

### Full Analytics Flow

```python
from src.analytics import create_full_analytics_flow

flow = create_full_analytics_flow()

# Combines both perspective selection and scene analytics
# Stage 0.5: Format detection → Perspective selection
# Stage 3: Subject detection → Scenery analysis → Composition scoring
```

---

## Pydantic Models

### AnalysisInput

Input data for component processing.

```python
from src.analytics import AnalysisInput
from pathlib import Path

input_data = AnalysisInput(
    file_id="file_VID_123",
    file_path=Path("video.insv"),
    scene_id="scene_5",
    metadata={
        "frame_path": "frame.jpg",
        "duration": 102.5,
        "custom_field": "value"
    }
)
```

### AnalysisOutput

Output from component processing.

```python
from src.analytics import AnalysisOutput, AnalysisStage, DecisionType

output = AnalysisOutput(
    analysis_id="scene_5_analysis",
    stage=AnalysisStage.STAGE_3,
    decision_type=DecisionType.SUBJECT_DETECTION,
    decision={"has_subjects": True, "count": 2},
    confidence=0.85,
    rationale="Detected 2 subjects with clear faces",
    inputs={"frame_path": "frame.jpg"},
    results={"human_count": 2, "confidence": 0.85}
)

# Convert to dict or JSON
output_dict = output.to_dict()
output_json = output.model_dump_json()
```

### AnalyticsConfig

Configuration for analytics system.

```python
from src.analytics import AnalyticsConfig

config = AnalyticsConfig(
    enabled=True,
    save_reports=True,
    report_formats=["json", "markdown"],
    face_detection_threshold=0.5,
    perspective_scoring_weights={
        "subject": 0.40,
        "scenery": 0.20,
        "composition": 0.25,
        "motion": 0.15,
    },
    min_confidence_threshold=0.50,
)
```

### FlowConfig

Configuration for flow execution.

```python
from src.analytics import FlowConfig

flow_config = FlowConfig(
    name="scene_analytics",
    description="Analyze scene quality",
    enabled=True,
    stop_on_error=False,
    timeout_seconds=300,
    retry_count=0,
    log_decisions=True,
    track_performance=True,
)
```

---

## Usage Examples

### Example 1: Basic Component Usage

```python
from src.analytics import (
    Insta360FormatDetector,
    AnalysisInput,
    AnalyticsConfig,
)
from pathlib import Path

# Initialize
config = AnalyticsConfig()
detector = Insta360FormatDetector(config)

# Create input
input_data = AnalysisInput(
    file_id="file_VID_123",
    file_path=Path("video.insv"),
    scene_id="scene_0",
)

# Process
output = detector.process(input_data)

# Inspect result
print(f"Decision: {output.decision}")
print(f"Confidence: {output.confidence:.2f}")
print(f"Rationale: {output.rationale}")
```

### Example 2: Flow-Based Processing

```python
from src.analytics import (
    create_scene_analytics_flow,
    FlowExecutorImpl,
    SubjectDetector,
    SceneryAnalyzer,
    AnalysisInput,
    AnalyticsConfig,
)
from pathlib import Path

# Build flow
flow = create_scene_analytics_flow()

# Create executor
executor = FlowExecutorImpl(flow)

# Register components
config = AnalyticsConfig()
executor.register_component("subject_detector", SubjectDetector(config))
executor.register_component("scenery_analyzer", SceneryAnalyzer(config))

# Create input
input_data = AnalysisInput(
    file_id="file_VID_123",
    file_path=Path("video.insv"),
    scene_id="scene_5",
    metadata={"frame_path": "keyframe.jpg"}
)

# Execute flow
results = executor.execute(input_data)

# Get individual results
subject_result = results.get("subject_detector")
scenery_result = results.get("scenery_analyzer")

print(f"Subjects: {subject_result.decision}")
print(f"Scenery: {scenery_result.decision}")
```

### Example 3: Custom Component

```python
from src.analytics import Analyzer, AnalysisInput, AnalysisOutput
from src.analytics import AnalysisStage, DecisionType, AnalyticsConfig

class CustomMetricAnalyzer(Analyzer):
    """Custom analyzer for specific metrics."""

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input has required metadata."""
        return "frame_path" in input_data.metadata

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Extract custom metrics."""
        frame_path = input_data.metadata["frame_path"]

        # Your custom analysis logic here
        return {
            "metric_a": 7.5,
            "metric_b": 8.2,
        }

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and return output."""
        if not self.validate_input(input_data):
            return self._error_output(input_data)

        analysis = self.analyze(input_data)

        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_custom",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.SCENERY_ANALYSIS,
            decision=analysis,
            confidence=0.75,
            rationale="Custom analysis results",
            results=analysis,
        )

    def _error_output(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Create error output."""
        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_custom_error",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.SCENERY_ANALYSIS,
            decision={"error": "validation failed"},
            confidence=0.0,
            rationale="Input validation failed",
        )

# Use it
config = AnalyticsConfig()
analyzer = CustomMetricAnalyzer(config)
output = analyzer.process(input_data)
```

### Example 4: Registry-Based Execution

```python
from src.analytics import (
    FlowRegistry,
    create_scene_analytics_flow,
    SubjectDetector,
    SceneryAnalyzer,
    AnalysisInput,
    AnalyticsConfig,
)

# Create registry
registry = FlowRegistry()

# Register flow
flow = create_scene_analytics_flow()
registry.register_flow(flow)

# Get executor and register components
executor = registry.get_executor("scene_analytics")
config = AnalyticsConfig()
executor.register_component("subject_detector", SubjectDetector(config))
executor.register_component("scenery_analyzer", SceneryAnalyzer(config))

# Execute by flow name
input_data = AnalysisInput(...)
results = registry.execute_flow("scene_analytics", input_data)
```

---

## Performance Monitoring

### PerformanceMetrics

Track component performance.

```python
from src.analytics import PerformanceMetrics

metrics = PerformanceMetrics(
    component_name="subject_detector",
    execution_time_ms=145.5,
    input_size_bytes=12345,
    output_size_bytes=1024,
    memory_used_mb=45.2,
    success=True,
)

# Calculate throughput (items/second)
throughput = metrics.throughput_items_per_second(items=8)
print(f"Throughput: {throughput:.2f} items/sec")
```

### ExecutionStats

Track overall flow execution.

```python
from src.analytics import ExecutionStats
from datetime import datetime

stats = ExecutionStats(
    flow_name="scene_analytics",
    start_time=datetime.now(),
    end_time=datetime.now(),
    total_items_processed=100,
    successful_items=98,
    failed_items=2,
)

print(f"Duration: {stats.duration_seconds:.1f} seconds")
print(f"Success rate: {stats.success_rate:.1f}%")
```

---

## Extending the Framework

### Create Custom Component

```python
from src.analytics import Detector, AnalysisInput, AnalysisOutput

class MyCustomDetector(Detector):
    """Custom detector implementation."""

    def validate_input(self, input_data: AnalysisInput) -> bool:
        # Your validation logic
        return True

    def detect(self, input_data: AnalysisInput) -> Dict[str, Any]:
        # Your detection logic
        return {"result": "value"}

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        # Alias for detect
        return self.detect(input_data)

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        # Your processing logic
        if not self.validate_input(input_data):
            return self._error_output(input_data)

        detection = self.detect(input_data)

        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_custom",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.CUSTOM,
            decision=detection,
            confidence=0.85,
            rationale="Custom detection result",
            results=detection,
        )
```

### Add to Flow

```python
from src.analytics import FlowBuilder

flow = (FlowBuilder("my_custom_flow")
    .add_node("my_detector", "detector")
    .add_node("my_analyzer", "analyzer", input_from="my_detector")
    .build())
```

---

## Benefits of This Architecture

### 1. **Type Safety**
- Pydantic models validate all inputs/outputs
- Type hints for IDE autocomplete
- Compile-time error detection

### 2. **Extensibility**
- Abstract base classes define clear contracts
- Easy to add new components
- No need to modify existing code

### 3. **Composability**
- Components work independently or in flows
- DAG execution enables complex pipelines
- Nodes can be conditionally enabled/disabled

### 4. **Traceability**
- Each output has analysis_id, confidence, rationale
- Full execution path is logged
- Easy to debug decision chains

### 5. **Performance**
- Built-in metrics tracking
- Async execution support (future)
- Caching support for repeated analyses

### 6. **Testability**
- Mock components easily
- Test in isolation or as flow
- Deterministic output validation

---

## Migration from Legacy System

### Before (Legacy):

```python
analyzer = SceneAnalyzer()
result = analyzer.analyze_frame(frame_path)
print(result.scenery_quality)
```

### After (New Flow):

```python
from src.analytics import (
    FlowBuilder,
    FlowExecutorImpl,
    SubjectDetector,
    SceneryAnalyzer,
    AnalysisInput,
    AnalyticsConfig,
)

config = AnalyticsConfig()

flow = (FlowBuilder("analysis")
    .add_node("detector", "detector")
    .add_node("analyzer", "analyzer", input_from="detector")
    .build())

executor = FlowExecutorImpl(flow)
executor.register_component("detector", SubjectDetector(config))
executor.register_component("analyzer", SceneryAnalyzer(config))

input_data = AnalysisInput(
    file_id="video_1",
    file_path=Path("video.insv"),
    scene_id="scene_1",
    metadata={"frame_path": "frame.jpg"}
)

results = executor.execute(input_data)
scenery = results["analyzer"].decision["scenery_score"]
```

### Backward Compatibility

Legacy classes still available:
- `SceneAnalyzer` - Direct frame analysis
- `PerspectiveSelector` - Direct perspective selection
- `TraceabilityLogger` - Decision logging

---

## Best Practices

1. **Use Flows for Complex Pipelines**
   - When components depend on each other
   - When you need performance tracking
   - When scalability matters

2. **Use Direct Components for Simple Cases**
   - Single analysis operation
   - No dependencies needed
   - Quick one-off processing

3. **Validate Early**
   - Use `validate_input()` before processing
   - Check metadata completeness
   - Return early on validation failure

4. **Document Custom Components**
   - Docstrings for all methods
   - Example usage in class docstring
   - Explain input/output contracts

5. **Monitor Performance**
   - Use `PerformanceMetrics` in production
   - Track success rates
   - Identify bottlenecks

---

## Conclusion

The new flow architecture provides a professional, extensible framework for analytics:
- **Abstract classes** define clear component interfaces
- **Pydantic models** ensure type safety and validation
- **Flow orchestration** enables complex DAG pipelines
- **Performance monitoring** tracks component health
- **Backward compatibility** maintains legacy code support

This foundation enables building sophisticated, production-grade analytics systems with confidence and clarity.

