# Analytics & Perspective Selection - Quick Reference

**What's New**: Intelligent 360° perspective selection + scene analytics + complete decision traceability

---

## Run Pipeline with Analytics

```bash
cd C:\Users\swamx\OneDrive\Pictures\Insta360-Analyzer
python src/main.py --input "path/to/video.insv" --max-duration=0 --verbose
```

---

## What Happens (Step by Step)

### Stage 0.5: Intelligent Perspective Selection

For 360° videos, the system:
1. **Detects** if video is 360° format (equirectangular)
2. **Analyzes** content (subjects, scenery, composition)
3. **Scores** all 8 viewing angles
4. **Selects** best perspective for conversion
5. **Logs** decision with rationale

**8 Perspectives Available**:
```
forward (0°, 0°)      ← Default, best for frontal subjects
backward (180°, 0°)   
left (-90°, 0°)       ← Good for profiles
right (90°, 0°)       
up (0°, -45°)         ← Overhead/sky view
down (0°, 45°)        ← Ground level
left_down (-90°, 30°)  ← Angled composition
right_down (90°, 30°)  
```

**Example Selection**:
```
Video has 2 people facing camera + beautiful landscape
→ "forward" scores 7.85/10 (highest)
→ Selected for conversion
→ Reason: "Forward shows subjects; horizontal angle maximizes scenery"
```

### Stage 3: Scene Analytics

For each scene, the system:
1. **Analyzes** the keyframe
2. **Detects** subjects (humans)
3. **Rates** scenery quality (1-10)
4. **Measures** composition score (1-10)
5. **Logs** all findings

**Example Frame Analysis**:
```
Frame: scene_005_keyframe.jpg

Subjects Detected:
  - Count: 3 people
  - Confidence: 0.82/1.0
  
Scenery Quality:
  - Brightness: 165/255 (good exposure)
  - Contrast: 45 (strong definition)
  - Sharpness: 8.1/10 (clear image)
  - Score: 8.4/10

Composition:
  - Score: 8.7/10
  - Factors: centered subjects, good framing
  - Colors: ["#4A7C59", "#8B9DC3", "#DEB887"]
```

---

## Traceability Reports (Automatic)

### 1. JSON Report
`data/working/stage0_insta360_conversion/{file_id}_traceability_report.json`

**Contains**:
- All decisions made
- Analysis results
- Confidence scores
- Summaries by stage/type

**Use for**: Data analysis, automation, integration

### 2. Markdown Report
`data/working/stage0_insta360_conversion/{file_id}_traceability_report.md`

**Contains**:
- Human-readable format
- Decision explanations
- Confidence levels
- Complete rationale

**Use for**: Review, documentation, sharing

### 3. CSV Export
`data/working/stage0_insta360_conversion/{file_id}_traceability.csv`

**Contains**:
- Tabular format
- All decisions as rows
- Columns: timestamp, stage, scene, type, decision, confidence, rationale

**Use for**: Spreadsheet analysis, plotting, trends

---

## Scoring Explained

### Confidence Score (0-1)

```
0.90-1.00 | ████████░░ | Very High  ✓ Trust completely
0.75-0.89 | ███████░░░ | High       ✓ Trust with verification
0.50-0.74 | █████░░░░░ | Medium     ✓ Verify or test
0.25-0.49 | ██░░░░░░░░ | Low        ⚠ Question decision
0.00-0.24 | █░░░░░░░░░ | Very Low   ✗ Require override
```

**What it means**:
- High confidence = System is certain about the decision
- Low confidence = System is uncertain, may need manual review

### Perspective Score (1-10)

```
9-10 | ██████████ | Excellent  ← Pick this angle
7-8  | ████████░░ | Very Good  
5-6  | █████░░░░░ | Decent     
3-4  | ███░░░░░░░ | Poor       
1-2  | █░░░░░░░░░ | Avoid      
```

**Components**:
- 40% Subject framing (if people present)
- 20% Scenery beauty (landscape quality)
- 25% Composition (framing, balance)
- 15% Motion capture (how well action is shown)

### Scenery Quality (1-10)

```
Based on:
  - Sharpness (clarity)
  - Contrast (definition)
  - Lighting (exposure)
  - Composition (visual balance)
```

---

## Key Decision Types Logged

| Decision | Stage | What It Means |
|----------|-------|---------------|
| `360_detection` | 0.5 | Is video 360° format? |
| `perspective_selection` | 0.5 | Which angle is best? |
| `360_conversion` | 0.5 | Did conversion succeed? |
| `subject_detection` | 3 | How many people detected? |
| `scenery_analysis` | 3 | What is scene quality? |
| `scene_scoring` | 3 | How good is this scene? |

---

## Reading a Report

### JSON Report Structure

```json
{
  "file_id": "unique_identifier",
  "generated_at": "2026-08-02T16:52:00Z",
  "total_decisions": 27,
  
  "decisions_by_stage": {
    "stage0_insta360_conversion": 3,
    "stage3_vision_editor": 24
  },
  
  "decisions_by_type": {
    "perspective_selection": 1,
    "subject_detection": 8,
    "scenery_analysis": 8,
    "scene_scoring": 8,
    "360_conversion": 1,
    "360_detection": 1
  },
  
  "all_decisions": [
    {
      "timestamp": "2026-08-02T16:52:00Z",
      "stage": "stage0_insta360_conversion",
      "scene_id": "scene_1",
      "decision_type": "perspective_selection",
      "decision": "forward",
      "confidence": 0.785,
      "rationale": "Forward shows subjects; horizontal best for scenery"
    },
    ...
  ],
  
  "summary": {
    "average_confidence": 0.82,
    "low_confidence_decisions": 2
  }
}
```

