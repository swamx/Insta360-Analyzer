# Phase 1 Roadmap: Stages 4-5 & End-to-End Testing

## Current Status
✅ Phase 0 Complete (39/39 tests passing)
- Stages 1-3: Fully implemented
- Checkpoint/resume: Validated
- Insta360 support: Integrated

---

## Phase 1 Goals

| Goal | Est. Time | Priority |
|------|-----------|----------|
| Implement Stage 4: Highlight Detection | 1 week | **High** |
| Implement Stage 5: Clip Encoding | 1 week | **High** |
| End-to-end testing with real videos | 3 days | **High** |
| Performance optimization | 3 days | **Medium** |
| **Phase 1 Total** | **~2 weeks** | - |

---

## Stage 4: Highlight Detection

### What It Does
Analyzes frame embeddings to identify interesting clips suitable for Instagram.

### Implementation Plan

#### 4.1 Scene Change Detection
**File**: `src/stages/stage4_highlights.py`

```python
class Stage4Highlights(Stage):
    """Detect scene changes and interesting segments."""
    
    def _detect_scene_changes(self, embeddings):
        """Find boundaries where scenes change significantly."""
        # Input: (N, 1024) embeddings from Stage 3
        # Output: List of (start_frame, end_frame) tuples
        
        # Algorithm:
        # 1. Compute embedding distance between consecutive frames
        # 2. Find peaks in distance (scene boundaries)
        # 3. Filter by minimum distance threshold
        pass
    
    def _score_segment(self, frames, embeddings, start, end):
        """Score a clip segment by interest."""
        # Score based on:
        # - Embedding uniqueness (distance from other frames)
        # - Motion (frame-to-frame changes)
        # - Object presence (from Stage 3 analysis)
        # - Length (prefer 15-60s clips)
        pass
    
    def run(self, file_id, embeddings_path, checkpoint):
        """Detect highlights and segment into clips."""
        # 1. Load embeddings from Stage 3 checkpoint
        # 2. Detect scene boundaries
        # 3. Score each segment
        # 4. Rank segments by score
        # 5. Select top 3-5 clips
        # 6. Save to checkpoint
        pass
```

#### 4.2 Key Methods

**Scene Boundary Detection**:
```python
def _detect_scene_changes(self, embeddings, threshold=0.5):
    """Detect scene changes via embedding distance."""
    # euclidean_distance between consecutive frames
    distances = np.linalg.norm(np.diff(embeddings, axis=0), axis=1)
    
    # Find peaks (sudden jumps)
    boundaries = np.where(distances > threshold)[0]
    
    return boundaries
```

**Clip Scoring**:
```python
def _score_segment(self, embeddings, start, end):
    """Score clip by uniqueness and consistency."""
    segment = embeddings[start:end]
    
    # Uniqueness: distance from overall mean
    uniqueness = np.mean(np.linalg.norm(
        segment - embeddings.mean(axis=0),
        axis=1
    ))
    
    # Consistency: low variance within segment
    consistency = 1.0 / (1.0 + np.std(segment, axis=0).mean())
    
    # Length score: prefer 15-60s (prefer ~30s)
    length_frames = end - start
    length_score = 1.0 if 15 <= length_frames <= 60 else 0.5
    
    # Combined score
    score = 0.4*uniqueness + 0.3*consistency + 0.3*length_score
    return score
```

#### 4.3 Tests for Stage 4

**New test file**: `tests/integration/test_stage4_highlights.py`

