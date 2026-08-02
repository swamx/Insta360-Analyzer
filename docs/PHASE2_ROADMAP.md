# Phase 2: Real Model Integration & Production Hardening

## Overview

Phase 2 transforms the tested prototype into a production system by integrating real models, real video processing, and optimization.

**Timeline**: 2-3 weeks  
**Goal**: End-to-end pipeline working with real Insta360 videos

---

## Phase 2 Roadmap

### Week 1: Core Model Integration

#### 1.1 PySceneDetect Integration (Stage 2)
**File**: Update `src/stages/stage2_scene_detection.py`

```python
from scenedetect import detect, AdaptiveDetector, ContentDetector

def _detect_scenes_real(self, video_path: Path) -> List[tuple]:
    """Use PySceneDetect for real scene detection."""
    try:
        # Try adaptive detector first (more accurate)
        scenes = detect(str(video_path), AdaptiveDetector())
        
        if len(scenes) < 2:
            # Fallback to content detector if too few scenes
            scenes = detect(str(video_path), ContentDetector(threshold=27.0))
        
        return scenes
    except Exception as e:
        logger.warning(f"PySceneDetect failed, using fallback: {str(e)}")
        return self._detect_scenes_fallback(video_path)
```

**Tests to Add**:
- `test_real_scene_detection()` - Real video processing
- `test_adaptive_detector()` - Adaptive detection accuracy
- `test_fallback_detection()` - Fallback mechanism
- `test_scene_detection_performance()` - Benchmark timing

---

#### 1.2 Qwen2.5-VL Model Integration (Stage 3)
**File**: Update `src/stages/stage3_vision_editor.py`

```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
import torch

def _load_model_real(self):
    """Load real Qwen2.5-VL model."""
    logger.info(f"Loading {self.model_name}...")
    
    self.model = Qwen2VLForConditionalGeneration.from_pretrained(
        self.model_name,
        device_map="auto",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        load_in_4bit=True,  # 4-bit quantization
    )
    
    self.processor = AutoProcessor.from_pretrained(self.model_name)
    logger.info("Model loaded successfully")

def _score_scene_real(self, scene: Dict[str, Any]) -> Dict[str, Any]:
    """Real LLM scoring of scene."""
    try:
        key_frame_path = scene.get("key_frame_path")
        image = Image.open(key_frame_path).convert("RGB")
        
        prompt = """You are a professional social media video editor.
        
Analyze this clip and return ONLY valid JSON.

Rate these aspects on 1-10 scale:
- scenic_beauty: Natural beauty, composition, lighting
- action: Movement, energy, dynamic content
- emotion: Emotional impact, compelling visual story
- stability: Camera stability, image quality
- blurriness: 1=very blurry, 10=crystal clear

Also provide:
- brief_description: One sentence describing the scene
- is_usable: true if usable in reel, false if poor quality

Return ONLY JSON, no other text:
{
  "scenic_beauty": 8,
  "action": 7,
  "emotion": 9,
  "stability": 8,
  "blurriness": 9,
  "brief_description": "Mountain landscape with sunset",
  "is_usable": true,
  "overall_score": 8.2
}"""
        
        # Prepare input
        text = self.processor.apply_chat_template(
            [{"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": prompt}
            ]}],
            tokenize=False,
            add_generation_prompt=True
        )
        
        image_input = self.processor(
            text=text,
            images=[image],
            padding=True,
            return_tensors="pt"
        )
        
        # Generate response
        with torch.no_grad():
            output_ids = self.model.generate(
                **image_input,
                max_new_tokens=256,
                temperature=0.7,
            )
        
        response_text = self.processor.batch_decode(
            output_ids,
            skip_special_tokens=True
        )[0]
        
        # Parse JSON response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            score_data = json.loads(json_match.group())
        else:
            score_data = self._default_score()
        
        return score_data
    
    except Exception as e:
        logger.warning(f"Real scoring failed: {str(e)}, using mock")
        return self._mock_score(scene)
```

**Tests to Add**:
- `test_real_model_loading()` - Model loads correctly
- `test_real_scene_scoring()` - Real LLM scoring
- `test_scoring_json_parsing()` - JSON extraction from response
- `test_scoring_fallback_on_error()` - Falls back to mock on error
- `test_scoring_performance()` - Benchmark per-frame timing

