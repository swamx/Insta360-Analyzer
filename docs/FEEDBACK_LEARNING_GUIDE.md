# Feedback & Learning System - Complete Guide

**Overview**: Closed-loop feedback system that learns from user feedback and automatically generates improved reels.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│            Generated Reel (v1)                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   User Feedback       │
         │   (Rating, Comments)  │
         └───────────┬───────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │    Feedback Collection             │
    │  - Store feedback                  │
    │  - Track patterns                  │
    └────────────────┬───────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │    Feedback Analysis               │
    │  - Extract patterns                │
    │  - Generate insights               │
    │  - Identify issues                 │
    └────────────────┬───────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │    Learning Engine                 │
    │  - Learn preferences               │
    │  - Update weights                  │
    │  - Generate suggestions            │
    └────────────────┬───────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────┐
    │    Adaptive Reel Generator         │
    │  - Apply learned preferences       │
    │  - Generate new configuration      │
    │  - Regenerate reel (v2)            │
    └────────────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Improved Reel (v2)    │
         └───────────────────────┘
```

---

## Core Components

### 1. FeedbackCollector

Collects and stores user feedback.

```python
from src.analytics import (
    FeedbackCollector,
    UserFeedback,
    FeedbackType,
    FeedbackCategory,
    FeedbackSource,
)
from pathlib import Path

# Initialize
collector = FeedbackCollector(Path("data/feedback"))

# Collect feedback
feedback = UserFeedback(
    file_id="file_VID_123",
    scene_id="scene_5",
    feedback_type=FeedbackType.NEGATIVE,
    category=FeedbackCategory.PERSPECTIVE,
    rating=2,
    comment="Wrong camera angle, should show faces",
    positive_aspects=["Good scenery"],
    negative_aspects=["Subjects not visible", "Bad angle"],
    suggestions=["Try forward-facing perspective"],
    engagement_metric=35.5,  # User watched 35.5% before skipping
)

feedback_id = collector.collect_feedback(feedback)

# Query feedback
all_feedback = collector.get_feedback_for_file("file_VID_123")
scene_feedback = collector.get_feedback_for_scene("file_VID_123", "scene_5")
negative_feedback = collector.get_negative_feedback()
```

**Feedback Types**:
- `POSITIVE` - Good decision, replicate
- `NEGATIVE` - Bad decision, avoid
- `NEUTRAL` - Acceptable
- `PARTIAL` - Some good, some bad
- `REDIRECT` - Suggest alternative

**Categories**:
- `PERSPECTIVE` - Wrong viewing angle
- `SCENE_SELECTION` - Wrong scene included
- `SUBJECT_DETECTION` - Missed subjects
- `SCENERY_QUALITY` - Bad composition
- `TIMING` - Wrong pacing
- `OVERALL` - General quality

**Sources**:
- `USER` - Direct user feedback
- `ANALYTICS` - Automated metrics
- `ENGAGEMENT` - Social media metrics
- `COMPARISON` - A/B test comparison

### 2. FeedbackAnalyzer

Analyzes patterns in feedback.

```python
from src.analytics import FeedbackAnalyzer

# Initialize
analyzer = FeedbackAnalyzer(collector)

# Analyze feedback
report = analyzer.analyze_feedback("file_VID_123")

# Access results
print(f"Total feedback: {report.total_feedback}")
print(f"Average rating: {report.average_rating:.1f}/5")
print(f"Positive: {report.positive_count}")
print(f"Negative: {report.negative_count}")
print(f"Patterns found: {len(report.patterns)}")
print(f"Recommendations: {report.recommendations}")
print(f"Top liked: {report.top_liked_aspects}")
print(f"Top disliked: {report.top_disliked_aspects}")
```

**What It Extracts**:
- Pattern discovery (recurring issues)
- Aspect sentiment analysis (what users liked/disliked)
- Confidence scoring for patterns
- Actionable recommendations

**Example Report**:
```json
{
  "total_feedback": 5,
  "positive_count": 2,
  "negative_count": 3,
  "average_rating": 2.6,
  "patterns": [
    {
      "category": "perspective",
      "pattern_type": "avoidance",
      "confidence": 0.8,
      "occurrences": 3
    }
  ],
  "recommendations": [
    "Try alternative perspective angles",
    "Manual scene selection recommended"
  ],
  "top_liked_aspects": ["Good scenery", "Nice colors"],
  "top_disliked_aspects": ["Wrong angle", "Bad timing"]
}
```

### 3. LearningEngine

Learns from feedback and adapts decisions.

```python
from src.analytics import LearningEngine