```python
def test_detect_scene_changes():
    """Verify scene boundary detection."""
    # Create mock embeddings with clear changes
    embeddings = create_test_embeddings_with_changes()
    
    stage = Stage4Highlights()
    boundaries = stage._detect_scene_changes(embeddings)
    
    # Verify boundaries found at expected locations
    assert len(boundaries) > 0

def test_clip_scoring():
    """Verify clip segments are scored correctly."""
    embeddings = create_test_embeddings()
    stage = Stage4Highlights()
    
    # Score a segment
    score = stage._score_segment(embeddings, 0, 30)
    assert 0.0 <= score <= 1.0

def test_highlight_detection_end_to_end():
    """Full highlight detection workflow."""
    # 1. Load embeddings from Stage 3
    # 2. Run Stage 4
    # 3. Verify clips identified
    # 4. Verify checkpoint saved
    pass

def test_top_clips_ranking():
    """Verify top clips ranked by score."""
    # Generate clips with different scores
    # Verify ordering is correct
    pass
```

#### 4.4 Checkpoint Format

```json
{
  "stage": "stage4_highlights",
  "file_id": "file_001",
  "clips": [
    {
      "clip_id": "file_001_clip_001",
      "start_frame": 100,
      "end_frame": 200,
      "start_time_ms": 5000,
      "end_time_ms": 10000,
      "duration_seconds": 5.0,
      "score": 0.92,
      "reason": "scene_change + high_uniqueness",
      "objects": ["person", "action"],
      "status": "PENDING_ENCODING"
    },
    ...
  ],
  "total_clips_found": 15,
  "top_clips_selected": 3,
  "timestamp": "2024-08-02T12:00:00Z"
}
```

---

## Stage 5: Clip Encoding

### What It Does
Extracts identified clips from the source video and encodes them as MP4 files ready for Instagram.

### Implementation Plan

#### 5.1 Clip Extraction & Encoding
**File**: `src/stages/stage5_encoding.py`

```python
class Stage5Encoding(Stage):
    """Extract and encode video clips."""
    
    def _extract_clip(self, input_video, output_path, start_ms, end_ms):
        """Extract clip from video using FFmpeg."""
        # Input: video path, start time (ms), end time (ms)
        # Output: MP4 clip file
        
        # FFmpeg command:
        # ffmpeg -i input.mp4 -ss START -to END -c:v libx264 -c:a aac output.mp4
        pass
    
    def _apply_filters(self, clip_path):
        """Apply optional filters (brightness, contrast, stabilization)."""
        # For now: basic quality encoding
        # Future: add effects, text overlays
        pass
    
    def run(self, file_id, source_video, clips_metadata, checkpoint):
        """Encode identified clips to MP4."""
        # 1. Load clips from Stage 4 checkpoint
        # 2. For each clip:
        #    a. Extract segment from source video
        #    b. Encode to MP4
        #    c. Verify output
        #    d. Update checkpoint
        # 3. Save all clips to output directory
        pass
```

#### 5.2 Key Methods

**Clip Extraction**:
```python
def _extract_clip(self, input_video, output_path, start_ms, end_ms):
    """Extract clip from video."""
    duration_s = (end_ms - start_ms) / 1000.0
    start_s = start_ms / 1000.0
    
    cmd = [
        "ffmpeg",
        "-i", str(input_video),
        "-ss", str(start_s),
        "-to", str(start_s + duration_s),
        "-c:v", "libx264",
        "-preset", "medium",          # Speed vs quality
        "-crf", "23",                 # Quality (0-51, lower=better)
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
        "-y",  # Overwrite
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    return result.returncode == 0
```

**Progress Tracking**:
```python
def run(self, file_id, source_video, clips_metadata, checkpoint):
    """Encode all clips with checkpoint saves."""
    clips = clips_metadata["clips"]
    
    for idx, clip in enumerate(clips):
        clip_id = clip["clip_id"]
        output_path = self.output_dir / f"{clip_id}.mp4"
        
        # Extract and encode
        success = self._extract_clip(
            source_video,
            output_path,
            clip["start_time_ms"],
            clip["end_time_ms"]
        )
        
        # Update checkpoint after each clip
        clip["status"] = "ENCODED" if success else "FAILED"
        checkpoint["encoded_clips"] = idx + 1
        checkpoint["timestamp"] = datetime.utcnow().isoformat()
        
        self.checkpoint_manager.save_file_checkpoint(
            file_id,
            self.stage_name,
            checkpoint
        )
```