### Markdown Report Example

```markdown
# Analytics Traceability Report

File: VID_20250727_170303_00_033.insv
Generated: 2026-08-02T16:52:00Z
Total Decisions: 27

## Summary
- Average Confidence: 0.82
- Low Confidence Decisions: 2 (7%)

## 360° Format Detection
- Decision: no_conversion_needed
- Confidence: 0.95
- Rationale: Video already single-perspective

## Perspective Selection
- Decision: forward
- Confidence: 0.785
- Rationale: Frontal subjects + scenery quality

## Scene 5 Analysis

### Subject Detection
Decision: {has_subjects: true, count: 3}
Confidence: 0.82

### Scenery Analysis
Scenery Score: 8.4/10
Composition: 8.7/10

### Scene Scoring
Overall Score: 8.0/10
Beauty: 8, Action: 7, Emotion: 8, Stability: 9, Clarity: 8
```

---

## Interpreting Results

### Good Signs ✓
```
- Average confidence > 0.80
- All decisions have rationale
- Perspective scores vary (not all same)
- Subject detection consistent with content
- Scenery scores reasonable for location
```

### Warning Signs ⚠
```
- Average confidence < 0.50
- Missing rationale for decisions
- All perspectives score similarly (no clear winner)
- Subject detection unreasonable (0 subjects but people visible)
- Scenery scores inconsistent (1 scene 2/10, next 9/10)
```

### Issues ✗
```
- No decisions logged (check if analytics ran)
- All confidence scores 0.0 (model/dependency issue)
- Perspective scores only 5.0 (using heuristics, no real analysis)
- File truncated or incomplete
```

---

## Troubleshooting

### Problem: Perspective Selection Seems Wrong

**Check**:
1. Open JSON report → look at all perspective scores
2. Check confidence score (if < 0.5, decision questionable)
3. Read rationale for why that perspective was chosen
4. Verify subjects detected correctly

**Solutions**:
- If subjects wrong: check video quality (lighting, motion blur)
- If scenery wrong: different video may have other priorities
- If no clear best: use multiple perspectives or manual selection

### Problem: Missing Subjects in Scene

**Check**:
1. Open markdown report → look at subject_detection decisions
2. Check human_count and human_confidence
3. Look at brightness/contrast metrics

**Why it happens**:
- Poor lighting (too dark/bright)
- Subjects far away
- People not facing camera
- Motion blur

**Solutions**:
- Use scenery_score if subjects optional
- Select different perspective
- Manually verify frame quality

### Problem: Low Scenery Scores (< 5)

**Check**:
1. Check brightness and contrast metrics
2. Look at sharpness/clarity score
3. Verify it's not a crowded scene (crowd penalty applied)

**Solutions**:
- Video quality issue (replace if possible)
- Use anyway if content is unique
- Consider alternative perspective
- Trim low-quality scenes

---

## Performance

### Time Impact

Analytics adds ~1-2 seconds to typical pipeline run:
- 100ms per frame analysis
- 80ms per perspective selection (8 angles)
- 20ms per scene scoring decision

**Example: 102-second video with 8 scenes**
- Frame analysis: ~800ms
- Perspective selection: ~80ms
- Scene analytics: ~800ms (8 scenes × 100ms)
- Total: ~1.7 seconds overhead

### Storage Impact

Traceability reports:
- JSON report: 50-200KB (depends on scene count)
- Markdown report: 30-150KB
- CSV export: 20-100KB
- **Total**: ~100-500KB per video

---

## Advanced Usage

### Custom Perspective Selection

```python
from src.analytics import PerspectiveSelector

selector = PerspectiveSelector()
perspective, score = selector.select_best_perspective(
    video_path=Path("video.insv"),
    keyframe_path=Path("frame.jpg"),
    prefer_subjects=True  # Prioritize humans
)

print(f"Best perspective: {perspective}")
print(f"Score: {score.overall_score:.1f}/10")
print(f"Reason: {score.rationale}")
```

### Manual Frame Analysis

```python
from src.analytics import SceneAnalyzer

analyzer = SceneAnalyzer()
result = analyzer.analyze_frame(Path("frame.jpg"))

print(f"Subjects: {result.human_count}")
print(f"Confidence: {result.human_confidence:.2f}")
print(f"Scenery: {result.scenery_quality:.1f}/10")
print(f"Composition: {result.composition_score:.1f}/10")
print(f"Colors: {result.dominant_colors}")
```

### Export to CSV for Analysis

```bash
# Reports automatically saved, but you can also:
python -c "
from pathlib import Path
from src.analytics import TraceabilityLogger

logger = TraceabilityLogger(Path('data/working/stage3_vision_editor'))
logger.export_decisions('file_id', format='csv')
"
```

---

## Next Steps

1. **Run with verbose logging** to see detailed decisions
2. **Review traceability reports** to understand perspective selection
3. **Verify scene analytics** match visual inspection
4. **Compare selected perspective** with your manual choice
5. **Fine-tune scoring weights** if needed (future enhancement)

---

## Resources

📖 **Full Documentation**: `ANALYTICS_TRACEABILITY_GUIDE.md`  
📊 **Implementation Details**: `PHASE3_ADVANCED_SUMMARY.md`  
📝 **Quick Start**: `QUICK_START.md`  

---

**Last Updated**: 2026-08-02  
**Version**: Phase 3 Advanced  
**Status**: Production-Ready

