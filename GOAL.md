# Insta360-Analyzer Project Goal

## Vision
Build a **local-first video analysis solution** that transforms Insta360 images and videos into Instagram/TikTok-ready reels for a video blog account.

## Core Requirements
1. **Local Processing** - No cloud APIs, run entirely on consumer hardware using Qwen3-VL-2B (4-bit quantized)
2. **Fault Tolerance** - Process can be interrupted at any point and resumed from last checkpoint without re-processing
3. **Interim Storage** - All analysis results are checkpointed to enable investigation and recovery
4. **Backup/Recovery** - Failed processing can replay from last successful step (frame-level granularity)

## Success Criteria

### Phase 0 MVP (Current)
- [ ] Single Insta360 video processes end-to-end through all 5 stages
- [ ] Checkpoint created after each stage
- [ ] Can resume from any failed stage without re-processing prior stages
- [ ] Can resume mid-batch in long-running stages (e.g., frame 543 out of 600)
- [ ] Generates 1-3 quality MP4 clips suitable for Instagram
- [ ] Full checkpoint recovery test passes (simulate crash, resume, verify no duplication)

### Phase 1-4 (Future)
- Multi-file batch processing
- Advanced highlight detection
- Performance optimization (2-5x speedup on consumer GPUs)
- Web UI for monitoring

## Technical Stack
- **Vision Model**: Qwen3-VL-2B (4-bit quantized, ~1.8GB VRAM)
- **Frame Processing**: FFmpeg, OpenCV
- **Storage**: HDF5 (embeddings), JSON (metadata)
- **Python**: 3.10+, PyTorch
- **Hardware Target**: NVIDIA GPU 6GB+ VRAM (RTX 3060/4060)

## Context
- User: Processing personal Insta360 content for video blog
- Timeline: Phase 0 MVP completion target: 2 weeks
- Constraints: Must run locally, cannot use cloud vision APIs
- Media Format: Insta360 native format (5760×2880) requires format conversion
