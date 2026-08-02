# Phase 1 Updated: AI-Driven 15-Second Reel Generation

## New Architecture (Much Better!)

```
Insta360 Videos (.insv, .mp4)
       │
       ▼
[STAGE 1] Discovery
   └─ File cataloging & metadata
       │
       ▼
[STAGE 2] Scene Detection (PySceneDetect)
   ├─ Detect scene boundaries
   ├─ Extract key frames per scene
   └─ Save scene metadata (timestamps, durations)
       │
       ▼
[STAGE 3] Vision Analysis (Qwen2.5-VL as Editor)
   ├─ Load key frames from each scene
   ├─ Prompt LLM as "professional video editor"
   ├─ Score each scene (beauty, action, emotion, stability)
   ├─ Detect activities & descriptions
   ├─ Flag blurry/poor quality clips
   └─ Save scoring to checkpoint
       │
       ▼
[STAGE 4] Reel Assembly (LLM)
   ├─ Load all scored scenes
   ├─ Prompt LLM to assemble optimal 15-second reel
   ├─ Get back clip order, timestamps, durations
   ├─ Verify total ≤15 seconds
   └─ Save assembly plan to checkpoint
       │
       ▼
[STAGE 5] Encoding (FFmpeg)
   ├─ Extract segments from source video
   ├─ Concatenate in reel order
   ├─ Encode to vertical 1080×1920 MP4
   ├─ Verify duration
   └─ Save final reel
       │
       ▼
output/
   └─ final_reel.mp4 (15 seconds, Instagram-ready)
```

---

## Stage Changes Summary

| Stage | Old | New | Why |
|-------|-----|-----|-----|
| 1 | Discovery | Discovery | Same (unchanged) |
| 2 | Frame Extraction (every 2s) | **Scene Detection** | PySceneDetect finds actual scene boundaries |
| 3 | Vision Analysis (embeddings) | **Vision Analysis as Editor** | LLM scores and describes scenes |
| 4 | Highlight Detection (heuristics) | **Reel Assembly** | LLM creates optimal 15s sequence |
| 5 | Clip Encoding | Encoding | FFmpeg to concatenate & encode |

---

## Stage 2: Scene Detection (NEW)

### What Changed
**OLD**: Extract frames every 2 seconds (arbitrary)  
**NEW**: Detect actual scene boundaries using PySceneDetect

### Implementation

#### 2.1 Scene Detection Stage
**File**: `src/stages/stage2_scene_detection.py`

```python
from scenedetect import detect, AdaptiveDetector
import subprocess
from pathlib import Path

class Stage2SceneDetection(Stage):
    """Detect scene boundaries in video using PySceneDetect."""
    
    def __init__(self, checkpoint_manager, threshold=27.0):
        super().__init__("stage2_scene_detection")
        self.checkpoint_manager = checkpoint_manager
        self.threshold = threshold  # Scene change sensitivity
    
    def run(self, file_id, video_path, resume_from=None):
        """Detect scenes and extract key frames."""
        self._log_stage_start(file_id)
        
        try:
            video_path = Path(video_path)
            
            # 1. Detect scenes using PySceneDetect
            scenes = self._detect_scenes(video_path)
            
            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scenes detected"
                )
            
            # 2. Extract key frame from each scene
            scene_data = []
            for idx, (start_frame, start_time, end_frame, end_time) in enumerate(scenes):
                key_frame_path = self._extract_key_frame(
                    video_path,
                    start_time,
                    end_time,
                    idx
                )
                
                scene_data.append({
                    "scene_id": f"{file_id}_scene_{idx:03d}",
                    "start_frame": start_frame,
                    "start_time_ms": int(start_time.get_seconds() * 1000),
                    "end_frame": end_frame,
                    "end_time_ms": int(end_time.get_seconds() * 1000),
                    "duration_seconds": end_time.get_seconds() - start_time.get_seconds(),
                    "key_frame_path": str(key_frame_path),
                    "scene_idx": idx,
                })
            
            # 3. Save checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "total_scenes": len(scene_data),
                "scenes": scene_data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )
            
            # 4. Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "SCENES_DETECTED"
            metadata["scene_count"] = len(scene_data)
            metadata["stage_timestamps"]["SCENES_DETECTED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)
            
            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Detected {len(scene_data)} scenes",
                data={"scene_count": len(scene_data)},
            )
        
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 2 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Scene detection failed: {str(e)}",
            )
    
    def _detect_scenes(self, video_path):
        """Detect scene boundaries using PySceneDetect."""
        try:
            # Use adaptive scene detection
            scenes = detect(str(video_path), AdaptiveDetector())
            logger.info(f"Detected {len(scenes)} scenes")
            return scenes
        except Exception as e:
            logger.error(f"PySceneDetect failed: {str(e)}")
            return []
    
    def _extract_key_frame(self, video_path, start_time, end_time, scene_idx):
        """Extract middle frame of scene as key frame."""
        # Extract frame at midpoint of scene
        mid_time = (start_time.get_seconds() + end_time.get_seconds()) / 2.0
        
        output_path = Path("data/working/scenes") / f"scene_{scene_idx:03d}_keyframe.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(mid_time),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
            "-hide_banner",
            "-loglevel", "error",
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and output_path.exists():
            return output_path
        else:
            raise Exception(f"FFmpeg frame extraction failed for scene {scene_idx}")
    
    def can_resume(self, file_id):
        """Scene detection is not resumable (re-run on resume)."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)
    
    def get_progress(self, file_id):
        """Get progress info."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=checkpoint.get("total_scenes", 0),
                completed_items=checkpoint.get("total_scenes", 0),
            )
        return None
```

