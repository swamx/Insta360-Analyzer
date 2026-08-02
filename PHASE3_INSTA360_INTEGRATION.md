# Phase 3: Insta360 SDK Integration & Real Analysis

**Status**: Planning  
**Goal**: Convert 360° videos to single-perspective view + real scene analysis

---

## Architecture Changes

### Current (Phase 2):
```
.insv (360°) → Scene Detection → Mock Scoring → Reel Assembly → Encoding
```

### Target (Phase 3):
```
.insv (360°) → Insta360 SDK (Stabilize) → Single-Person View → 
  Real Scene Detection → Real Qwen2.5-VL Scoring → Reel Assembly → Encoding
```

---

## Phase 3 Implementation Plan

### Stage 0.5: Insta360 Format Conversion (NEW)
**File**: `src/stages/stage0_insta360_conversion.py`

**Purpose**: Convert 360° video to single-perspective view

**Features**:
- Detect if video is 360° format (.insv)
- Use Insta360 SDK to:
  - Extract stabilization metadata
  - Convert to equirectangular projection
  - Follow object/person detection
  - Generate single-perspective output
- Output: Stabilized single-view MP4

**Insta360 SDK Options**:
1. **Official Insta360 SDK** (if available)
2. **FFmpeg with Insta360 filters**
3. **Custom perspective tracking**

### Stage 2: Real Scene Detection (UPDATED)
**Current**: Mock 5-second chunks  
**Target**: Real PySceneDetect integration

**Changes**:
- Remove fallback detection
- Use real PySceneDetect
- Detect actual scene boundaries
- Extract representative keyframes

### Stage 3: Real Vision Analysis (UPDATED)
**Current**: Mock scoring  
**Target**: Real Qwen2.5-VL model

**Changes**:
- Load real Qwen2.5-VL model
- Score scenes as professional editor
- Multi-dimensional analysis:
  - Scenic beauty
  - Action/movement
  - Emotional impact
  - Stability
  - Clarity
- GPU-accelerated inference

### Stage 4-5: Reel Assembly & Encoding (UNCHANGED)
- Use real reel assembly
- Vertical format encoding
- Unlimited duration support

---

## Implementation Steps

### Step 1: Insta360 SDK Research & Integration
```
Tasks:
1. Research available Insta360 SDK options
2. Determine .insv file format details
3. Extract video metadata and format info
4. Implement format conversion pipeline
5. Test with sample Insta360 video
```

### Step 2: Real Scene Detection
```
Tasks:
1. Install PySceneDetect
2. Integrate AdaptiveDetector
3. Extract accurate scene boundaries
4. Test on converted video
```

### Step 3: Real Vision Model
```
Tasks:
1. Load Qwen2.5-VL model (non-quantized for accuracy)
2. Implement professional editor prompting
3. Score scenes with real analysis
4. Cache model for performance
```

### Step 4: End-to-End Testing
```
Tasks:
1. Test full pipeline with .insv video
2. Verify 360→single-view conversion
3. Validate scene detection accuracy
4. Test reel quality
```

---

## Technical Challenges & Solutions

### Challenge 1: Insta360 SDK Availability
**Options**:
- Use official Insta360 SDK (if available)
- Extract .insv using FFmpeg
- Implement custom converter
- Use third-party libraries

**Recommendation**: Research official SDK first

### Challenge 2: Perspective Selection
**Options**:
- Follow detected person/object
- Use rule-based perspective (e.g., forward-facing)
- User-specified direction
- Multiple perspectives (bundle output)

**Recommendation**: Start with rule-based, add tracking later

### Challenge 3: Real Model Performance
**Options**:
- 4-bit quantization (faster, less accurate)
- Full precision (slower, more accurate)
- Batching & caching
- Multi-GPU inference

**Recommendation**: Full precision with caching for real scene understanding

### Challenge 4: Video Stability
**Goal**: Smooth, stabilized perspective view

**Solutions**:
- Use Insta360 stabilization metadata
- Apply FFmpeg stabilization filter
- Implement gimbal-like tracking
- Post-process smoothing

---

## File Structure (Phase 3)

```
src/
├── stages/
│   ├── stage0_insta360_conversion.py    (NEW - 300 lines)
│   ├── stage1_discovery.py              (UNCHANGED)
│   ├── stage2_scene_detection.py        (UPDATED - real PySceneDetect)
│   ├── stage3_vision_editor.py          (UPDATED - real Qwen2.5-VL)
│   ├── stage4_reel_assembly.py          (UNCHANGED)
│   └── stage5_encoding.py               (UNCHANGED)
├── insta360/
│   ├── detector.py                      (NEW - Format detection)
│   ├── converter.py                     (NEW - 360→single-view)
│   └── stabilizer.py                    (NEW - Video stabilization)
└── processing/
    └── insta360_converter.py            (Existing, enhance)
```

---

## Expected Outcomes

### Input:
- Insta360 .insv video (360° format)
- 140MB, ~10 minutes

### Output:
- **Converted Video**: Single-perspective, stabilized
- **Scene Analysis**: Real boundaries detected
- **Quality Scores**: Professional video editor judgment
- **Final Reel**: 8-15 second vertical MP4
  - Size: 4-8MB
  - Quality: High
  - Format: 1080×1920 (Instagram Reels)

---

## Success Criteria

- ✅ Detect .insv format correctly
- ✅ Convert 360° to single-perspective
- ✅ Maintain video quality post-conversion
- ✅ Real scene detection working
- ✅ Real vision model scoring
- ✅ End-to-end pipeline functional
- ✅ Output ready for Instagram

---

## Next Steps

1. Research Insta360 SDK options
2. Implement Stage 0.5 (Insta360 conversion)
3. Integrate real PySceneDetect
4. Load real Qwen2.5-VL model
5. End-to-end testing
6. Performance optimization
7. Production deployment

---

## Estimated Timeline

- **Research**: 1-2 hours
- **SDK Integration**: 2-4 hours
- **Real Scene Detection**: 1 hour
- **Real Vision Model**: 2-3 hours
- **Testing**: 2-3 hours
- **Total**: 8-13 hours (1-2 days)

---

This Phase 3 upgrade will transform the analyzer from a demo with mock scoring to a production-grade system that truly understands Insta360 video content and creates professional-quality reels.
