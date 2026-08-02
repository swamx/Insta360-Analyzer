# Quick Start Guide - Phase 3 Complete

## Current Status
✅ **Phase 3 Complete**: Insta360 SDK integration with 360° to single-perspective conversion  
✅ **Pipeline**: 6 stages (0.5 + 1-5) fully integrated  
✅ **Testing**: End-to-end pipeline verified with real Insta360 video  

---

## Basic Usage

### Process a Video
```bash
cd C:\Users\swamx\OneDrive\Pictures\Insta360-Analyzer
python src/main.py --input "path/to/video.insv" --max-duration=0
```

### Options
```bash
--input FILE              Input video file (.insv, .insp, .lrv)
--max-duration SECONDS    Reel duration (default: 15.0, use 0 for unlimited)
--resume                  Resume from last checkpoint
--verbose                 Enable verbose logging
--health-check            Verify system setup
--status FILE_ID          Check processing status
--list-files              List all processed files
```

### Examples
```bash
# Process full-length video (unlimited duration)
python src/main.py --input "video.insv" --max-duration=0

# 15-second reel (Instagram Reels standard)
python src/main.py --input "video.insv" --max-duration=15

# Resume interrupted processing
python src/main.py --input "video.insv" --resume

# Check system setup
python src/main.py --health-check
```

---

## Pipeline Stages

### Stage 0.5: Insta360 Conversion
- **Input**: .insv, .insp, .lrv files (360° or single-view)
- **Detection**: Analyzes format and projection type
- **Action**: Converts 360° to single-perspective if needed
- **Output**: Stabilized single-view video

### Stage 1: Discovery
- **Action**: Catalogs input video properties
- **Output**: File metadata and format info

### Stage 2: Scene Detection
- **Action**: Detects scene boundaries (fallback if PySceneDetect unavailable)
- **Output**: Scene timestamps and keyframes

### Stage 3: Vision Analysis
- **Action**: Scores scenes (mock scoring if Qwen unavailable)
- **Output**: Scene quality scores (1-10 scale)

### Stage 4: Reel Assembly
- **Action**: Selects best scenes for reel (heuristic if LLM unavailable)
- **Output**: Assembled clip list and timeline

### Stage 5: Encoding
- **Action**: Encodes clips and concatenates into vertical format
- **Output**: Final reel (1080×1920, MP4)

---

## Output Files

### Generated Output
```
data/output/
└── file_{filename}_{timestamp}_reel.mp4
```

### Checkpoints (Resume Support)
```
data/working/checkpoints/
└── file_{filename}_{timestamp}/
    ├── metadata.json
    ├── stage0_insta360_conversion/
    ├── stage1_discovery/
    ├── stage2_scene_detection/
    ├── stage3_vision_editor/
    ├── stage4_reel_assembly/
    └── stage5_encoding/
```

### Working Files
```
data/working/
├── scenes/           - Extracted keyframes
├── clips/           - Temporary video clips
└── stage0_insta360_conversion/  - Converted videos
```

---

## Optimization: Enable Real Models

### Install Scene Detection
```bash
pip install scenedetect[opencv]
```
**Benefit**: Precise scene boundary detection instead of duration-based

### Install Vision Model
```bash
pip install torch transformers accelerate
```
**Benefit**: Professional video editor judgment instead of mock scoring

### After Installation
Simply run the pipeline again - it will automatically detect and use real models:
```bash
python src/main.py --input "video.insv" --max-duration=0 --verbose
```

---

## Architecture Overview

```
Input Video (.insv)
    ↓
Stage 0.5: Insta360 Detection & Conversion
    ├─ Is Insta360 format? Check extension
    ├─ Is 360° projection? Check aspect ratio (2:1 = 360°)
    ├─ Convert if needed: FFmpeg v360 filter
    └─ Stabilize: vidstab filters
    ↓
Stage 1: Discovery
    └─ Catalog file properties
    ↓
Stage 2: Scene Detection
    └─ Find scene boundaries (real or fallback)
    ↓
Stage 3: Vision Analysis
    └─ Score scenes (real model or mock)
    ↓
Stage 4: Reel Assembly
    └─ Select best scenes (LLM or heuristic)
    ↓
Stage 5: Encoding
    └─ Create vertical reel (1080×1920)
    ↓
Output: Instagram Reel (MP4)
```

---

## Performance Tips

### For Large Videos (>500MB)
- Use `--max-duration=15` for faster processing
- Ensure adequate disk space for temporary clips
- FFmpeg timeout is set to 1200s (20 minutes)

### For Batch Processing
- Process videos sequentially to avoid memory conflicts
- Monitor GPU usage (especially if using real Qwen model)
- Clean up old checkpoints: `rm -rf data/working/checkpoints/*`

### For Production
- Run with `--verbose` initially to catch issues
- Monitor `logs/` directory for errors
- Use `--health-check` to verify setup
- Implement external logging/monitoring

---

## Troubleshooting

### Error: "PySceneDetect not available"
→ Install: `pip install scenedetect[opencv]`

### Error: "PyTorch/transformers not available"
→ Install: `pip install torch transformers accelerate`

### Error: "FFmpeg timeout"
→ Increase timeout in Stage 5 (currently 1200s)
→ Check video file integrity
→ Ensure sufficient disk space

### Error: "No scenes detected"
→ Verify video duration > 5 seconds
→ Check video codec support (H.264, HEVC)
→ Try with explicit `--max-duration=15`

### Hanging Process
→ Check with: `python src/main.py --status FILE_ID`
→ Resume if stuck: `python src/main.py --input "file.insv" --resume`

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/main.py` | CLI entry point |
| `src/pipeline.py` | Stage orchestration |
| `src/stages/stage0_*.py` | Insta360 conversion |
| `src/stages/stage1_*.py` | Video discovery |
| `src/stages/stage2_*.py` | Scene detection |
| `src/stages/stage3_*.py` | Vision analysis |
| `src/stages/stage4_*.py` | Reel assembly |
| `src/stages/stage5_*.py` | Video encoding |
| `src/insta360/detector.py` | Format detection |
| `src/insta360/converter.py` | 360° conversion |
| `src/insta360/stabilizer.py` | Stabilization |

---

## Documentation

- **PHASE3_INSTA360_INTEGRATION.md** - Architecture design
- **PHASE3_IMPLEMENTATION_SUMMARY.md** - Detailed implementation report
- **PHASE2_SUMMARY.md** - Phase 2 phase real model integration
- **README.md** - Project overview

---

## Next Phase (Future)

### Phase 4: Advanced Features
- [ ] AI perspective detection (auto-select best angle)
- [ ] Multi-perspective output (generate multiple reels)
- [ ] Panoramic mode (360° sweep)
- [ ] Gimbal effect simulation
- [ ] Real-time processing
- [ ] Web UI for batch operations
- [ ] Cloud deployment (AWS/Google Cloud)
- [ ] Performance optimization (model quantization)

---

## Contact & Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run `python src/main.py --health-check`
3. Review error messages in output
4. Check GitHub issues: https://github.com/swamx/Insta360-Analyzer

---

**Last Updated**: 2026-08-02  
**Version**: Phase 3.0  
**Status**: Production-Ready

