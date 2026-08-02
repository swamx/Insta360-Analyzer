# Testing Guide

## Overview

Insta360-Analyzer has comprehensive test coverage for:
- ✅ Checkpoint atomic operations (save/load/integrity)
- ✅ Recovery from interrupted processing
- ✅ Frame-level resume capability
- ✅ No re-processing of completed work
- ✅ Vision model inference (mock for testing)

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures
├── unit/
│   ├── test_checkpoint_manager.py      # Checkpoint I/O tests
│   └── test_recovery.py                # Recovery logic tests
└── integration/
    ├── test_stage3_analysis.py         # Stage 3 full workflow
    └── test_recovery_simulation.py     # Failure/recovery scenarios
```

## Quick Start

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run full test suite
python scripts/run_tests.py

# Or use pytest directly
pytest tests/ -v
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_checkpoint_manager.py -v

# Specific test class
pytest tests/integration/test_stage3_analysis.py::TestStage3Checkpoint -v

# Specific test function
pytest tests/integration/test_recovery_simulation.py::TestRecoverySimulation::test_crash_and_resume_mid_batch -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
# Opens coverage report in htmlcov/index.html
```

## Test Categories

### Unit Tests: Checkpoint Manager

**File:** `tests/unit/test_checkpoint_manager.py`

Tests checkpoint save/load operations:
- ✅ Atomic JSON writes (temp file → rename pattern)
- ✅ Corruption detection (invalid JSON)
- ✅ File checkpoint operations (save/load/exists)
- ✅ File metadata tracking
- ✅ Global manifest management
- ✅ State tracking (file state, last complete stage)

**Run:**
```bash
pytest tests/unit/test_checkpoint_manager.py -v
```

### Unit Tests: Recovery Manager

**File:** `tests/unit/test_recovery.py`

Tests recovery point detection:
- ✅ Scan file with no checkpoints
- ✅ Scan file with multiple completed stages
- ✅ Scan all files for recovery
- ✅ Get frame-level resume point
- ✅ Detect if stage can resume
- ✅ Needs processing detection

**Run:**
```bash
pytest tests/unit/test_recovery.py -v
```

### Integration Tests: Stage 3 Analysis

**File:** `tests/integration/test_stage3_analysis.py`

Tests vision analysis stage:
- ✅ Frame analysis (mock embeddings, metadata)
- ✅ Checkpoint saves after each batch
- ✅ Can resume from checkpoint
- ✅ Progress tracking
- ✅ Embedding storage verification
- ✅ Analysis metadata storage
- ✅ Resume without duplication
- ✅ Resume from specific frame
- ✅ Partial run + resume flow
- ✅ Error handling (missing frames, no checkpoint)

**Run:**
```bash
pytest tests/integration/test_stage3_analysis.py -v
```

### Integration Tests: Recovery Simulation

**File:** `tests/integration/test_recovery_simulation.py`

Tests real-world failure scenarios:
- ✅ **Crash mid-batch** - Simulate crash, verify recovery checkpoint, resume without duplication
- ✅ **Multiple interruptions** - Run analysis 3 times with interruptions, verify no duplication
- ✅ **Data preservation** - Verify no data loss during resume
- ✅ **Checkpoint atomicity** - Verify checkpoints are valid JSON and complete

**Run:**
```bash
pytest tests/integration/test_recovery_simulation.py -v
```

## Test Fixtures

### Provided by `conftest.py`

| Fixture | Purpose | Type |
|---------|---------|------|
| `temp_dir` | Temporary directory for each test | Path |
| `checkpoint_dir` | Checkpoint directory | Path |
| `checkpoint_manager` | CheckpointManager instance | Object |
| `data_dir` | Full data directory structure | Path |
| `pipeline` | Pipeline instance | Object |
| `test_frames` | 100 synthetic JPEG frames (256×256) | (Path, list) |
| `test_embeddings` | 100 mock embeddings (1024-dim) | ndarray |
| `test_metadata` | Sample file metadata | dict |

### Usage Example

```python
def test_my_feature(checkpoint_manager, test_frames):
    """Test using fixtures."""
    frames_dir, frames = test_frames  # 100 test frames
    
    # Your test code here
    assert len(frames) == 100
```

## Key Test Scenarios

### 1. Checkpoint Atomicity

**What:** Verify checkpoint writes can't be corrupted mid-write

**How:** 
- Write data to temp file first
- Atomic rename to final location
- Load and verify JSON integrity

**Why:** If process crashes during checkpoint, old checkpoint is preserved

```python
# Example test
def test_atomic_save_json(checkpoint_manager):
    data = {"key": "value"}
    checkpoint_manager.atomic_save_json(path, data)
    # Even if crash happened during write, checkpoint is valid
    loaded = checkpoint_manager.load_json(path)
    assert loaded == data
```

