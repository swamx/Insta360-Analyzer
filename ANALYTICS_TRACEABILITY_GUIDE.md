# Analytics & Traceability Guide

**Phase 3 Advanced Features**: Intelligent perspective selection, scene analytics, and complete decision traceability

---

## Overview

The Phase 3 analytics system provides:

1. **Scene Analytics** - Detect humans, analyze scenery quality, and measure composition
2. **Intelligent Perspective Selection** - Automatically choose the best 360° viewing angle
3. **Complete Traceability** - Track every analytics decision with rationale and confidence
4. **Detailed Reports** - JSON and Markdown reports for analysis and debugging

---

## Components

### 1. Scene Analyzer (`src/analytics/scene_analyzer.py`)

Analyzes individual frames for:
- **Human Detection** - Identifies people/subjects using face detection
- **Scenery Quality** - Rates landscape and composition beauty (1-10 scale)
- **Composition Score** - Evaluates framing and visual balance
- **Image Metrics**:
  - Brightness (0-255)
  - Contrast (0-100)
  - Motion Level (0-100)
  - Sharpness/Clarity

#### Example Analysis Output:
```json
{
  "has_humans": true,
  "human_count": 2,
  "human_confidence": 0.6,
  "scenery_quality": 7.5,
  "composition_score": 8.2,
  "brightness": 165.5,
  "contrast": 45.3,
  "motion_level": 62.0,
  "dominant_colors": ["#4A7C59", "#8B9DC3", "#DEB887"]
}
```

**How it Works**:
1. Opens frame image with OpenCV
2. Detects faces using Haar cascades (proxy for humans)
3. Calculates Laplacian sharpness variance
4. Analyzes brightness and contrast from grayscale conversion
5. Estimates motion from Laplacian energy
6. Scores scenery based on sharpness × 0.5 + contrast × 0.3 - crowd penalty
7. Scores composition based on clarity, presence of humans, and exposure

**Scoring Formulas**:
```
Scenery Score = (Sharpness × 0.5 + Contrast/10 × 0.3) × crowd_penalty
Composition Score = Sharpness × 0.6 + (Human Bonus 2.0) + (Exposure Bonus 1.0)
```

### 2. Perspective Selector (`src/analytics/perspective_selector.py`)

Intelligently selects best viewing direction for 360° videos.

#### Standard Perspectives (8 directions):
```
forward   (yaw=0°,   pitch=0°)   - Primary shooting direction
backward  (yaw=180°, pitch=0°)   - Alternative reverse angle
left      (yaw=-90°, pitch=0°)   - Left profile
right     (yaw=90°,  pitch=0°)   - Right profile
up        (yaw=0°,   pitch=-45°) - Overhead/sky view
down      (yaw=0°,   pitch=45°)  - Ground/downward view
left_down (yaw=-90°, pitch=30°)  - Angled left composition
right_down(yaw=90°,  pitch=30°)  - Angled right composition
```

#### Perspective Scoring:
```
Overall Score = 
  Subject Score × 0.4 +    (40% - prioritize humans)
  Scenery Score × 0.2 +    (20% - landscape beauty)
  Composition Score × 0.25 +(25% - framing quality)
  Motion Score × 0.15      (15% - action capture)
```

#### Example Score Output:
```json
{
  "perspective": "forward",
  "yaw": 0,
  "pitch": 0,
  "roll": 0,
  "fov": 90,
  "subject_score": 8.5,
  "scenery_score": 7.2,
  "composition_score": 8.0,
  "motion_score": 6.8,
  "overall_score": 7.85,
  "rationale": "Forward shows 2 subjects; Horizontal angle good for scenery; Forward: ideal for frontal subjects; Motion level: 62.0%"
}
```

**Selection Strategy**:
- If subjects detected: maximize subject_score (frontal angles preferred)
- If no subjects: maximize composition_score (landscape aesthetics)
- Always balance with scenery_score and motion_score

### 3. Traceability Logger (`src/analytics/traceability.py`)

Records every analytics decision with complete context.