#### 2.2 Dependencies
Add to `requirements.txt`:
```
scenedetect==0.6.1
```

---

## Stage 3: Vision Analysis as Editor (REDESIGNED)

### Key Difference
**OLD**: Generate embeddings for every frame  
**NEW**: Prompt LLM to score each scene like a professional editor

### Implementation

#### 3.1 Vision Analysis Stage (Editor Mode)
**File**: `src/stages/stage3_vision_editor.py`

```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
import json
import re

class Stage3VisionEditor(Stage):
    """Score scenes using Qwen2.5-VL as a professional video editor."""
    
    def __init__(self, checkpoint_manager, model_name="Qwen/Qwen2-VL-7B-Instruct"):
        super().__init__("stage3_vision_editor")
        self.checkpoint_manager = checkpoint_manager
        self.model_name = model_name
        self.model = None
        self.processor = None
    
    def _load_model(self):
        """Load Qwen2.5-VL model."""
        if self.model is not None:
            return
        
        logger.info(f"Loading {self.model_name}...")
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype="auto",
        )
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        logger.info("Model loaded successfully")
    
    def run(self, file_id, scenes_checkpoint, resume_from=None):
        """Score each scene as a professional video editor."""
        self._log_stage_start(file_id)
        
        try:
            self._load_model()
            
            # Load scenes from Stage 2
            scenes = scenes_checkpoint.get("scenes", [])
            
            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scenes to analyze",
                )
            
            # Score each scene
            scored_scenes = []
            
            for scene_idx, scene in enumerate(scenes):
                logger.info(f"Scoring scene {scene_idx + 1}/{len(scenes)}")
                
                score = self._score_scene(scene)
                scene.update(score)
                scored_scenes.append(scene)
                
                # Save checkpoint after each scene
                checkpoint_data = {
                    "stage": self.stage_name,
                    "file_id": file_id,
                    "total_scenes": len(scenes),
                    "scored_scenes": scored_scenes,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "stage_progress": {
                        self.stage_name: {
                            "total_scenes": len(scenes),
                            "scored_scenes": len(scored_scenes),
                            "last_scene_idx": scene_idx,
                        }
                    },
                }
                
                self.checkpoint_manager.save_file_checkpoint(
                    file_id,
                    self.stage_name,
                    checkpoint_data,
                )
            
            # Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "ANALYZED"
            metadata["stage_timestamps"]["ANALYZED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)
            
            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Scored {len(scored_scenes)} scenes",
                data={"scored_scenes": len(scored_scenes)},
            )
        
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 3 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Vision analysis failed: {str(e)}",
            )
    
    def _score_scene(self, scene):
        """Score a scene as a professional video editor."""
        from PIL import Image
        
        # Load key frame
        key_frame_path = scene["key_frame_path"]
        image = Image.open(key_frame_path).convert("RGB")
        
        # Build editor prompt
        prompt = """You are a professional social media video editor.

Analyze this video scene and return ONLY valid JSON (no markdown, no explanation).

Rate these aspects on 1-10 scale:
- scenic_beauty: Natural beauty, composition, lighting
- action: Movement, energy, dynamic content
- emotion: Emotional impact, compelling visual story
- stability: Camera stability, image quality
- blurriness: 1=very blurry, 10=crystal clear

Also provide:
- brief description: One sentence describing the scene
- is_usable: true if usable in a reel, false if blurry/poor quality

Return ONLY JSON, no other text:
{
  "scenic_beauty": 8,
  "action": 7,
  "emotion": 9,
  "stability": 8,
  "blurriness": 9,
  "brief_description": "Mountain landscape with sunset glow",
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
        
        # Parse JSON from response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                score_data = json.loads(json_match.group())
            else:
                logger.warning("Could not extract JSON from LLM response")
                score_data = self._default_score()
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {response_text}")
            score_data = self._default_score()
        
        return score_data
    
    @staticmethod
    def _default_score():
        """Default score if LLM fails."""
        return {
            "scenic_beauty": 5,
            "action": 5,
            "emotion": 5,
            "stability": 5,
            "blurriness": 5,
            "brief_description": "Scene",
            "is_usable": True,
            "overall_score": 5.0,
        }
    
    def can_resume(self, file_id):
        """Check if can resume from checkpoint."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return False
        
        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        return checkpoint.get("stage_progress", {}).get(self.stage_name) is not None
    
    def get_progress(self, file_id):
        """Get progress info."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            progress = checkpoint.get("stage_progress", {}).get(self.stage_name)
            if progress:
                return ProgressInfo(
                    stage_name=self.stage_name,
                    file_id=file_id,
                    total_items=progress.get("total_scenes", 0),
                    completed_items=progress.get("scored_scenes", 0),
                )
        return None
```