# Initialize
learning_engine = LearningEngine(collector, analyzer)

# Learn from feedback
learned = learning_engine.learn_from_feedback("file_VID_123")

# Get learned preferences
prefs = learning_engine.learned_preferences
print(f"Learned preferences: {prefs}")

# Apply to configuration
config = {
    "perspective_scoring_weights": {
        "subject": 0.40,
        "scenery": 0.20,
        "composition": 0.25,
        "motion": 0.15,
    }
}

updated_config = learning_engine.apply_learned_preferences(config)

# Get adaptive weights
weights = learning_engine.get_learned_weights()
print(f"Adaptive weights: {weights}")

# Get suggestions for next reel
suggestions = learning_engine.suggest_parameters("file_VID_123")
print(f"Suggestions: {suggestions}")
```

**Learning Process**:
1. Analyze patterns from feedback
2. Extract preferences and avoidances
3. Adjust scoring weights
4. Update thresholds
5. Generate suggestions for improvement

### 4. AdaptiveReelGenerator

Generates improved reels based on learned preferences.

```python
from src.analytics import AdaptiveReelGenerator, UserFeedback, FeedbackType

# Initialize
generator = AdaptiveReelGenerator(Path("data/feedback"))

# Collect feedback
feedback = UserFeedback(...)
generator.collect_reel_feedback(feedback)

# Analyze feedback
analysis = generator.analyze_reel_feedback("file_VID_123")

# Learn and adapt
adaptation = generator.learn_and_adapt("file_VID_123")

# Generate new configuration
config = generator.generate_adaptive_config(
    file_id="file_VID_123",
    scenes=[...],  # Available scenes
)

# Regenerate reel with new config
result = generator.regenerate_reel(
    file_id="file_VID_123",
    scenes=[...],
    executor_callback=lambda cfg: execute_reel_generation(cfg),
)

# Get performance metrics
metrics = generator.get_performance_metrics("file_VID_123")
print(f"Average rating: {metrics['feedback_summary']['average_rating']}")
print(f"Positive feedback: {metrics['feedback_summary']['positive_feedback_percent']}%")
print(f"Watch time: {metrics['engagement_metrics']['average_watch_time']}%")
```

---

## Complete Workflow Example

### Step 1: Generate Initial Reel

```python
from src.analytics import create_full_analytics_flow, FlowExecutorImpl

# Create and execute flow
flow = create_full_analytics_flow()
executor = FlowExecutorImpl(flow)
# ... register components ...
results = executor.execute(input_data)

# Save reel v1
reel_path = "output/reel_v1.mp4"
```

### Step 2: Collect Feedback

```python
from src.analytics import (
    UserFeedback,
    FeedbackType,
    FeedbackCategory,
    AdaptiveReelGenerator,
)

generator = AdaptiveReelGenerator(Path("data"))

# User watches reel and provides feedback
feedback = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.NEGATIVE,
    category=FeedbackCategory.PERSPECTIVE,
    rating=2,
    comment="Forward angle doesn't show the main subject",
    negative_aspects=["Subject not visible", "Bad framing"],
    suggestions=["Try left perspective"],
    watch_time_percent=40.0,  # Watched 40% before skipping
)

generator.collect_reel_feedback(feedback)

# Collect more feedback (multiple iterations)
feedback2 = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.NEGATIVE,
    category=FeedbackCategory.PERSPECTIVE,
    rating=2,
    comment="Same issue as before",
    negative_aspects=["Subject not visible"],
    suggestions=["Left or right angle would be better"],
)

generator.collect_reel_feedback(feedback2)
```

### Step 3: Analyze Feedback

```python
# Analyze patterns
analysis = generator.analyze_reel_feedback("video_123")

print(f"Total feedback items: {analysis['summary']['total_feedback']}")
print(f"Average rating: {analysis['summary']['average_rating']:.1f}/5")
print(f"Patterns: {analysis['patterns']}")
print(f"Recommendations: {analysis['recommendations']}")
```

### Step 4: Learn and Adapt

```python
# Learn from feedback
adaptation = generator.learn_and_adapt("video_123")

print(f"Learned preferences: {adaptation['learned_preferences']}")
print(f"Suggestions: {adaptation['suggestions']}")

# Output:
# Learned preferences: {'perspective_preference': {'subject': 0.45}}
# Suggestions: {
#     'emphasize': ['left perspective', 'subject visibility'],
#     'avoid': ['forward perspective'],
#     'recommendations': ['Try alternative perspective angles']
# }
```

### Step 5: Generate Adaptive Configuration

```python
# Generate new configuration based on feedback
config = generator.generate_adaptive_config(
    file_id="video_123",
    scenes=available_scenes,  # From Stage 2 results
)

