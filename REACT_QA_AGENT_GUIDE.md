# ReACT QA Agent System - Complete Guide

**Status**: Production Implementation  
**Architecture**: Haystack AI with Persistent State Caching  
**Agent Pattern**: ReACT (Reason-Act-Observe-Think)  
**Date**: 2026-08-03

---

## System Overview

The ReACT QA Agent System implements a closed-loop quality assurance pipeline using the **Reason-Act-Observe-Think** pattern with **Haystack AI** orchestration and **persistent state caching** for transfer between cycles.

```
┌─────────────────────────────────────────────────────────┐
│            COMPLETE PIPELINE ARCHITECTURE               │
└─────────────────────────────────────────────────────────┘

INPUT: Video File (.insv)
  ↓
┌─────────────────────────────────────────────────────────┐
│   [1] ANALYTICS PIPELINE (Stages 0.5-5)                │
│  - Format detection (Insta360)                          │
│  - Perspective selection (360° → single-view)          │
│  - Scene detection (boundaries & keyframes)            │
│  - Vision analysis (Qwen2.5-VL scoring)                │
│  - Reel assembly (scene composition)                   │
│  - Encoding (1080×1920 vertical)                       │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│   [2] ReACT QA LOOP (Reason-Act-Observe-Think)        │
│                                                         │
│  ITERATION 1                                           │
│  ├─ THOUGHT: Analyze quality, diagnose issues         │
│  ├─ ACTION: Execute corrective action                 │
│  ├─ OBSERVATION: Evaluate results                     │
│  └─ STATE: Cache iteration checkpoint                 │
│                                                         │
│  ITERATION 2 (if quality < threshold)                 │
│  ├─ THOUGHT: Reason about new approach               │
│  ├─ ACTION: Regenerate with learned preferences      │
│  ├─ OBSERVATION: Compare quality improvements        │
│  └─ STATE: Update cache & continue                    │
│                                                         │
│  ... (up to 5 iterations or quality >= 7.0)           │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│   [3] FINAL REPORT & RECOMMENDATIONS                   │
│  - Quality score (0-10)                               │
│  - Issues identified                                  │
│  - Recommendations for deployment                     │
│  - Execution statistics                               │
└─────────────────────────────────────────────────────────┘
  ↓
OUTPUT: Reel (MP4) + QA Report (JSON)
```

---

## Core Components

### 1. Agent Contracts

Define clear interfaces for agent responsibilities:

```python
from src.agents import (
    ReasonerContract,      # Analyzes state, reasons about fixes
    ActorContract,         # Executes corrective actions
    OrchestratorContract,  # Coordinates Reasoner and Actor
    QualityAssuranceContract  # Comprehensive QA assessment
)
```

**ReasonerContract**:
- `reason()` - Analyze current state, diagnose issues, recommend next action
- `evaluate()` - Score quality of results (0-10 scale)

**ActorContract**:
- `act()` - Execute action based on reasoning
- `can_act()` - Check if action type is supported

**QualityAssuranceContract**:
- `assess_quality()` - Comprehensive quality metrics
- `identify_issues()` - List quality problems
- `recommend_improvements()` - Suggest fixes

### 2. Execution Context

Shared state between agents:

```python
from src.agents import ExecutionContext

context = ExecutionContext(
    file_id="file_VID_123",
    video_path="video.insv",
    stage="qa_assessment",
    # Shared state that agents update
)

# Each agent has working memory
context.reasoner_memory.add_thought("Analyzing quality...")
context.actor_memory.add_action("regenerate", {...})
```

### 3. ReACT Orchestrator

Implements Thought-Action-Observation loop:

```python
from src.agents import ReActOrchestrator

orchestrator = ReActOrchestrator(
    reasoner=qa_reasoner,
    actor=qa_actor,
    state_cache=state_cache,
    max_iterations=5,
)

result = orchestrator.orchestrate(context)
```

**ReACT Loop**:
```
Iteration 1:
  THOUGHT  → Analyze state
  ACTION   → Execute fix
  OBSERVE  → Evaluate results
  CACHE    → Save state

Iteration 2 (if quality < 7.0):
  THOUGHT  → Reason about new approach
  ACTION   → Regenerate with learned prefs
  OBSERVE  → Check improvement
  CACHE    → Checkpoint state

... (continue until quality threshold or max iterations)
```

### 4. State Management

**In-Memory Cache** (speed):
```python
from src.agents import InMemoryStateCache

cache = InMemoryStateCache(max_size=100)
cache.cache_state("key", state_dict)
state = cache.retrieve_state("key")
stats = cache.get_cache_stats()
```

**Persistent Cache** (checkpoints):
```python
from src.agents import PersistentStateCache

cache = PersistentStateCache(Path("data/cache"))
cache.cache_state("checkpoint_1", state)  # Saves to disk + memory
```

