# Insta360-Analyzer: Architecture & Design

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     VIDEO ANALYZER PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Input Media]                                                   │
│       ↓                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STAGE 1: DISCOVERY & CATALOGING                         │   │
│  │ - Scan input directory (images/videos)                  │   │
│  │ - Generate file metadata (duration, dimensions, etc)    │   │
│  │ - Checkpoint: File catalog + processing state           │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STAGE 2: FRAME EXTRACTION & PREPARATION                │   │
│  │ - Extract frames at regular intervals                   │   │
│  │ - Handle Insta360 format conversion if needed           │   │
│  │ - Normalize images for model input                      │   │
│  │ - Checkpoint: Extracted frames path, frame count        │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STAGE 3: VISION ANALYSIS                               │   │
│  │ - Load Qwen3-VL-2B (4-bit quantized)                    │   │
│  │ - Batch process frames with model                       │   │
│  │ - Extract: embeddings, scene changes, objects detected  │   │
│  │ - Checkpoint: Embeddings, analysis metadata per frame   │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STAGE 4: HIGHLIGHT DETECTION                           │   │
│  │ - Scene boundary detection (frame diff + embeddings)    │   │
│  │ - Interest scoring (unique scenes, action detection)    │   │
│  │ - Clip segmentation (15s - 60s segments)                │   │
│  │ - Checkpoint: Identified clips with timestamps          │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STAGE 5: CLIP EXTRACTION & ENCODING                    │   │
│  │ - Extract video segments to MP4 (H.264)                │   │
│  │ - Apply basic filters if needed                         │   │
│  │ - Checkpoint: Generated clips, encoding status          │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                           │
│  [Output Reels Directory]                                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 2. CHECKPOINT STRATEGY (CRITICAL)

### 2.1 Checkpoint Directory Structure
```
checkpoints/
├── manifest.json              # Global processing state
├── file_manifest.json         # Per-file processing tracking
└── {file_id}/
    ├── metadata.json          # File metadata + state
    ├── stage1_cataloging/
    │   └── catalog.json       # Discovery results
    ├── stage2_frames/
    │   ├── frame_metadata.json
    │   └── extracted_frames/  # Frame images
    ├── stage3_analysis/
    │   ├── embeddings.bin     # Frame embeddings (binary)
    │   └── analysis.json      # Per-frame analysis metadata
    ├── stage4_highlights/
    │   └── clips.json         # Identified clip segments
    └── stage5_encoding/
        ├── encoding_status.json
        └── output/            # Final MP4 clips
```

### 2.2 State Machine (Per File)
```
State Transitions:
DISCOVERED → FRAMES_EXTRACTED → ANALYZED → HIGHLIGHTS_DETECTED → ENCODED → COMPLETED

Recovery Rules:
- At startup: Scan all checkpoints to determine last successful state
- If Stage N fails: Preserve stages 1..N-1, restart N
- If Stage N partially completes: Resume from next unprocessed batch
- Atomic writes: Write to temp file, then atomic rename to prevent corruption
```

### 2.3 Checkpoint Content Details

**manifest.json** (Global state):
```json
{
  "version": "1.0",
  "last_updated": "2024-08-02T10:30:00Z",
  "total_files": 42,
  "completed_files": 15,
  "failed_files": 2,
  "processing_stage": "stage3_analysis",
  "current_file_id": "file_20240801_001",
  "model_version": "qwen3-vl-2b-4bit-v1.0",
  "settings": {
    "frame_interval_seconds": 2,
    "clip_min_length": 15,
    "clip_max_length": 60,
    "batch_size": 16,
    "model_quantization": "4bit"
  }
}
```

**{file_id}/metadata.json**:
```json
{
  "file_id": "file_20240801_001",
  "source_path": "/media/insta360_001.mp4",
  "file_type": "video",
  "duration_seconds": 1234,
  "resolution": "5760x2880",
  "frame_count": 37020,
  "ingest_timestamp": "2024-08-01T15:45:00Z",
  "state": "ANALYZED",
  "stage_timestamps": {
    "DISCOVERED": "2024-08-01T15:46:00Z",
    "FRAMES_EXTRACTED": "2024-08-01T15:48:30Z",
    "ANALYZED": "2024-08-01T16:05:15Z"
  },
  "stage_progress": {
    "stage3_analysis": {
      "total_frames": 600,
      "processed_frames": 600,
      "last_batch": 36,
      "last_frame_idx": 599
    }
  }
}
```