print(f"Adaptive config: {config.to_dict()}")

# Output includes:
# - Adjusted perspective (learned from feedback)
# - Modified scene selection (based on patterns)
# - Updated scoring weights (from learning)
# - Quality thresholds (adapted)
```

### Step 6: Regenerate Improved Reel

```python
# Regenerate reel with adaptive config
result = generator.regenerate_reel(
    file_id="video_123",
    scenes=available_scenes,
    executor_callback=lambda cfg: generate_reel_with_config(cfg),
)

print(f"Regeneration success: {result['success']}")
print(f"New config: {result['config']}")

# Save reel v2
reel_path_v2 = "output/reel_v2.mp4"
```

### Step 7: Compare & Validate

```python
# Compare original vs adaptive
comparison = generator.get_comparison_report(
    file_id="video_123",
    first_reel_config=original_config,
    second_reel_config=config,
)

print(f"Prefer v1: {comparison['comparison']['prefer_first']}")
print(f"Prefer v2: {comparison['comparison']['prefer_second']}")
print(f"Recommendation: {comparison['recommendation']}")
```

---

## Feedback Integration Patterns

### Pattern 1: Direct Feedback Input

```python
# User directly rates reel after watching
feedback = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.POSITIVE if rating >= 4 else FeedbackType.NEGATIVE,
    category=FeedbackCategory.OVERALL,
    rating=rating,
    comment=user_comment,
)

generator.collect_reel_feedback(feedback)
```

### Pattern 2: Engagement-Based Feedback

```python
# Automated feedback from social media engagement
feedback = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.NEGATIVE,
    category=FeedbackCategory.TIMING,
    source=FeedbackSource.ENGAGEMENT,
    engagement_metric=avg_likes,
    watch_time_percent=avg_watch_time,
    # Calculate rating from engagement
    rating=int((avg_watch_time / 100) * 5) or 1,
)

generator.collect_reel_feedback(feedback)
```

### Pattern 3: A/B Test Feedback

```python
# Compare two reels and collect preference feedback
feedback = UserFeedback(
    file_id="video_123",
    scene_id="combined",
    feedback_type=FeedbackType.POSITIVE,
    category=FeedbackCategory.OVERALL,
    source=FeedbackSource.COMPARISON,
    comment="Prefer version 2 - better angle",
    suggestions=["Use this perspective for similar videos"],
)

generator.collect_reel_feedback(feedback)
```

---

## Learning Outcomes

### What Gets Learned

1. **Perspective Preferences**
   ```
   If feedback shows "forward not working" → Increase weight for alternatives
   If "left angle preferred" → Learn this preference for similar content
   ```

2. **Scene Quality Standards**
   ```
   If rejected scenes rated low → Raise minimum score threshold
   If always-included scenes rated high → Learn their characteristics
   ```

3. **Subject Detection Needs**
   ```
   If "subjects not visible" feedback → Increase subject confidence threshold
   If "subjects are good" → Prefer scenes with detected subjects
   ```

4. **Content Preferences**
   ```
   If "too much static scenery" → Prefer high-action scenes
   If "like calm scenes" → Reduce motion threshold
   ```

### How Preferences Are Applied

```python
# Before adaptation
original_weights = {
    "subject": 0.40,
    "scenery": 0.20,
    "composition": 0.25,
    "motion": 0.15,
}

# After learning "subjects are important"
adapted_weights = {
    "subject": 0.45,      # ↑ Increased
    "scenery": 0.15,      # ↓ Decreased
    "composition": 0.25,  # ← Unchanged
    "motion": 0.15,       # ← Unchanged
}
```

---

## Performance Metrics

Track improvement with built-in metrics:

```python
metrics = generator.get_performance_metrics("video_123")

print(f"Average rating v1: {metrics['feedback_summary']['average_rating']}")
print(f"Positive feedback %: {metrics['feedback_summary']['positive_feedback_percent']}")
print(f"Average watch time: {metrics['engagement_metrics']['average_watch_time']}%")
print(f"Engagement score: {metrics['engagement_metrics']['average_engagement']}")
```

**Key Metrics**:
- **Rating**: 1-5 stars average
- **Positive %**: Percentage of positive feedback
- **Watch Time**: Average % of reel watched
- **Engagement**: Likes, comments, shares
- **Improvement Opportunity**: Number of avoidance patterns

---

## Multi-Iteration Learning

Feedback-driven improvement over multiple iterations:

```
Reel v1 → Feedback 1,2,3 → Analysis 1 → Learning 1 → Reel v2
                ↓