---

#### 1.3 LLM-Based Reel Assembly (Stage 4)
**File**: Update `src/stages/stage4_reel_assembly.py`

```python
def _assemble_reel_with_llm(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Use LLM to create optimal 15-second reel."""
    
    # Prepare scene data for LLM
    scene_data = []
    for scene in scenes[:20]:  # Top 20 scenes
        scene_data.append({
            "scene_id": scene["scene_id"],
            "duration": scene["duration_seconds"],
            "score": scene.get("overall_score", 5.0),
            "description": scene.get("brief_description", "Scene"),
            "start_time_ms": scene.get("start_time_ms", 0),
            "end_time_ms": scene.get("end_time_ms", 0),
        })
    
    prompt = f"""Create a 15-second Instagram Reel from these scored scenes.

Available scenes (sorted by quality):
{json.dumps(scene_data, indent=2)}

Requirements:
- Total duration ≤15 seconds
- Fast-paced, engaging flow
- Start with strongest hook (first 2 seconds high-energy)
- Keep individual clips between 1.5 and 3 seconds
- Avoid repetitive/similar scenes back-to-back
- Alternate between close-ups and wide shots if possible
- End with the most cinematic shot
- Prefer scenes with high scores (>7.0)
- Create visual variety and narrative flow

Return ONLY valid JSON:
{{
  "total_duration": 14.8,
  "reasoning": "Editorial choices explanation",
  "clips": [
    {{"scene_id": "...", "start_ms": 1000, "end_ms": 3500, "clip_duration": 2.5}},
    ...
  ]
}}"""
    
    try:
        # Call LLM (Qwen2.5-VL or other model)
        response = self._call_llm(prompt)
        
        # Parse response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            reel_plan = json.loads(json_match.group())
        else:
            reel_plan = self._default_reel_plan(scenes)
        
        return reel_plan
    
    except Exception as e:
        logger.warning(f"LLM reel assembly failed: {str(e)}, using heuristic")
        return self._default_reel_plan(scenes)
```

**Tests to Add**:
- `test_llm_reel_assembly()` - LLM creates valid reel plan
- `test_reel_duration_validation()` - LLM respects 15s limit
- `test_reel_clip_ordering()` - LLM orders clips logically
- `test_reel_fallback_on_error()` - Falls back to heuristic

---

### Week 2: FFmpeg & Encoding

#### 2.1 Real FFmpeg Encoding (Stage 5)
**File**: Update `src/stages/stage5_encoding.py`