**Pipeline Orchestrator** (full integration):
```python
from src.agents import PipelineOrchestrator

orchestrator = PipelineOrchestrator(
    reasoner=qa_reasoner,
    actor=qa_actor,
    cache_dir=Path("data/cache"),
)

result = orchestrator.run_pipeline(context)
```

### 5. QA Agents

**QAReasonerAgent**:
- Analyzes user feedback patterns
- Diagnoses root causes
- Recommends corrective actions
- Evaluates quality progress

**QAActorAgent**:
- Executes: Analyze, Learn, Regenerate, Compare
- Collects feedback
- Learns from patterns
- Regenerates reels with adaptations

**QAAssessmentAgent**:
- Comprehensive quality evaluation
- Scores: perspective, scenes, subjects, scenery, engagement
- Identifies issues
- Recommends improvements

---

## Complete Workflow Example

### 1. Initialize System

```python
from pathlib import Path
from src.executor import ReelExecutor

video = Path("C:/Users/.../Camera01/VID_20250727_170303_00_033.insv")

executor = ReelExecutor(
    video_path=video,
    data_dir=Path("data"),
    max_duration=0,  # Unlimited
)
```

### 2. Run Pipeline

```python
results = executor.run()

# Output:
# {
#   "success": True,
#   "pipeline": {
#       "file_id": "file_VID_...",
#       "status": "success",
#       "stages": {
#           "stage0_insta360_conversion": {"success": True, ...},
#           "stage1_discovery": {"success": True, ...},
#           "stage2_scene_detection": {"success": True, ...},
#           "stage3_vision_editor": {"success": True, ...},
#           "stage4_reel_assembly": {"success": True, ...},
#           "stage5_encoding": {"success": True, ...}
#       }
#   },
#   "qa": {
#       "react_result": {
#           "success": True,
#           "iterations": 3,
#           "quality_score": 8.2,
#           "trace": {...}
#       },
#       "cache_stats": {
#           "size": 3,
#           "hits": 12,
#           "misses": 3,
#           "hit_rate": 80.0
#       }
#   },
#   "report": {
#       "summary": {
#           "quality_score": 8.2,
#           "status": "success",
#           "qa_iterations": 3
#       },
#       "recommendations": [
#           "Reel quality is excellent - ready for publishing"
#       ]
#   }
# }
```

### 3. Review Results

```python
executor.print_summary()

# Output:
# ================================================================================
# EXECUTION SUMMARY
# ================================================================================
# Video: VID_20250727_170303_00_033.insv
# File ID: file_VID_20250727_170303_00_033_1753650286010000000
# Quality Score: 8.2/10
# QA Iterations: 3
# Status: success
#
# Recommendations:
#   - Reel quality is excellent - ready for publishing
# ================================================================================
```

### 4. Save & Review Report

```python
report_path = executor.save_results()
# Report saved to: data/output/execution_report.json

# Read report
import json
with open(report_path) as f:
    report = json.load(f)
```

---

## ReACT Execution Trace

Every iteration is captured for transparency:

```json
{
  "agent_id": "react_file_VID_123",
  "steps": [
    {
      "step_num": 1,
      "phase": "thought",
      "content": "Analyzing state at iteration 1"
    },
    {
      "step_num": 2,
      "phase": "thought",
      "content": "{\n  \"diagnosis\": \"Perspective not optimal\",\n  \"confidence\": 0.85,\n  \"next_step\": \"Try alternative perspective angles\"\n}"
    },
    {
      "step_num": 3,
      "phase": "action",
      "content": "Executing: Try alternative perspective angles"
    },
    {
      "step_num": 4,
      "phase": "observation",
      "content": "{\n  \"action_type\": \"regenerate\",\n  \"action\": \"regenerate\",\n  \"result\": \"Reel regeneration prepared\",\n  \"success\": true\n}"
    },
    {
      "step_num": 5,
      "phase": "observation",
      "content": "Quality score: 7.5/10"
    }
  ],
  "final_answer": "Completed 3 iterations, quality score: 8.2/10",
  "success": true,
  "score": 8.2
}
```

---

## State Caching & Checkpoints

### Checkpoint Recovery

If pipeline crashes, it can resume:

```python
# First run
executor = ReelExecutor(video_path=video)
results = executor.run()  # Runs iterations 1-5

# Later, resume with same executor or new instance
# Haystack automatically loads cached state
executor2 = ReelExecutor(video_path=video)
results2 = executor2.run()  # Resumes from checkpoint
```

### Cache Statistics

```json
{
  "cache_stats": {
    "size": 5,
    "max_size": 100,
    "hits": 27,
    "misses": 8,
    "hit_rate": 77.1
  }
}
```

### State Transfer Between Agents

Persistent cache enables state transfer:

```python
# Reasoner analyzes, saves state
reasoner_state = {
    "diagnosis": "perspective_issue",
    "confidence": 0.85,
    "recommended_action": "regenerate"
}
cache.cache_state("reasoner_output", reasoner_state)

# Actor retrieves and acts on state
actor_state = cache.retrieve_state("reasoner_output")
action_result = actor.act(context, actor_state)

# Result cached for next iteration
cache.cache_state("iteration_1_result", action_result)
```