#### 5.3 Tests for Stage 5

**New test file**: `tests/integration/test_stage5_encoding.py`

```python
def test_clip_extraction():
    """Verify clip extraction from video."""
    # Create test video with known content
    # Extract clip
    # Verify duration and content
    pass

def test_encoding_quality():
    """Verify output MP4 meets quality requirements."""
    # Extract clip
    # Check: video codec, audio codec, bitrate
    pass

def test_resume_encoding():
    """Verify encoding can resume from checkpoint."""
    # Extract 3 clips
    # Interrupt after 1st clip
    # Resume
    # Verify no duplication (3 clips total, not 5)
    pass

def test_all_clips_encoded():
    """Verify all clips from Stage 4 are encoded."""
    # Create checkpoint with 5 clips
    # Run encoding
    # Verify 5 MP4 files created
    pass
```

#### 5.4 Checkpoint Format

```json
{
  "stage": "stage5_encoding",
  "file_id": "file_001",
  "source_video": "/path/to/video.mp4",
  "clips_encoded": [
    {
      "clip_id": "file_001_clip_001",
      "output_path": "data/output/file_001_clip_001.mp4",
      "file_size_mb": 45.2,
      "duration_seconds": 30.0,
      "status": "ENCODED",
      "timestamp": "2024-08-02T12:15:00Z"
    },
    ...
  ],
  "total_clips": 3,
  "encoded_clips": 3,
  "failed_clips": 0,
  "timestamp": "2024-08-02T12:20:00Z"
}
```

---

## End-to-End Testing

### 5.1 Integration Test Plan

**New test file**: `tests/integration/test_end_to_end_pipeline.py`

```python
def test_full_pipeline_small_video():
    """Process 1-minute test video through all stages."""
    # 1. Stage 1: Discover (metadata)
    # 2. Stage 2: Extract frames
    # 3. Stage 3: Analyze frames
    # 4. Stage 4: Detect highlights (expect 2-3 clips)
    # 5. Stage 5: Encode clips
    # 6. Verify output MP4 files created
    
    input_video = "tests/fixtures/test_video_1min.mp4"
    result = pipeline.process_file("test_e2e_001", input_video)
    
    assert result["success"]
    assert len(output_clips) >= 2
    assert all(clip.exists() for clip in output_clips)

def test_recovery_across_all_stages():
    """Test resume capability across all 5 stages."""
    # Run through stage 3
    # Simulate crash
    # Resume
    # Verify stages 1-3 skipped, stages 4-5 run
    # Verify no duplication
    pass

def test_real_insta360_video():
    """Process real Insta360 video end-to-end."""
    # Use actual .insv file
    # Verify format detection
    # Verify stitching
    # Full pipeline
    # Verify output quality
    pass
```

### 5.2 Real Video Testing

**Create test video**:
```bash
# If you have Insta360 videos:
# Copy sample.insv to tests/fixtures/
# Run:
python main.py --input tests/fixtures/sample.insv --verbose
python main.py --status <file_id>
```

**Verify output**:
```
data/output/
├── file_001_clip_001.mp4  (30-40MB, 30s duration)
├── file_001_clip_002.mp4
└── file_001_clip_003.mp4
```

---

## Performance Optimization

### 6.1 Bottlenecks to Address

| Stage | Bottleneck | Solution | Est. Time |
|-------|-----------|----------|-----------|
| Stage 3 | Model inference | Batch optimization, GPU tuning | 2 days |
| Stage 5 | Video encoding | Parallel encoding (2-3 clips at once) | 2 days |
| Overall | Frame I/O | Preprocessing cache | 1 day |

### 6.2 Optimization Plan

**Parallel Encoding** (Stage 5):
```python
def run_parallel(self, clips, num_workers=2):
    """Encode multiple clips in parallel."""
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for clip in clips:
            future = executor.submit(self._extract_clip, clip)
            futures.append(future)
        
        results = [f.result() for f in futures]
    
    return results
```