#### Decision Record Structure:
```json
{
  "timestamp": "2026-08-02T16:52:00.000000",
  "stage": "stage3_vision_editor",
  "scene_id": "scene_5",
  "decision_type": "subject_detection",
  "inputs": {
    "frame_path": "data/working/scenes/frame_5.jpg"
  },
  "analysis_results": {
    "brightness": 165.5,
    "contrast": 45.3,
    "sharpness": 7.2
  },
  "decision": {
    "has_subjects": true,
    "count": 2
  },
  "confidence": 0.85,
  "rationale": "Detected 2 subjects using face cascade detector"
}
```

#### Decision Types Logged:

| Type | Stage | Purpose |
|------|-------|---------|
| `360_detection` | Stage 0.5 | Detect if video is 360° format |
| `perspective_selection` | Stage 0.5 | Select best viewing angle |
| `360_conversion` | Stage 0.5 | Track conversion success |
| `subject_detection` | Stage 3 | Identify humans in frame |
| `scenery_analysis` | Stage 3 | Rate landscape/composition |
| `scene_scoring` | Stage 3 | Score quality dimensions |

---

## How Perspective Selection Works

### Example: Processing 360° Insta360 Video

**Input**: `VID_20250727.insv` (equirectangular 360°, 2880×1440)

**Stage 0.5 Execution**:

1. **Format Detection**
   ```
   Insta360 format? YES (.insv)
   Projection type? equirectangular (aspect ratio 2.0)
   Needs conversion? YES
   ```

2. **Perspective Scoring**
   - Analyzes keyframe or uses heuristics
   - Scores all 8 standard perspectives
   - Results:
     ```
     forward:     7.85/10 ✓ SELECTED
     backward:    6.50/10
     left:        7.20/10
     right:       7.15/10
     up:          5.30/10
     down:        5.10/10
     left_down:   6.80/10
     right_down:  6.75/10
     ```

3. **Decision Rationale**
   ```
   "Forward shows 2 subjects at center frame;
    Horizontal angle maximizes scenery impact;
    Forward is ideal for frontal subjects;
    Motion detected at 62% - forward captures it well"
   ```

4. **Conversion**
   ```bash
   ffmpeg -i input.insv \
     -vf "v360=e:p:yaw=0:pitch=0:roll=0:h_fov=90:v_fov=90,
           vidstabdetect,vidstabtransform,
           scale=1080:1920:force_original_aspect_ratio=decrease,
           pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
     -c:v libx264 -preset medium -crf 23 \
     -c:a aac -b:a 192k output.mp4
   ```

5. **Traceability Log**
   ```json
   {
     "perspective_selected": "forward",
     "overall_score": 7.85,
     "confidence": 0.785,
     "rationale": "...",
     "all_perspectives": {
       "forward": 7.85,
       "backward": 6.50,
       ...
     }
   }
   ```

---

## Scene Analytics in Stage 3

### Frame Analysis for Each Scene

**Input**: Keyframe from scene

**Analysis Pipeline**:

1. **Subject Detection**
   ```python
   face_cascade.detectMultiScale(img)
   → has_humans: bool
   → human_count: int (0-5+)
   → human_confidence: float (0-1)
   ```

2. **Scenery Quality**
   ```python
   cv2.Laplacian(gray) → sharpness_score
   gray.std() → contrast_normalized
   scenery_score = (sharpness × 0.5 + contrast × 0.3) × crowd_penalty
   ```

3. **Composition Score**
   ```python
   composition_score = sharpness × 0.6
   if has_humans: +2.0 bonus
   if bright enough: +1.0 bonus
   max_cap: 10.0
   ```

4. **Color Analysis**
   ```python
   cv2.kmeans() → k=3 dominant colors in hex
   ```

**Output Example**:
```json
{
  "analytics": {
    "has_subjects": true,
    "subject_count": 2,
    "scenery_quality": 8.1,
    "composition_score": 8.7,
    "dominant_colors": ["#4A7C59", "#8B9DC3", "#E8D5C4"],
    "brightness": 168.2,
    "contrast": 52.8
  }
}
```

---

## Traceability Reports

### Generated Reports

#### 1. JSON Report (`{file_id}_traceability_report.json`)
Complete structured data with all decisions.