---

## Quality Scoring

Quality score calculated from multiple dimensions:

```
Quality Score = 
  Perspective Score × 0.2 +
  Scene Selection × 0.2 +
  Subject Detection × 0.2 +
  Scenery Quality × 2 +
  Engagement Potential × 0.2

Score Interpretation:
  9.0-10.0: Excellent - Ready for publishing
  8.0-8.9:  Very Good - High quality
  7.0-7.9:  Good - Acceptable quality
  5.0-6.9:  Fair - Needs improvement
  < 5.0:    Poor - Significant issues
```

---

## Integration with Feedback System

QA Agent uses feedback to improve reels:

```python
# Collect feedback
feedback = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.NEGATIVE,
    category=FeedbackCategory.PERSPECTIVE,
    rating=2,
    comment="Wrong angle",
    suggestions=["Try left perspective"],
)

generator.collect_reel_feedback(feedback)

# ReACT loop learns from it
# Next iteration regenerates with learned preferences
```

**Learning Flow**:
```
Collect Feedback
  ↓
Analyze Patterns
  ↓
Learn Preferences
  ↓
Apply to Next Iteration
  ↓
Regenerate Reel
  ↓
Evaluate Improvement
  ↓
(Repeat until converged)
```

---

## Configuration & Tuning

### Max Iterations

```python
orchestrator = ReActOrchestrator(
    reasoner=qa_reasoner,
    actor=qa_actor,
    max_iterations=5,  # Adjust based on needs
)
```

### Quality Threshold

```python
# In orchestrator.should_iterate():
if context.quality_score >= 8.0:  # Stop early if excellent
    return False
```

### Cache Size

```python
cache = InMemoryStateCache(max_size=100)  # LRU eviction
```

### Persistent Storage

```python
cache_dir = Path("data/cache")  # All checkpoints saved here
```

---

## Debugging & Transparency

### Execution Traces

Every step logged and accessible:

```python
trace = orchestrator.get_execution_trace(iteration=-1)  # Last iteration
trace.to_dict()  # Full trace as dict

# See all steps
for step in trace.steps:
    print(f"{step.phase}: {step.content}")
```

### Agent Memories

Track agent reasoning:

```python
context.reasoner_memory.thoughts  # All thoughts
context.reasoner_memory.observations  # All observations
context.reasoner_memory.add_error(error)  # Error tracking

context.actor_memory.actions_taken  # Actions executed
context.actor_memory.outcomes  # Results
```

### Cache Monitoring

```python
stats = orchestrator.state_cache.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1f}%")
```

---

## Architecture Advantages

✅ **Reason-Act-Observe Loop**: Transparent decision-making  
✅ **Persistent State Caching**: Resumable from any checkpoint  
✅ **Agent Contracts**: Clear, mockable interfaces  
✅ **Execution Traces**: Full transparency and debugging  
✅ **Haystack Integration**: Professional DAG orchestration  
✅ **Feedback Learning**: Continuous improvement  
✅ **Multi-Iteration**: Converges on optimal quality  
✅ **Type Safe**: Pydantic validation throughout  

---

## Production Deployment

### Monitoring

```python
# Check cache hit rate (high = good reuse)
stats = orchestrator.state_cache.get_cache_stats()
assert stats['hit_rate'] > 70

# Verify quality threshold
assert results['qa']['react_result']['quality_score'] >= 7.0

# Check iteration count
assert results['qa']['react_result']['iterations'] <= 5
```

### Error Recovery

```python
try:
    results = executor.run()
except Exception as e:
    # Can resume from checkpoint
    # Just run again with same file_id
    results = executor.run()
```

### Performance Tuning

```python
# Monitor iteration time
trace = orchestrator.get_execution_trace()
iteration_times = [
    (step.step_num, step.timestamp)
    for step in trace.steps
]

# Adjust cache size based on hit rate
if stats['hit_rate'] < 50:
    cache.max_size += 50
```

---

## Future Enhancements

1. **Parallel Reasoning**: Multiple reasoners in parallel
2. **Ensemble Scoring**: Combine multiple QA approaches
3. **Federated Learning**: Learn from multiple users' feedback
4. **Adaptive Thresholds**: Adjust quality threshold per video type
5. **Cost Tracking**: Monitor compute cost per iteration
6. **Preference Learning**: User-specific quality preferences

---

## Conclusion

The ReACT QA Agent System provides:

- **Explainable AI**: Every decision traced and logged
- **Continuous Improvement**: Learns from feedback across iterations
- **Resilient**: Can resume from any checkpoint
- **Professional**: Haystack-based DAG orchestration
- **Extensible**: Agent contract pattern for custom implementations
- **Production-Ready**: State caching, error recovery, monitoring

This enables **automated quality assurance** with **human-understandable reasoning** and **continuous learning from feedback**.