**Batch Optimization** (Stage 3):
```python
def _estimate_batch_size(self):
    """Dynamically adjust batch size based on VRAM."""
    available_gb = get_available_memory_gb()
    
    # Heuristic: model takes ~1.8GB, each frame ~5MB
    # Safe batch size = (available - 2GB) / 0.005GB
    batch_size = int((available_gb - 2.0) / 0.005)
    return max(1, min(batch_size, 64))
```

---

## Implementation Schedule

### Week 1: Stages 4-5
```
Day 1-2: Stage 4 (highlight detection)
  - Scene change detection
  - Clip scoring
  - Tests

Day 3-4: Stage 5 (clip encoding)
  - FFmpeg integration
  - Progress tracking
  - Resume capability
  - Tests

Day 5: End-to-end integration
  - Full pipeline tests
  - Bug fixes
  - Documentation
```

### Week 2: Testing & Optimization
```
Day 1-2: Real video testing
  - Test with Insta360 videos
  - Verify output quality
  - Fix edge cases

Day 3: Performance optimization
  - Benchmark Stage 3 inference
  - Optimize Stage 5 encoding
  - Test on slower hardware

Day 4-5: Polish & documentation
  - Code cleanup
  - Update ARCHITECTURE.md
  - Write completion guide
```

---

## Success Criteria: Phase 1

- [ ] Stage 4 fully implemented (scene detection + scoring)
- [ ] Stage 5 fully implemented (clip encoding)
- [ ] All 50+ tests pass (including new Stage 4-5 tests)
- [ ] End-to-end pipeline works (input → output clips)
- [ ] Resume works across all 5 stages
- [ ] Real Insta360 video processed successfully
- [ ] Output MP4s verified (correct duration, quality)
- [ ] Performance benchmarked (< 4 hours for 1-hour video)

---

## Files to Create

### New Source Files
```
src/stages/stage4_highlights.py    (300-400 lines)
src/stages/stage5_encoding.py      (250-350 lines)
```

### New Test Files
```
tests/integration/test_stage4_highlights.py     (200+ lines)
tests/integration/test_stage5_encoding.py       (200+ lines)
tests/integration/test_end_to_end_pipeline.py   (150+ lines)
```

### Test Fixtures
```
tests/fixtures/test_video_1min.mp4   (test video)
tests/fixtures/test_embeddings.npy   (pre-computed)
```

### Documentation
```
docs/HIGHLIGHT_DETECTION.md
docs/CLIP_ENCODING.md
PHASE1_COMPLETION.md
```

---

## Git Commits (Phase 1)

Expected 5-6 commits:
1. Implement Stage 4 with tests
2. Implement Stage 5 with tests
3. End-to-end pipeline testing
4. Performance optimization
5. Real video testing results
6. Phase 1 completion summary

---

## Ready to Start?

### Next Command
```bash
# Create Stage 4 implementation
# 1. Copy structure from stage3_analysis.py
# 2. Implement scene detection
# 3. Implement scoring
# 4. Write tests
# 5. Commit

# Or let me know if you want me to implement it!
```

---

## Questions to Answer First

1. **Output format**: Instagram Reels, TikTok, or both?
   - Instagram: 1080×1920 (vertical), 15-60s
   - TikTok: Same specs
   - Both use H.264 video codec

2. **Clip quantity**: Always 3 clips per video, or top-N scoring?
   - Option A: Always exactly 3 clips
   - Option B: 1-5 clips depending on video quality

3. **Video quality**: Optimize for quality or file size?
   - Option A: High quality (CRF 18-20) → 80-120MB per clip
   - Option B: Balanced (CRF 23-25) → 30-50MB per clip
   - Option C: Optimized (CRF 28-30) → 10-20MB per clip

---

**Ready to implement Stage 4 & 5!** 🚀