#### 3.2 Checkpoint Format

```json
{
  "stage": "stage3_vision_editor",
  "file_id": "file_001",
  "total_scenes": 42,
  "scored_scenes": [
    {
      "scene_id": "file_001_scene_001",
      "start_time_ms": 0,
      "end_time_ms": 5000,
      "duration_seconds": 5.0,
      "key_frame_path": "data/working/scenes/scene_000_keyframe.jpg",
      "scenic_beauty": 8,
      "action": 7,
      "emotion": 9,
      "stability": 8,
      "blurriness": 9,
      "brief_description": "Mountain landscape with sunset",
      "is_usable": true,
      "overall_score": 8.2
    },
    ...
  ],
  "timestamp": "2024-08-02T12:00:00Z"
}
```

---

## Stage 4: Reel Assembly (LLM) (NEW)

### What It Does
Prompt LLM to create an optimal 15-second reel from scored scenes.

### Implementation

#### 4.1 Reel Assembly Stage
**File**: `src/stages/stage4_reel_assembly.py`

```python
class Stage4ReelAssembly(Stage):
    """Assemble optimal 15-second reel using LLM."""
    
    def __init__(self, checkpoint_manager, max_duration_seconds=15, model_name="Qwen/Qwen2-VL-7B-Instruct"):
        super().__init__("stage4_reel_assembly")
        self.checkpoint_manager = checkpoint_manager
        self.max_duration_seconds = max_duration_seconds
        self.model_name = model_name
        self.model = None
        self.processor = None
    
    def run(self, file_id, scored_scenes_checkpoint, resume_from=None):
        """Assemble optimal 15-second reel."""
        self._log_stage_start(file_id)
        
        try:
            self._load_model()
            
            # Get scored scenes
            scenes = scored_scenes_checkpoint.get("scored_scenes", [])
            
            if not scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No scenes to assemble",
                )
            
            # Filter usable scenes and sort by score
            usable_scenes = [s for s in scenes if s.get("is_usable", True)]
            usable_scenes.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            
            if not usable_scenes:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No usable scenes found",
                )
            
            # Prepare scene data for LLM
            scene_data = []
            for scene in usable_scenes[:20]:  # Top 20 scenes
                scene_data.append({
                    "scene_id": scene["scene_id"],
                    "duration": scene["duration_seconds"],
                    "score": scene["overall_score"],
                    "description": scene["brief_description"],
                    "start_time_ms": scene["start_time_ms"],
                    "end_time_ms": scene["end_time_ms"],
                })
            
            # Prompt LLM to assemble reel
            reel_plan = self._assemble_reel_with_llm(scene_data)
            
            # Save checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "reel_plan": reel_plan,
                "total_duration_seconds": reel_plan.get("total_duration", 0),
                "clips_selected": len(reel_plan.get("clips", [])),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )
            
            # Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "REEL_ASSEMBLED"
            metadata["stage_timestamps"]["REEL_ASSEMBLED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)
            
            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Assembled {len(reel_plan.get('clips', []))} clips into 15s reel",
                data={
                    "clip_count": len(reel_plan.get("clips", [])),
                    "total_duration": reel_plan.get("total_duration", 0),
                },
            )
        
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 4 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Reel assembly failed: {str(e)}",
            )
    
    def _assemble_reel_with_llm(self, scene_data):
        """Use LLM to create optimal 15-second reel sequence."""
        
        prompt = f"""You are a professional social media video editor.

Create a 15-second Instagram Reel from these scored scenes.

Available scenes (sorted by quality):
{json.dumps(scene_data, indent=2)}

Requirements:
- Total duration ≤15 seconds
- Fast-paced, engaging
- Start with strongest hook (first 2 seconds should be high-energy)
- Keep individual clips between 1.5 and 3 seconds
- Avoid repetitive/similar scenes
- Alternate between close-ups and wide shots
- End with the most cinematic shot
- Prefer scenes with high scores
- Include variety (landscape, action, emotion)

Return ONLY valid JSON (no markdown):
{{
  "total_duration": 14.8,
  "reasoning": "Brief explanation of editorial choices",
  "clips": [
    {{"scene_id": "file_001_scene_001", "start_ms": 1000, "end_ms": 3500, "clip_duration": 2.5}},
    {{"scene_id": "file_001_scene_005", "start_ms": 4000, "end_ms": 6200, "clip_duration": 2.2}},
    ...
  ]
}}"""
        
        # Call LLM with text-only prompt (no images needed)
        text_input = self.processor(
            text=prompt,
            padding=True,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            output_ids = self.model.generate(
                **text_input,
                max_new_tokens=512,
                temperature=0.8,
            )
        
        response_text = self.processor.batch_decode(
            output_ids,
            skip_special_tokens=True
        )[0]
        
        # Parse JSON
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                reel_plan = json.loads(json_match.group())
            else:
                logger.error("No JSON found in LLM response")
                reel_plan = self._default_reel_plan(scene_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse reel plan JSON")
            reel_plan = self._default_reel_plan(scene_data)
        
        return reel_plan
    
    @staticmethod
    def _default_reel_plan(scene_data):
        """Default reel plan if LLM fails (use top scenes)."""
        clips = []
        total_duration = 0
        
        # Use top scenes in order, limiting each to 3 seconds
        for scene in scene_data[:8]:
            clip_duration = min(scene["duration"], 3.0)
            total_duration += clip_duration
            
            if total_duration > 15:
                # Trim last clip to fit in 15 seconds
                clip_duration = 15 - (total_duration - clip_duration)
                total_duration = 15
            
            clips.append({
                "scene_id": scene["scene_id"],
                "start_ms": int(scene["start_time_ms"]),
                "end_ms": int(scene["start_time_ms"] + clip_duration * 1000),
                "clip_duration": clip_duration,
            })
            
            if total_duration >= 15:
                break
        
        return {
            "total_duration": total_duration,
            "reasoning": "Default reel plan using top-scored scenes",
            "clips": clips,
        }
    
    def can_resume(self, file_id):
        """Assembly is deterministic, no resume needed."""
        return self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name)
    
    def get_progress(self, file_id):
        """Get progress."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            checkpoint = self.checkpoint_manager.load_file_checkpoint(
                file_id, self.stage_name
            )
            clips = checkpoint.get("reel_plan", {}).get("clips", [])
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=1,
                completed_items=1,
            )
        return None
```