### 2. Resume Without Duplication

**What:** Verify resumed processing doesn't re-process completed work

**How:**
1. Run analysis on 100 frames
2. Checkpoint after each batch
3. Resume from checkpoint
4. Verify exact same embeddings (no duplicates)

**Why:** Critical for long-running jobs that may crash

```python
# Example scenario
def test_resume_no_duplication():
    # First run: analyze frames 0-99
    result1 = stage.run(file_id, frames_dir)
    embeddings1 = load_checkpoint(file_id)["embeddings"]  # 100 items
    
    # Simulate crash and resume
    result2 = stage.run(file_id, frames_dir)  # Resume from last checkpoint
    embeddings2 = load_checkpoint(file_id)["embeddings"]  # Still 100 items
    
    assert embeddings1 == embeddings2  # No duplication!
```

### 3. Frame-Level Granularity

**What:** Can resume from specific frame index

**How:**
- Track `last_completed_frame` in checkpoint
- Resume next time from `last_completed_frame + 1`
- Save checkpoint every N frames

**Why:** If a specific frame fails, can skip it and continue

```python
# Checkpoint tracks progress
{
    "stage_progress": {
        "stage3_analysis": {
            "total_frames": 100,
            "last_completed_frame": 47  # Crashed at frame 48
        }
    }
}

# Resume from frame 48
resume_point = 47 + 1  # = 48
```

### 4. Multiple Interruptions

**What:** Handle multiple crash/resume cycles

**How:**
1. Run, save checkpoint after 20 frames
2. Resume, save checkpoint after 40 frames
3. Resume again, complete all 100 frames
4. Verify final state matches single-run result

**Why:** Real-world jobs get interrupted multiple times

## Test Utilities

### Generate Test Frames

```python
# Fixtures create 100 synthetic JPEG frames automatically
# Each frame is 256×256 with varying patterns
frames_dir, frames = test_frames
assert len(frames) == 100
assert all(f.suffix == ".jpg" for f in frames)
```

### Mock Embeddings

```python
# 1024-dimensional embeddings (matches Qwen3-VL-2B output)
embeddings = np.random.randn(100, 1024).astype(np.float32)
assert embeddings.shape == (100, 1024)
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python scripts/run_tests.py
```

## Troubleshooting

### Tests fail with "module not found"

```bash
# Make sure you're in repo root
cd Insta360-Analyzer

# Install dependencies
pip install -r requirements.txt
```

### Tests timeout

```bash
# Increase timeout (default 60 seconds)
pytest tests/ --timeout=300
```

### Test isolation issues

```bash
# Run tests with no parallel execution
pytest tests/ -n 0

# Or run single test at a time
pytest tests/unit/test_checkpoint_manager.py::TestCheckpointManagerBasics::test_init_creates_directory
```

## Writing New Tests

### Template: Unit Test

```python
def test_my_feature(checkpoint_manager):
    """Clear description of what this tests."""
    file_id = "test_file_001"
    
    # Setup
    checkpoint_manager.save_file_metadata(file_id, {"data": "test"})
    
    # Execute
    metadata = checkpoint_manager.load_file_metadata(file_id)
    
    # Assert
    assert metadata["data"] == "test"
```

### Template: Integration Test

```python
def test_my_integration_scenario(checkpoint_manager, test_frames):
    """Test interaction between components."""
    frames_dir, frames = test_frames
    stage = Stage3Analysis(checkpoint_manager, skip_model_load=True)
    
    file_id = "test_integration_001"
    
    # Setup
    checkpoint_manager.save_file_metadata(file_id, {...})
    
    # Execute
    result = stage.run(file_id, frames_dir)
    
    # Assert
    assert result.success
    # Add specific assertions for your scenario
```

### Best Practices

1. **Use fixtures** - Don't create temp dirs manually
2. **Clear names** - `test_resume_from_checkpoint_no_duplication` > `test_resume`
3. **One assertion per test** - Or closely related assertions
4. **Document intent** - Why are you testing this?
5. **Clean setup/teardown** - Fixtures handle this automatically

## Coverage Goals

Target: **>90% coverage** for critical paths

```bash
pytest tests/ --cov=src --cov-report=term-missing

# Critical paths requiring 100% coverage:
# - src/storage/checkpoint_manager.py (atomic operations)
# - src/recovery.py (recovery logic)
# - src/stages/stage3_analysis.py (checkpoint/resume)
```

## Next Steps

After passing full test suite:
1. Implement Stage 4 (Highlight Detection)
2. Implement Stage 5 (Clip Encoding)
3. Add end-to-end pipeline tests
4. Test with real Insta360 videos