```python
def run(self, file_id: str, source_video: Path, reel_plan_checkpoint: Dict, resume_from: Optional[int] = None) -> StageResult:
    """Encode final reel using real FFmpeg."""
    self._log_stage_start(file_id)
    
    try:
        source_video = Path(source_video)
        reel_plan = reel_plan_checkpoint.get("reel_plan", {})
        clips = reel_plan.get("clips", [])
        
        if not clips:
            return StageResult(success=False, message="No clips to encode")
        
        # Determine start index for resume
        start_idx = resume_from or 0
        if resume_from is None:
            checkpoint = self.checkpoint_manager.load_file_checkpoint(file_id, self.stage_name)
            start_idx = checkpoint.get("stage_progress", {}).get(self.stage_name, {}).get("last_encoded_clip", -1) + 1
        
        temp_clips_dir = Path("data/working/temp_clips")
        temp_clips_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_clips = []
        
        # Extract clips from source video
        for idx in range(start_idx, len(clips)):
            clip = clips[idx]
            output_path = temp_clips_dir / f"clip_{idx:02d}.mp4"
            
            success = self._extract_clip(
                source_video,
                output_path,
                clip["start_ms"] / 1000.0,
                clip["end_ms"] / 1000.0
            )
            
            if success:
                extracted_clips.append(str(output_path))
                
                # Save progress checkpoint
                checkpoint_data = self._create_progress_checkpoint(
                    file_id, clips, extracted_clips, idx
                )
                self.checkpoint_manager.save_file_checkpoint(
                    file_id, self.stage_name, checkpoint_data
                )
            else:
                logger.warning(f"Failed to extract clip {idx}")
        
        if not extracted_clips:
            return StageResult(success=False, message="No clips extracted")
        
        # Create concat file for FFmpeg
        concat_file = Path("data/working") / f"{file_id}_concat.txt"
        with open(concat_file, "w") as f:
            for clip_path in extracted_clips:
                f.write(f"file '{clip_path}'\n")
        
        # Concatenate and encode to vertical format
        output_reel = Path("data/output") / f"{file_id}_reel.mp4"
        output_reel.parent.mkdir(parents=True, exist_ok=True)
        
        success = self._concatenate_and_encode(concat_file, output_reel)
        
        if not success or not output_reel.exists():
            return StageResult(success=False, message="Encoding failed")
        
        # Verify duration
        duration = self._get_video_duration(output_reel)
        
        if duration > 15.5:  # Allow 0.5s tolerance
            logger.warning(f"Reel duration {duration}s exceeds 15s limit")
        
        # Final checkpoint
        checkpoint_data = {
            "stage": self.stage_name,
            "file_id": file_id,
            "output_path": str(output_reel),
            "final_duration_seconds": duration,
            "file_size_mb": output_reel.stat().st_size / (1024**2),
            "clips_encoded": len(extracted_clips),
            "status": "ENCODED",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        self.checkpoint_manager.save_file_checkpoint(file_id, self.stage_name, checkpoint_data)
        
        # Update metadata
        metadata = self.checkpoint_manager.load_file_metadata(file_id)
        metadata["state"] = "COMPLETED"
        metadata["output_path"] = checkpoint_data["output_path"]
        metadata["stage_timestamps"]["COMPLETED"] = datetime.utcnow().isoformat() + "Z"
        self.checkpoint_manager.save_file_metadata(file_id, metadata)
        
        self._log_stage_complete(file_id)
        return StageResult(
            success=True,
            message=f"Encoded reel: {output_reel.name}",
            data={
                "output_path": str(output_reel),
                "duration": duration,
                "file_size_mb": checkpoint_data["file_size_mb"],
            }
        )
    
    except Exception as e:
        logger.exception(f"[{file_id}] Stage 5 failed: {str(e)}")
        return StageResult(success=False, message=f"Encoding failed: {str(e)}")

@staticmethod
def _extract_clip(source_video: Path, output_path: Path, start_seconds: float, end_seconds: float) -> bool:
    """Extract clip segment from video."""
    duration_s = end_seconds - start_seconds
    
    cmd = [
        "ffmpeg",
        "-i", str(source_video),
        "-ss", str(start_seconds),
        "-to", str(end_seconds),
        "-c:v", "libx264",
        "-preset", "ultrafast",  # Speed for intermediate clips
        "-crf", "28",            # Quality for intermediate
        "-c:a", "aac",
        str(output_path),
        "-y",  # Overwrite
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    return result.returncode == 0

@staticmethod
def _concatenate_and_encode(concat_file: Path, output_path: Path) -> bool:
    """Concatenate clips and encode to vertical format."""
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",            # Higher quality for final
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
        "-y",
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=1200)
    return result.returncode == 0
```

**Tests to Add**:
- `test_real_clip_extraction()` - Extract real video segments
- `test_real_concatenation()` - Concatenate multiple clips
- `test_vertical_encoding()` - Output is 1080×1920
- `test_encoding_with_audio()` - Audio preserved
- `test_duration_accuracy()` - Duration matches plan
- `test_encoding_performance()` - Benchmark timing

---

### Week 2-3: End-to-End Testing & Optimization

#### 3.1 End-to-End Test Suite
**File**: Create `tests/integration/test_end_to_end_real.py`

```python
def test_full_pipeline_with_real_video():
    """Process real Insta360 video through entire pipeline."""
    # 1. Create test video or use fixture
    # 2. Run full pipeline: Discovery → Scenes → Vision → Reel → Encode
    # 3. Verify:
    #    - Scenes detected (>5)
    #    - All scenes scored
    #    - Reel plan ≤15s
    #    - Final MP4 created
    #    - Duration accurate
    #    - Video plays correctly

def test_resume_with_real_video():
    """Verify resume works across all stages with real video."""
    # 1. Run stages 1-2
    # 2. Simulate failure in stage 3
    # 3. Resume from stage 3
    # 4. Verify:
    #    - No duplication
    #    - Same final output as continuous run

def test_large_video_processing():
    """Process 1-hour Insta360 video."""
    # Performance targets:
    # - Scene detection: <10 min
    # - Vision analysis: <45 min
    # - Reel assembly: <1 min
    # - Encoding: <5 min
    # Total: <90 min on RTX 3060

def test_error_recovery_all_stages():
    """Inject errors at each stage, verify recovery."""
```