#### 4.2 Checkpoint Format

```json
{
  "stage": "stage4_reel_assembly",
  "file_id": "file_001",
  "reel_plan": {
    "total_duration": 14.8,
    "reasoning": "Started with sunset shot (high emotion), alternated landscape and action",
    "clips": [
      {
        "scene_id": "file_001_scene_021",
        "start_ms": 12400,
        "end_ms": 15000,
        "clip_duration": 2.6
      },
      {
        "scene_id": "file_001_scene_009",
        "start_ms": 5000,
        "end_ms": 7800,
        "clip_duration": 2.8
      },
      ...
    ]
  },
  "total_duration_seconds": 14.8,
  "clips_selected": 5,
  "timestamp": "2024-08-02T12:05:00Z"
}
```

---

## Stage 5: Encoding (FFmpeg)

### Implementation

#### 5.1 Encoding Stage
**File**: `src/stages/stage5_encoding.py`

```python
class Stage5Encoding(Stage):
    """Encode reel into vertical MP4 (1080×1920)."""
    
    def run(self, file_id, source_video, reel_plan_checkpoint, resume_from=None):
        """Encode final 15-second vertical reel."""
        self._log_stage_start(file_id)
        
        try:
            source_video = Path(source_video)
            reel_plan = reel_plan_checkpoint.get("reel_plan", {})
            clips = reel_plan.get("clips", [])
            
            if not clips:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No clips in reel plan",
                )
            
            # 1. Extract all clips
            extracted_clips = []
            for idx, clip in enumerate(clips):
                output_path = Path("data/working/reel_clips") / f"clip_{idx:02d}.mp4"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                success = self._extract_clip(
                    source_video,
                    output_path,
                    clip["start_ms"] / 1000.0,
                    clip["end_ms"] / 1000.0
                )
                
                if success:
                    extracted_clips.append(str(output_path))
                else:
                    logger.warning(f"Failed to extract clip {idx}")
            
            if not extracted_clips:
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="No clips extracted",
                )
            
            # 2. Create concat file for FFmpeg
            concat_file = Path("data/working") / f"{file_id}_concat.txt"
            with open(concat_file, "w") as f:
                for clip_path in extracted_clips:
                    f.write(f"file '{clip_path}'\n")
            
            # 3. Concatenate and encode to vertical format
            output_reel = Path("data/output") / f"{file_id}_reel.mp4"
            output_reel.parent.mkdir(parents=True, exist_ok=True)
            
            success = self._concatenate_and_encode(concat_file, output_reel)
            
            if not success or not output_reel.exists():
                return StageResult(
                    success=False,
                    stage_name=self.stage_name,
                    file_id=file_id,
                    message="Encoding failed",
                )
            
            # 4. Verify duration
            duration = self._get_video_duration(output_reel)
            logger.info(f"Final reel duration: {duration:.2f} seconds")
            
            # 5. Save checkpoint
            checkpoint_data = {
                "stage": self.stage_name,
                "file_id": file_id,
                "output_path": str(output_reel),
                "final_duration_seconds": duration,
                "file_size_mb": output_reel.stat().st_size / (1024**2),
                "clips_concatenated": len(extracted_clips),
                "status": "ENCODED",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            self.checkpoint_manager.save_file_checkpoint(
                file_id,
                self.stage_name,
                checkpoint_data,
            )
            
            # 6. Update metadata
            metadata = self.checkpoint_manager.load_file_metadata(file_id)
            metadata["state"] = "COMPLETED"
            metadata["output_path"] = str(output_reel)
            metadata["stage_timestamps"]["COMPLETED"] = (
                datetime.utcnow().isoformat() + "Z"
            )
            self.checkpoint_manager.save_file_metadata(file_id, metadata)
            
            self._log_stage_complete(file_id)
            return StageResult(
                success=True,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Encoded 15s reel: {output_reel.name}",
                data={
                    "output_path": str(output_reel),
                    "duration": duration,
                    "file_size_mb": output_reel.stat().st_size / (1024**2),
                },
            )
        
        except Exception as e:
            logger.exception(f"[{file_id}] Stage 5 failed: {str(e)}")
            return StageResult(
                success=False,
                stage_name=self.stage_name,
                file_id=file_id,
                message=f"Encoding failed: {str(e)}",
            )
    
    @staticmethod
    def _extract_clip(source_video, output_path, start_seconds, end_seconds):
        """Extract clip segment from video."""
        cmd = [
            "ffmpeg",
            "-i", str(source_video),
            "-ss", str(start_seconds),
            "-to", str(end_seconds),
            "-c:v", "libx264",
            "-preset", "ultrafast",  # Fast for intermediate clips
            "-crf", "28",
            "-c:a", "aac",
            str(output_path),
            "-y",
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0
    
    @staticmethod
    def _concatenate_and_encode(concat_file, output_path):
        """Concatenate clips and encode to vertical format."""
        # Encode to 1080×1920 vertical reel (Instagram format)
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path),
            "-y",
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=1200)
        return result.returncode == 0
    
    @staticmethod
    def _get_video_duration(video_path):
        """Get video duration in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def can_resume(self, file_id):
        """Check if encoding is complete."""
        if not self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return False
        
        checkpoint = self.checkpoint_manager.load_file_checkpoint(
            file_id, self.stage_name
        )
        return checkpoint.get("status") == "ENCODED"
    
    def get_progress(self, file_id):
        """Get progress."""
        if self.checkpoint_manager.checkpoint_exists(file_id, self.stage_name):
            return ProgressInfo(
                stage_name=self.stage_name,
                file_id=file_id,
                total_items=1,
                completed_items=1,
            )
        return None
```

