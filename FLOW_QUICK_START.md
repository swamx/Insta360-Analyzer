# Flow Architecture - Quick Start

**Modern, extensible analytics using abstract classes, Pydantic, and DAG-based flows**

---

## 30-Second Overview

**Old Way** (Direct component):
```python
analyzer = SceneAnalyzer()
result = analyzer.analyze_frame(frame_path)
```

**New Way** (Flow-based):
```python
from src.analytics import create_scene_analytics_flow, FlowExecutorImpl
from src.analytics import SubjectDetector, SceneryAnalyzer, AnalysisInput, AnalyticsConfig

flow = create_scene_analytics_flow()
executor = FlowExecutorImpl(flow)
executor.register_component("subject_detector", SubjectDetector(AnalyticsConfig()))
executor.register_component("scenery_analyzer", SceneryAnalyzer(AnalyticsConfig()))
results = executor.execute(AnalysisInput(...))
```

---

## Core Concepts

### 1. Components (Do the Work)

Five types of abstract components:

| Component | Purpose | Concrete Examples |
|-----------|---------|------------------|
| **Detector** | Find objects/subjects | Insta360FormatDetector, SubjectDetector |
| **Analyzer** | Extract features | SceneryAnalyzer |
| **Scorer** | Evaluate quality | (Implement custom) |
| **Selector** | Choose best option | PerspectiveSelectorComponent |
| **Reporter** | Generate reports | (Implement custom) |

### 2. Flows (Orchestrate)

Connect components in DAGs (directed acyclic graphs):

```
Format Detector
      ↓
  Frame Analyzer
      ↓
Perspective Selector
```

### 3. Models (Validate)

Pydantic models ensure type safety:

| Model | Purpose |
|-------|---------|
| `AnalysisInput` | Input data with metadata |
| `AnalysisOutput` | Result with decision, confidence, rationale |
| `AnalyticsConfig` | Component settings |
| `FlowConfig` | Flow execution settings |

---

## Quick Examples

### Example 1: Use Predefined Flow

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

# 1. Create flow
flow = create_scene_analytics_flow()

# 2. Create executor
executor = FlowExecutorImpl(flow)

# 3. Register components
config = AnalyticsConfig()
executor.register_component("subject_detector", SubjectDetector(config))
executor.register_component("scenery_analyzer", SceneryAnalyzer(config))

# 4. Create input
input_data = AnalysisInput(
    file_id="video_1",
    file_path=Path("video.insv"),
    scene_id="scene_5",
    metadata={"frame_path": "keyframe.jpg"}
)

# 5. Execute
results = executor.execute(input_data)

# 6. Get results
subject_result = results["subject_detector"]
scenery_result = results["scenery_analyzer"]

print(f"Subjects: {subject_result.decision}")
print(f"Confidence: {subject_result.confidence:.2f}")
print(f"Rationale: {subject_result.rationale}")
```

### Example 2: Build Custom Flow

```python
from src.analytics import FlowBuilder, FlowExecutorImpl

# 1. Build flow with fluent API
flow = (FlowBuilder("my_pipeline")
    .with_description("Custom analysis pipeline")
    .add_node("detector", "detector")                    # Start
    .add_node("analyzer", "analyzer", 
              input_from="detector")                     # Chains from detector
    .add_node("scorer", "scorer", 
              input_from="analyzer")                     # Chains from analyzer
    .build())

# 2. Execute (same as above)
```

### Example 3: Use Flow Registry

```python
from src.analytics import FlowRegistry, create_scene_analytics_flow

# 1. Create and register flows
registry = FlowRegistry()
registry.register_flow(create_scene_analytics_flow())
registry.register_flow(create_insta360_perspective_flow())

# 2. Execute by name
results = registry.execute_flow("scene_analytics", input_data)
```

### Example 4: Direct Component Usage

```python
from src.analytics import Insta360FormatDetector, AnalysisInput, AnalyticsConfig

# Still works like before, just with better architecture
detector = Insta360FormatDetector(AnalyticsConfig())
output = detector.process(input_data)
```

---

## Predefined Flows

### Insta360 Perspective Selection

```python
from src.analytics import create_insta360_perspective_flow

flow = create_insta360_perspective_flow()

# Nodes (execution order):
# 1. format_detector: Is video Insta360 format?
# 2. frame_analyzer: Analyze keyframe
# 3. perspective_selector: Choose best angle
```

### Scene Analytics

```python
from src.analytics import create_scene_analytics_flow

flow = create_scene_analytics_flow()

# Nodes (execution order):
# 1. subject_detector: Find humans
# 2. scenery_analyzer: Rate landscape
# 3. composition_scorer: Score composition
```

### Full Analytics

```python
from src.analytics import create_full_analytics_flow

flow = create_full_analytics_flow()

# Combines both:
# Stage 0.5: Format detection → Perspective selection
# Stage 3: Subject detection → Scenery analysis → Composition scoring
```

---

## Output Structure

Every component returns `AnalysisOutput`:

```python
output = component.process(input_data)

# Properties:
output.analysis_id          # Unique ID
output.stage                # Which pipeline stage
output.decision_type        # Type of decision
output.decision             # The decision (Any type)
output.confidence           # 0.0-1.0 confidence
output.rationale            # Explanation of decision
output.inputs               # Input data used
output.results              # Analysis results