Reel v2 → Feedback 4,5,6 → Analysis 2 → Learning 2 → Reel v3
                ↓
Reel v3 → Feedback 7,8,9 → Analysis 3 → Learning 3 → Reel v4

Convergence: Eventually settles on preferences that work
```

Each iteration:
1. More feedback collected
2. Patterns become clearer
3. Learning becomes more confident
4. Reels improve continuously

---

## Best Practices

### 1. Collect Diverse Feedback
- Collect feedback from multiple users
- Include both positive and negative
- Cover all categories (perspective, scenery, timing, etc.)

### 2. Wait for Patterns
- Don't adapt after single feedback
- Wait for 3+ similar feedback items (pattern threshold)
- Only apply when confidence > 0.5

### 3. A/B Test Changes
- Generate v1 and v2
- Show both to users
- Measure which performs better
- Adopt if statistically significant

### 4. Monitor Drift
- Track if preferences keep changing
- Stabilize weights if converging
- Detect if feedback contradicts previous

### 5. Provide Context
- Tell users why changes were made
- Show before/after comparison
- Explain learned preferences

---

## API Reference

### UserFeedback

```python
UserFeedback(
    file_id: str,                      # Video ID
    scene_id: str,                     # Scene or "combined" for whole reel
    feedback_type: FeedbackType,       # POSITIVE, NEGATIVE, NEUTRAL, PARTIAL, REDIRECT
    category: FeedbackCategory,        # PERSPECTIVE, SCENE_SELECTION, etc.
    source: FeedbackSource = USER,     # USER, ANALYTICS, ENGAGEMENT, COMPARISON
    rating: int,                       # 1-5 stars
    comment: str = "",                 # User comment
    positive_aspects: List[str] = [],  # What was good
    negative_aspects: List[str] = [],  # What was bad
    suggestions: List[str] = [],       # User suggestions
    related_decision_id: str = None,   # Traceability link
    engagement_metric: float = None,   # 0-100
    watch_time_percent: float = None,  # 0-100
)
```

### FeedbackCollector

```python
collector = FeedbackCollector(storage_dir)
collector.collect_feedback(feedback) → feedback_id
collector.get_feedback_for_file(file_id) → List[UserFeedback]
collector.get_feedback_by_category(category) → List[UserFeedback]
collector.load_feedback_history()
```

### FeedbackAnalyzer

```python
analyzer = FeedbackAnalyzer(collector)
report = analyzer.analyze_feedback(file_id) → FeedbackReport
report.patterns → List[FeedbackPattern]
report.recommendations → List[str]
report.top_liked_aspects → List[str]
```

### LearningEngine

```python
engine = LearningEngine(collector, analyzer)
learned = engine.learn_from_feedback(file_id) → Dict
engine.apply_learned_preferences(config) → Dict
engine.get_learned_weights() → Dict[str, float]
engine.suggest_parameters(file_id) → Dict
```

### AdaptiveReelGenerator

```python
gen = AdaptiveReelGenerator(feedback_dir)
gen.collect_reel_feedback(feedback) → feedback_id
gen.analyze_reel_feedback(file_id) → Dict
gen.learn_and_adapt(file_id) → Dict
gen.generate_adaptive_config(file_id, scenes) → ReelConfiguration
gen.regenerate_reel(file_id, scenes, executor_callback) → Dict
gen.get_performance_metrics(file_id) → Dict
```

---

## Future Enhancements

1. **Federated Learning** - Learn from multiple users' feedback without centralizing
2. **Reinforcement Learning** - Reward good decisions, penalize bad ones
3. **Collaborative Filtering** - Learn what similar users prefer
4. **Trend Detection** - Detect if preferences are changing over time
5. **Anomaly Detection** - Identify unusual feedback patterns
6. **Explanation Generation** - Explain why changes were made
7. **Rollback Support** - Revert to previous config if new one performs worse

---

## Conclusion

The feedback and learning system creates a **closed-loop improvement cycle**:

```
User watches reel
    ↓
Provides feedback (1-5 stars + comment)
    ↓
System analyzes patterns
    ↓
Learns preferences
    ↓
Regenerates improved reel
    ↓
User watches v2, provides more feedback
    ↓
(Loop continues → Progressive improvement)
```

This enables **continuous optimization** of reel generation with **zero manual tuning**.

