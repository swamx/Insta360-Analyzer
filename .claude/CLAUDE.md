# Insta360-Analyzer: Project Instructions

## Project Overview
Local-first Insta360 video analyzer with fault-tolerant checkpoint/resume capability. Generates Instagram reels using Qwen3-VL-2B (4-bit).

## Architecture & Standards
- See `ARCHITECTURE.md` for pipeline design, checkpoint strategy, and recovery mechanism
- See `GOAL.md` for success criteria and project scope
- All checkpoint operations must be atomic (temp file + rename)
- All stages must implement the `Stage` base class interface
- Frame-level granularity for resumption in batch processing

## Checkpoint/Recovery First
- **Never re-process completed work** - preserve all intermediate results
- **Frame-level tracking** - know exactly which frame/clip failed
- **Atomic writes everywhere** - no partial/corrupted checkpoints
- **Resume from state** - scan checkpoints on startup, determine recovery point

## Code Standards

### Error Handling
- Custom exception classes in `src/utils/errors.py`
- Distinguish RECOVERABLE vs NON_RECOVERABLE errors
- Log full traceback with file_id + stage for debugging
- Exit gracefully on recoverable errors (exit code 1)

### Stage Implementation
All stages in `src/stages/` must:
1. Inherit from `Stage` base class
2. Implement `run(file_id, resume_from=None)`
3. Implement `can_resume(file_id)` 
4. Implement `get_progress(file_id)`
5. Save checkpoint after each logical step
6. Support resume from any checkpoint point

### Logging
- Use `src/utils/logger.py` for structured logging
- Log levels: DEBUG (frame-level), INFO (stage-level), WARNING (errors), ERROR (failures)
- Include context: file_id, stage_name, current_frame/batch
- All errors go to `logs/errors.log` with timestamp

### Checkpoint Data
- JSON for metadata (human-readable, inspectable)
- HDF5/Binary for embeddings (efficient I/O)
- Atomic operations: temp file → rename pattern
- Version checkpoints to handle format evolution

## Development Workflow
1. Write stage logic in `src/stages/`
2. Implement checkpoint save/load in stage
3. Test resume capability (simulate failure, restart, verify no duplication)
4. Update `src/pipeline.py` to orchestrate
5. Add CLI command to `src/cli/commands.py`

## Phase 0 (Current) Deliverables
- [ ] Stage 1: Discovery + checkpoint
- [ ] Stage 2: Frame extraction + checkpoint
- [ ] Stage 3: Vision analysis + frame-level resume
- [ ] Stage 4: Highlight detection + checkpoint
- [ ] Stage 5: Clip encoding + checkpoint
- [ ] Checkpoint manager with atomic writes
- [ ] Recovery manager for startup restoration
- [ ] CLI: `python main.py --input video.mp4 --resume`
- [ ] Full recovery test (fail mid-stage, resume, verify success)

## Testing
- All checkpoint operations tested (atomicity, corruption recovery)
- Resume capability tested after each stage
- No re-processing verified on resume
- Integration test: end-to-end on 1-min test video

## Important Constraints
- Local processing only (no cloud APIs)
- 4-bit quantization for Qwen3-VL-2B (~1.8GB VRAM)
- Support Windows paths and POSIX paths equally
- Checkpoint format versioning for forward compatibility

## File Organization
- Source code: `src/` (never edit for docs/configs)
- Configs: `config/` (YAML format)
- Tests: `tests/` (mirror `src/` structure)
- Docs: `ARCHITECTURE.md`, `GOAL.md`, and `docs/` subdirs
- Data: `data/` (input, working, output, models)

## Debugging & Recovery
If something breaks:
1. Check `logs/errors.log` for full traceback
2. Inspect checkpoint state: `data/working/checkpoints/{file_id}/`
3. Use CLI to query state: `python main.py --status [file_id]`
4. Resume with `--resume` flag (auto-finds recovery point)

## When in Doubt
Refer to ARCHITECTURE.md section 2 (Checkpoint Strategy) and section 6 (Critical Implementation Patterns).