# Convert to dict
output_dict = output.to_dict()
output_json = output.model_dump_json()
```

### Example Output:

```python
{
    "analysis_id": "scene_5_subject_detection",
    "stage": "stage3_vision_editor",
    "decision_type": "subject_detection",
    "decision": {
        "has_subjects": True,
        "count": 3
    },
    "confidence": 0.85,
    "rationale": "Detected 3 subjects with clear faces",
    "inputs": {"frame_path": "keyframe.jpg"},
    "results": {
        "human_count": 3,
        "human_confidence": 0.85,
        "scenery_quality": 8.4,
        "composition_score": 8.7
    }
}
```

---

## Component Hierarchy

```
AnalyticsComponent (Base)
├─ Detector (Find objects)
│   ├─ Insta360FormatDetector
│   └─ SubjectDetector
├─ Analyzer (Extract features)
│   └─ SceneryAnalyzer
├─ Scorer (Evaluate quality)
│   └─ (Implement custom)
├─ Selector (Choose best)
│   └─ PerspectiveSelectorComponent
└─ Reporter (Generate reports)
    └─ (Implement custom)
```

---

## Create Custom Component

```python
from src.analytics import (
    Analyzer,
    AnalysisInput,
    AnalysisOutput,
    AnalyticsConfig,
    AnalysisStage,
    DecisionType,
)
from typing import Dict, Any

class MyCustomAnalyzer(Analyzer):
    """Custom analyzer for specific metrics."""

    def validate_input(self, input_data: AnalysisInput) -> bool:
        """Validate input requirements."""
        return "data" in input_data.metadata

    def analyze(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """Extract metrics."""
        # Your analysis logic
        return {
            "metric_a": 7.5,
            "metric_b": 8.2,
        }

    def process(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Process and return output."""
        if not self.validate_input(input_data):
            return AnalysisOutput(
                analysis_id=f"{input_data.scene_id}_error",
                stage=AnalysisStage.STAGE_3,
                decision_type=DecisionType.SCENERY_ANALYSIS,
                decision={},
                confidence=0.0,
                rationale="Input validation failed",
            )

        analysis = self.analyze(input_data)

        return AnalysisOutput(
            analysis_id=f"{input_data.scene_id}_custom",
            stage=AnalysisStage.STAGE_3,
            decision_type=DecisionType.SCENERY_ANALYSIS,
            decision=analysis,
            confidence=0.85,
            rationale="Custom analysis complete",
            results=analysis,
        )

# Use it
config = AnalyticsConfig()
analyzer = MyCustomAnalyzer(config)
output = analyzer.process(input_data)
```

---

## Common Patterns

### Chain Components (Sequential)

```python
flow = (FlowBuilder("sequential")
    .add_node("step1", "detector")
    .add_node("step2", "analyzer", input_from="step1")
    .add_node("step3", "scorer", input_from="step2")
    .build())
```

**Execution**: step1 → step2 → step3

### Conditional Execution

```python
node = AnalyticsNode(
    name="optional_analyzer",
    component_type="analyzer",
    enabled=False  # Disabled
)

# Re-enable if needed
node.enabled = True
```

### Error Handling

```python
flow_config = FlowConfig(
    stop_on_error=False,      # Continue on error
    timeout_seconds=300,      # 5 minute timeout
    retry_count=1,            # Retry once
)
```

---

## Configuration

### Global Analytics Config

```python
from src.analytics import AnalyticsConfig

config = AnalyticsConfig(
    enabled=True,
    save_reports=True,
    report_formats=["json", "markdown"],
    face_detection_threshold=0.5,
    min_confidence_threshold=0.50,
    perspective_scoring_weights={
        "subject": 0.40,
        "scenery": 0.20,
        "composition": 0.25,
        "motion": 0.15,
    }
)
```

### Flow Config

```python
from src.analytics import FlowConfig

config = FlowConfig(
    name="my_flow",
    stop_on_error=False,
    timeout_seconds=300,
    retry_count=0,
    log_decisions=True,
    track_performance=True,
)
```

---

## Performance Monitoring

```python
from src.analytics import PerformanceMetrics

# Automatically tracked by executor
executor = FlowExecutorImpl(flow)
results = executor.execute(input_data)

# Get metrics
for metric in executor.metrics:
    print(f"{metric.component_name}: {metric.execution_time_ms:.1f}ms")
    if not metric.success:
        print(f"  Error: {metric.error_message}")
```

---

## Migration Guide

### Before (Legacy):
```python
detector = Insta360FormatDetector()
result = detector.detect_format(video_path)
```

### After (Flow-based):
```python
from src.analytics import Insta360FormatDetector, FlowExecutorImpl
from src.analytics import create_insta360_perspective_flow

flow = create_insta360_perspective_flow()
executor = FlowExecutorImpl(flow)
executor.register_component("format_detector", 
                            Insta360FormatDetector(config))
result = executor.execute(input_data)
```

---

## Best Practices

1. **Use flows for complex pipelines** (multi-component)
2. **Use direct components for simple cases** (single analysis)
3. **Always validate input** in component
4. **Return early on error** with error output
5. **Document custom components** with docstrings
6. **Track performance** in production
7. **Test components independently** before adding to flow

---

## Files & Locations

📁 **Core Architecture**:
- `src/analytics/core.py` - Abstract classes and Pydantic models
- `src/analytics/flow.py` - Flow execution engine
- `src/analytics/implementations.py` - Concrete components

📖 **Documentation**:
- `FLOW_ARCHITECTURE_GUIDE.md` - Full reference guide
- `FLOW_QUICK_START.md` - This quick start (you are here)

📊 **Usage**:
- Direct: `component.process(input_data)`
- Flow: `executor.execute(input_data)`
- Registry: `registry.execute_flow(name, input_data)`

---

## Next Steps

1. Read `FLOW_ARCHITECTURE_GUIDE.md` for deep dive
2. Try the quick examples above
3. Build a custom flow with `FlowBuilder`
4. Add custom components as needed
5. Monitor performance with metrics

---

**Version**: Flow Architecture v1.0  
**Status**: Production-ready  
**Backward Compatible**: Yes (legacy code still works)