---

## Updated Pipeline Summary

```python
class UpdatedPipeline:
    """New 5-stage pipeline for AI-driven reel generation."""
    
    def process_file(self, file_id, input_video, resume=False):
        # Stage 1: Discovery
        result1 = self.stage1.run(file_id, input_video)
        
        # Stage 2: Scene Detection (PySceneDetect)
        result2 = self.stage2.run(file_id, input_video)
        
        # Stage 3: Vision Analysis (Qwen2.5-VL as Editor)
        result3 = self.stage3.run(file_id, result2.data)
        
        # Stage 4: Reel Assembly (LLM creates 15s sequence)
        result4 = self.stage4.run(file_id, result3.data)
        
        # Stage 5: Encoding (FFmpeg to vertical MP4)
        result5 = self.stage5.run(file_id, input_video, result4.data)
        
        return result5
```

---

## Testing Strategy

### New Tests Needed
```
tests/integration/test_stage2_scene_detection.py
  - Scene detection accuracy
  - Key frame extraction
  - Checkpoint saving

tests/integration/test_stage3_vision_editor.py
  - Scene scoring (beauty, action, etc.)
  - JSON parsing from LLM
  - Overall score calculation
  - Resume capability

tests/integration/test_stage4_reel_assembly.py
  - Reel plan generation
  - Duration verification (≤15s)
  - Clip ordering
  - LLM prompt execution

tests/integration/test_stage5_encoding.py
  - Clip extraction
  - Concatenation
  - Vertical format encoding (1080×1920)
  - Final duration verification

tests/integration/test_end_to_end_reel.py
  - Full pipeline: input video → output reel
  - Resume across all stages
  - Output quality verification
```