### 2.4 Recovery Mechanism

**Startup Recovery**:
1. Read `manifest.json` to identify last processing stage
2. Scan all `{file_id}/metadata.json` to find incomplete files
3. For incomplete files, check stage completion status:
   - Verify checkpoints exist for previous stages
   - Identify next stage to resume from
   - Skip already-completed stages

**Mid-Stage Recovery**:
For long-running stages (analysis, encoding):
```json
// stage3_analysis/progress.json - Updated every N frames
{
  "batch_number": 12,
  "frames_processed": [0, 1, 2, ..., 191],
  "last_completed_frame": 191,
  "timestamp": "2024-08-02T10:35:20Z"
}
```

**On Failure**:
1. Exception handler catches error, logs with file_id + stage
2. Saves partial results to checkpoint
3. On restart: Detects incomplete stage, resumes from `last_completed_frame + 1`
4. No re-processing of already-completed frames

## 3. FILE STRUCTURE & STORAGE LAYOUT

```
Insta360-Analyzer/
├── README.md
├── GOAL.md
├── ARCHITECTURE.md
├── requirements.txt
├── setup.py
├── .gitignore
│
├── config/
│   ├── default_config.yaml
│   └── hardware_profiles.yaml
│
├── src/
│   ├── __init__.py
│   ├── main.py                       # Entry point with CLI
│   ├── pipeline.py                   # Main orchestrator
│   ├── checkpoint.py                 # Checkpoint I/O operations
│   ├── recovery.py                   # Recovery logic and state restoration
│   │
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── base.py                   # Base Stage interface
│   │   ├── stage1_discovery.py       # Catalog input media
│   │   ├── stage2_extraction.py      # Frame extraction from video
│   │   ├── stage3_analysis.py        # Vision model inference
│   │   ├── stage4_highlights.py      # Clip detection/segmentation
│   │   └── stage5_encoding.py        # Video encoding to MP4
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── vision_model.py           # Qwen3-VL-2B wrapper
│   │   ├── quantization.py           # 4-bit quantization config
│   │   └── embeddings.py             # Embedding utilities
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── frame_processor.py        # Frame handling
│   │   ├── insta360_converter.py     # Insta360 format handling
│   │   └── video_utils.py            # FFmpeg wrapper
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── checkpoint_manager.py     # Read/write checkpoints atomically
│   │   ├── state_tracker.py          # Track per-file state
│   │   └── binary_store.py           # Embeddings storage (numpy/HDF5)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── errors.py                 # Custom exception classes
│   │   └── device_utils.py           # GPU/CPU detection
│   │
│   └── cli/
│       ├── __init__.py
│       ├── commands.py               # CLI commands
│       └── progress.py               # Progress reporting
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── data/
│   ├── input/                        # Raw Insta360 media
│   ├── working/
│   │   └── checkpoints/              # All checkpoint data
│   ├── output/                       # Generated clips
│   └── models/
│       └── qwen3-vl-2b-4bit/        # Downloaded quantized model
│
└── docs/
    ├── CHECKPOINT_RECOVERY.md
    ├── SETUP.md
    └── API.md
```

## 4. KEY TECHNICAL DECISIONS & TRADE-OFFS

| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|
| **Checkpoint Format** | JSON + Binary (HDF5) | JSON for metadata (human-readable), HDF5 for embeddings (efficient I/O) | Slightly more complex management vs flexibility |
| **State Tracking** | Per-file JSON metadata | Easy resumption at any stage without DB | Limited to local filesystem queries |
| **Frame Extraction** | FFmpeg subprocess | Proven, handles many formats natively | Subprocess dependency management |
| **Model Storage** | Local cache with manual download | Full control, reproducible | Manual model version management |
| **Batch Size** | Dynamic (8-16 based on VRAM) | Maximize GPU utilization | More complex memory management code |
| **Clip Detection** | Heuristic + embedding-based | Fast, doesn't require training | May miss subtle scene changes |
| **Recovery Strategy** | Frame-level checkpoints | Resume from exact failure point | Disk space for frame metadata |
| **Atomicity** | Temp file + atomic rename | Prevents corruption on crash | Platform-dependent (works on Windows NTFS) |

## 5. IMPLEMENTATION PHASES

### PHASE 0: MVP (Week 1-2)
**Goal**: Single file pipeline with full checkpoint/resume capability

Core deliverables:
- [ ] Stage 1: Discovery (catalog single file, save metadata checkpoint)
- [ ] Stage 2: Frame extraction (extract frames, save checkpoint with paths)
- [ ] Stage 3: Vision analysis (batch inference on frames with resume capability)
- [ ] Stage 4: Simple highlight detection (scene changes + motion)
- [ ] Stage 5: Basic clip encoding (extract MP4 segments)
- [ ] Checkpoint manager with atomic writes
- [ ] Recovery mechanism (identify last state, resume)
- [ ] Error handling with checkpoint persistence
- [ ] Basic CLI: `python main.py --input video.mp4 --resume`

Testing:
- Test resume after each stage
- Simulate failures and verify recovery
- Verify no re-processing of completed stages

### PHASE 1: Batch Processing & Robustness (Week 3-4)
- Multi-file orchestration
- Queue-based processing (process multiple files in parallel/sequence)
- Enhanced error handling (per-file error isolation)
- Partial batch recovery (resume from failed frame in batch)
- Progress reporting and ETA
- Configuration file support

### PHASE 2: Advanced Analysis (Week 5-6)
- Object detection confidence scoring
- Temporal coherence scoring (clip flow)
- Audio-visual sync detection (if audio)
- Multi-clip generation per video (top-3 best segments)
- Clip ranking/scoring system
- Filter by content type (action, landscape, people-focused)

### PHASE 3: Optimization & Inference Speed (Week 7)
- Model batching optimization (dynamic batch sizes)
- Frame preprocessing caching
- Parallel stage processing
- GPU memory optimization
- Benchmark on target hardware

### PHASE 4: User Experience (Week 8+)
- Web UI (Flask/Streamlit) for monitoring
- Scheduled batch jobs
- Output gallery + metadata export
- Statistics dashboard
- Docker containerization

## 6. CRITICAL IMPLEMENTATION PATTERNS

### 6.1 Checkpoint Manager (Core Component)
```python
class CheckpointManager:
    """Atomic checkpoint operations with rollback safety"""
    
    def save_checkpoint(file_id, stage, data):
        """1. Serialize to temp file
           2. Atomic rename (atomic on NTFS)
           3. Verify integrity
           4. Update manifest
        """
    
    def load_checkpoint(file_id, stage):
        """1. Check if checkpoint exists
           2. Load with integrity check
           3. Return data + last_progress marker
        """
    
    def get_recovery_point(file_id):
        """Determine where to resume from based on checkpoints"""
    
    def mark_stage_complete(file_id, stage):
        """Update manifest atomically"""
```

### 6.2 Recovery Strategy
```python
class RecoveryManager:
    """Restore last known good state"""
    
    def scan_all_checkpoints():
        """For each file:
           1. Check which stages have valid checkpoints
           2. Find last complete stage
           3. Return dict: {file_id: last_complete_stage}
        """
    
    def resume_from_stage(file_id, stage):
        """1. Load checkpoint metadata
           2. Identify last processed item (frame/clip)
           3. Skip already-done work
           4. Resume from next item
        """
```

### 6.3 Stage Interface (Consistency)
```python
class Stage(ABC):
    """All stages implement this interface for consistency"""
    
    @abstractmethod
    def run(self, file_id, resume_from=None) -> StageResult:
        """Execute stage, supporting resumption"""
        pass
    
    @abstractmethod
    def can_resume(self, file_id) -> bool:
        """Check if resumable checkpoint exists"""
        pass
    
    @abstractmethod
    def get_progress(self, file_id) -> ProgressInfo:
        """Return last known progress"""
        pass
```