---

#### 3.2 Performance Optimization
**File**: New `src/optimization/performance.py`

```python
class PerformanceOptimizer:
    """Optimize processing speed."""
    
    def optimize_model_inference(self, model, processor):
        """Optimize Qwen2.5-VL inference."""
        # 1. Batch processing of frames
        # 2. KV cache optimization
        # 3. Attention patterns tuning
        # 4. ONNX runtime option
        # 5. Quantization validation
        pass
    
    def parallelize_frame_extraction(self, video_path):
        """Extract frames in parallel."""
        # 1. Split video into segments
        # 2. Process segments in parallel
        # 3. Merge results maintaining order
        pass
    
    def cache_model_state(self):
        """Cache model for warm starts."""
        pass
    
    def monitor_memory_usage(self):
        """Track VRAM/RAM during processing."""
        pass
```

---

## Updated Requirements

**Add to `requirements.txt`**:
```
scenedetect==0.6.1
# transformers and torch already there
opencv-python==4.8.1.78  # May need for video frame operations
```

---

## Testing Strategy for Phase 2

### Unit Tests (existing)
- Checkpoint atomicity
- Recovery logic
- Data structures

### Integration Tests (NEW)
- Real scene detection accuracy
- Real model scoring
- LLM-based reel assembly
- Real FFmpeg encoding
- Vertical format output
- Duration validation

### End-to-End Tests (NEW)
- Full pipeline with real video
- Resume capability with real data
- Large video (1-hour) processing
- Error injection and recovery
- Performance benchmarking

### Manual Testing (NEW)
- Process actual Insta360 video
- Verify output quality
- Check Instagram compatibility
- Validate vertical format on mobile

---

## Success Criteria for Phase 2

- [ ] PySceneDetect integration working
- [ ] Real Qwen2.5-VL model inference working
- [ ] LLM-based reel assembly implemented
- [ ] Real FFmpeg encoding functional
- [ ] End-to-end test passes with real video
- [ ] Resume works end-to-end with real data
- [ ] Performance: <90 min for 1-hour video
- [ ] Output MP4 verified on mobile
- [ ] All 80 existing tests still passing
- [ ] 30+ new tests for Phase 2
- [ ] Code properly documented
- [ ] Error handling comprehensive

---

## Implementation Order

**Week 1 Priority**:
1. PySceneDetect integration (Stage 2)
2. Qwen2.5-VL model integration (Stage 3)
3. Tests for both

**Week 2 Priority**:
4. LLM-based reel assembly (Stage 4)
5. Real FFmpeg encoding (Stage 5)
6. Tests for both

**Week 2-3 Priority**:
7. End-to-end testing
8. Performance optimization
9. Production hardening
10. Documentation

---

## Deployment Checklist

Before going to production:

- [ ] All tests passing (>110 tests)
- [ ] Real Insta360 video tested
- [ ] Performance benchmarked
- [ ] Error recovery verified
- [ ] Memory profiling complete
- [ ] No hardcoded paths
- [ ] Logging comprehensive
- [ ] Configuration externalized
- [ ] Documentation complete
- [ ] Recovery scenarios documented

---

## Phase 2 Estimated Effort

| Component | Effort | Tests |
|-----------|--------|-------|
| PySceneDetect | 2-3 days | 4 tests |
| Qwen2.5-VL | 3-4 days | 5 tests |
| LLM Reel Assembly | 2-3 days | 4 tests |
| Real FFmpeg | 2-3 days | 6 tests |
| End-to-End | 2-3 days | 8 tests |
| Optimization | 2-3 days | - |
| **Total** | **~2-3 weeks** | **~30 tests** |

---

This Phase 2 roadmap takes the tested architecture and brings it to production with real models, real video processing, and comprehensive testing. The modular design allows independent development on each component with thorough testing before integration.