**Structure**:
```json
{
  "file_id": "file_VID_20250727_1753650286010000000",
  "generated_at": "2026-08-02T16:52:00.000000",
  "total_decisions": 42,
  "decisions_by_stage": {
    "stage0_insta360_conversion": 3,
    "stage3_vision_editor": 39
  },
  "decisions_by_type": {
    "perspective_selection": 1,
    "subject_detection": 8,
    "scenery_analysis": 8,
    "scene_scoring": 8,
    "360_conversion": 1,
    "360_detection": 1
  },
  "all_decisions": [...],
  "summary": {
    "total_decisions": 42,
    "average_confidence": 0.82,
    "min_confidence": 0.45,
    "max_confidence": 0.95,
    "low_confidence_decisions": 2
  }
}
```

#### 2. Markdown Report (`{file_id}_traceability_report.md`)
Human-readable report for analysis.

**Example**:
```markdown
# Analytics Traceability Report

**File ID**: file_VID_20250727_1753650286010000000
**Generated**: 2026-08-02T16:52:00.000000
**Total Decisions**: 42

## Summary

- **Average Confidence**: 0.82
- **Low Confidence Decisions** (<50%): 2

## Decisions by Stage

- **stage0_insta360_conversion**: 3 decisions
- **stage3_vision_editor**: 39 decisions

## Decisions by Type

- **360_conversion**: 1 decisions
- **360_detection**: 1 decisions
- **scene_scoring**: 8 decisions
- **scenery_analysis**: 8 decisions
- **subject_detection**: 8 decisions

## Detailed Decisions

### 360 Detection

**Scene**: file_VID_20250727
**Time**: 2026-08-02T16:52:00.000000
**Stage**: stage0_insta360_conversion
**Decision**: no_conversion_needed
**Confidence**: 0.95
**Rationale**: Video is already in single-perspective format

### Perspective Selection

**Scene**: file_VID_20250727
**Time**: 2026-08-02T16:52:00.000000
**Stage**: stage0_insta360_conversion
**Decision**: forward
**Confidence**: 0.79
**Rationale**: Forward shows 2 subjects at center frame; Horizontal angle maximizes scenery impact
```

#### 3. CSV Export (`{file_id}_traceability.csv`)
For analysis in spreadsheet tools.

```csv
timestamp,stage,scene_id,decision_type,decision,confidence,rationale
2026-08-02T16:52:00Z,stage0_insta360_conversion,file_VID_20250727,360_detection,no_conversion_needed,0.95,Video is already single-perspective
2026-08-02T16:52:00Z,stage3_vision_editor,scene_0,subject_detection,"{""has_subjects"": true, ""count"": 1}",0.85,Detected 1 subject
2026-08-02T16:52:05Z,stage3_vision_editor,scene_0,scenery_analysis,"{""scenery_score"": 7.5, ""composition_score"": 8.2}",0.79,Scenery: 7.5/10
```

---

## Interpreting Results

### Confidence Scores

| Range | Meaning | Action |
|-------|---------|--------|
| 0.80-1.00 | Very High | Trust decision completely |
| 0.60-0.79 | High | Trust with minor verification |
| 0.40-0.59 | Medium | Verify or A/B test |
| 0.20-0.39 | Low | Questionable, may need manual review |
| 0.00-0.19 | Very Low | Do not use, requires manual override |

### Subject Detection Quality

**High Confidence** (>0.8):
- Clear faces, frontal orientation
- Good lighting, sharp image
- Single or few subjects

**Low Confidence** (<0.4):
- Distant subjects, profile/back orientation
- Poor lighting, motion blur
- Crowded scenes, multiple overlapping people

**Mitigation**: Use alternative perspectives or manual selection

### Scenery Quality Interpretation

| Score | Quality | Best For |
|-------|---------|----------|
| 9-10 | Stunning | Feature content, hero shots |
| 7-8 | Great | Main reel content, high-engagement |
| 5-6 | Decent | Filler, transitions, supporting shots |
| 3-4 | Poor | Avoid if possible, only if necessary |
| 1-2 | Unusable | Discard, too low quality |

### Motion Level Analysis

| Level | Characteristic | Use Case |
|-------|-----------------|----------|
| 80-100 | Highly dynamic | Action content, energetic shots |
| 60-79 | Moderate motion | Balanced content, walking/movement |
| 40-59 | Slight motion | Talking heads, static composition |
| 20-39 | Very static | Landscape, still scenes |
| 0-19 | Completely still | Dead content, avoid |