---

## Updated Requirements

Add to `requirements.txt`:
```
scenedetect==0.6.1
transformers>=4.36.0
torch>=2.1.0
```

---

## Key Differences from Original Plan

| Aspect | Old | New |
|--------|-----|-----|
| **Stage 2** | Frame extraction every 2s | Scene detection with PySceneDetect |
| **Stage 3** | Embeddings for every frame | LLM scores scenes as editor |
| **Stage 4** | Heuristic highlight detection | **LLM creates 15s reel sequence** |
| **Output** | 3 clips (open-ended) | **1 x 15-second reel** |
| **Prompt** | Generic image analysis | **Professional editor persona** |
| **Determinism** | Probabilistic | **Reproducible (15s goal is clear)** |

---

## Implementation Priority

### Week 1
1. **Stage 2**: Scene Detection with PySceneDetect
   - Detect scene boundaries
   - Extract key frames
   - Save metadata

2. **Stage 3**: Vision Editor (Qwen2.5-VL)
   - Load key frames
   - Score with editor prompts
   - Parse JSON responses

### Week 2
3. **Stage 4**: Reel Assembly
   - Prompt LLM to create 15s sequence
   - Verify duration
   - Handle LLM fallbacks

4. **Stage 5**: Encoding
   - Extract clips from source
   - Concatenate
   - Encode to 1080×1920
   - Verify output

### Week 3
5. **Testing & Optimization**
   - End-to-end tests
   - Real Insta360 videos
   - Performance tuning

---

**This approach is significantly cleaner, more deterministic, and production-ready!** 🎬