### 6.4 Checkpoint Atomicity
```python
def atomic_save(path, data):
    import tempfile, shutil, os
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(
        dir=os.path.dirname(path), 
        delete=False
    ) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name
    
    # Atomic rename (works on Windows NTFS)
    os.replace(tmp_path, path)
```

## 7. ERROR HANDLING & RETRY LOGIC

### 7.1 Error Classification
```python
class ProcessingError(Exception):
    """Categorize errors for recovery decisions"""
    
    RECOVERABLE:  # Resume from checkpoint
        - OutOfMemoryError
        - GPUTimeout
        - DiskSpaceError
        - FrameLoadError (skip frame, continue)
    
    NON_RECOVERABLE:  # Needs manual intervention
        - CorruptedCheckpoint
        - InvalidInputFile
        - ModelLoadError
```

### 7.2 Retry Strategy
```
For RECOVERABLE errors:
  1. Log full traceback to error.log with timestamp + file_id
  2. Flush current checkpoint with error status
  3. Exit gracefully with exit code 1
  4. User can retry with --resume flag (auto-resumes from last checkpoint)

For NON_RECOVERABLE errors:
  1. Log detailed error
  2. Mark file status as FAILED
  3. Move to next file in queue
```

## 8. MODEL OPTIMIZATION FOR LOCAL HARDWARE

### 8.1 Qwen3-VL-2B Configuration
```yaml
model:
  name: "Qwen3-VL-2B"
  quantization: "4-bit"
  device_map: "auto"
  
inference:
  batch_size: 16
  precision: "float16"
  use_cache: True
  max_new_tokens: 256

frame_preprocessing:
  resolution: [384, 384]
  cache_processed: True
```

### 8.2 Memory Optimization
- Incremental loading of embeddings (HDF5 supports this)
- Batch processing to maximize GPU throughput
- Device memory monitoring and dynamic batch sizing
- Frame preprocessing caching to avoid re-computation

## 9. STORAGE STRATEGY & DISK USAGE

### 9.1 Disk Space Estimation

For 1-hour Insta360 video (5760x2880, 30fps):
```
Extracted frames (1 every 2s, 1800 frames @ 720p JPEG):     ~450MB
Frame embeddings (1024-dim float32):                        ~7MB
Analysis metadata (JSON):                                   ~1MB
Final MP4 clips (3 clips x 30s @ 5Mbps):                   ~60MB
─────────────────────────────────────────
TOTAL PER VIDEO:                                            ~520MB
```

### 9.2 Storage Cleanup Strategy
```
Auto-cleanup (can recover if needed):
  - Extracted frames deleted after analysis complete
  - Embeddings kept (small, useful for re-analysis)
  - Metadata checkpoints always kept
  
Manual cleanup:
  - python main.py --cleanup-stage 2 [file_id]
  - python main.py --cleanup-all [file_id]
```

## 10. SYSTEM REQUIREMENTS

### Minimum Hardware
```
GPU: NVIDIA GPU with 6GB+ VRAM (RTX 3060, 4060, etc)
CPU: Modern multi-core (8+ cores recommended)
RAM: 16GB system RAM
Storage: 500MB+ free per video processed
```

### Software Requirements
```
Python 3.10+
FFmpeg 4.4+
CUDA 11.8+ (for GPU inference)
PyTorch with CUDA support
```

## 11. TESTING STRATEGY

### Unit Tests
- Checkpoint save/load/atomicity
- Recovery point detection
- State machine transitions
- Frame batch calculations

### Integration Tests
- End-to-end pipeline on 1-min test video
- Resume after each stage
- Simulate mid-batch failures and recovery
- Verify no re-processing on resume

### Recovery Tests
- Checkpoint corruption recovery
- Mid-stage resume
- Frame-level resume in batch processing
- Multiple sequential failures and restarts