---

## Performance Optimization

### Model Requirements

**Scene Analyzer** (OpenCV):
- Memory: ~200MB
- Processing: ~100ms per frame
- GPU: Not required

**Perspective Selector**:
- Memory: ~50MB
- Processing: ~10ms per perspective (8 × 10ms = 80ms)
- GPU: Not required

**Qwen2.5-VL** (optional):
- Memory: 7B model = 4.5GB (4-bit quantized), 14GB (full precision)
- Processing: ~2-3 seconds per frame
- GPU: NVIDIA RTX 3060+ recommended

### Optimization Tips

1. **Batch Frame Analysis**
   ```python
   analyzer.analyze_multiple_frames(frame_paths)
   # 8× faster than sequential analysis
   ```

2. **Cache Perspective Scores**
   - Reuse scores across similar videos
   - Pre-calculate for common formats

3. **Disable Full Precision Qwen**
   - Use 4-bit quantization (saves 3.5GB VRAM)
   - Use distilled models for faster inference

---

## Common Issues & Solutions

### Issue: Low Subject Detection Confidence

**Symptoms**:
- has_humans: true, human_confidence: 0.2
- Rationale mentions "distant" or "profile"

**Solutions**:
1. Ensure good lighting in video
2. Consider alternative perspectives
3. Manually verify frame quality
4. Use scenery_score if subjects not important

### Issue: Perspective Score < 6.0

**Symptoms**:
- All perspectives scored low (< 6.0)
- Average confidence < 0.50

**Solutions**:
1. Video quality issue (low light, motion blur)
2. No clear subject matter
3. Use default "forward" perspective
4. Manually select best angle

### Issue: High Subject Count Low Score

**Symptoms**:
- has_humans: true, human_count: 5+
- scenery_quality: 3.5 (crowd penalty applied)

**Solutions**:
1. Subject-focused composition hurts scenery score
2. May be intentional (group shots)
3. Consider subject_score > scenery_score
4. Use backward/side perspectives to avoid crowd

---

## Advanced Usage

### Custom Perspective Selection

```python
from src.analytics import PerspectiveSelector

selector = PerspectiveSelector()
perspective, score = selector.select_best_perspective(
    video_path="video.insv",
    keyframe_path="keyframe.jpg",
    prefer_subjects=True  # or False for landscapes
)

print(f"Selected: {perspective} (score: {score.overall_score})")
print(f"Rationale: {score.rationale}")
```

### Batch Analysis

```python
from src.analytics import SceneAnalyzer

analyzer = SceneAnalyzer()
frames = [Path(f"frame_{i}.jpg") for i in range(10)]
results = analyzer.analyze_multiple_frames(frames)

for frame_path, result in results.items():
    print(f"{frame_path}: scenery={result.scenery_quality:.1f}, "
          f"has_humans={result.has_humans}")
```

### Manual Perspective Override

```python
# Skip AI selection, use specific perspective
converter = Insta360Converter()
converter.convert_360_to_perspective(
    input_video=Path("video.insv"),
    output_path=Path("output.mp4"),
    perspective="left",  # Manual override
    fov=90,
    stabilize=True
)
```

---

## Future Enhancements

1. **AI Perspective Tracking** - Follow moving subjects across frames
2. **Multi-Perspective Output** - Generate multiple reels from same video
3. **Motion Prediction** - Extrapolate motion to predict where action will be
4. **Gimbal Effect** - Smooth camera motion between perspectives
5. **Real-time Processing** - Stream 360° content with live perspective selection
6. **User Feedback Loop** - Learn from manual overrides
7. **Crowd Analytics** - Estimate crowd density and energy
8. **Audio Analysis** - Correlate audio energy with visual motion

---

## References

- OpenCV Documentation: https://docs.opencv.org/
- FFmpeg v360 Filter: https://ffmpeg.org/ffmpeg-filters.html#v360_002c-v360
- Qwen2.5-VL Model: https://huggingface.co/Qwen/Qwen2.5-VL-7B
- Insta360 Format: https://www.insta360.com/

