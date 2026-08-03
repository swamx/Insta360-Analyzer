# Insta360 Analyzer

Professional-grade AI-powered video analyzer for Insta360 content. Converts 360° videos to publication-ready Instagram reels with intelligent quality assurance.

## Quick Start

```python
from src.executor import ReelExecutor
from pathlib import Path

executor = ReelExecutor(
    video_path=Path("video.insv"),
    data_dir=Path("data"),
    max_duration=0,  # Unlimited
)

results = executor.run()
executor.print_summary()
executor.save_results()
```

## Documentation

- **[Project Guide](docs/README_PROJECT.md)** - Complete system overview
- **[Quick Start](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Flow Architecture](docs/FLOW_ARCHITECTURE_GUIDE.md)** - DAG orchestration & abstract components
- **[ReACT QA Agent](docs/REACT_QA_AGENT_GUIDE.md)** - Quality assurance loop
- **[Feedback System](docs/FEEDBACK_LEARNING_GUIDE.md)** - Continuous improvement
- **[Analytics](docs/ANALYTICS_TRACEABILITY_GUIDE.md)** - Scene detection & vision analysis
- **[Setup Guide](docs/SETUP.md)** - Installation & configuration
- **[Testing](docs/TESTING.md)** - Running tests

## Architecture

### 6-Stage Pipeline
1. **Stage 0.5** - Insta360 360° → single-perspective conversion
2. **Stage 1** - Video discovery (properties, duration)
3. **Stage 2** - Scene detection (boundaries, keyframes)
4. **Stage 3** - Vision analysis (Qwen2.5-VL scoring)
5. **Stage 4** - Reel assembly (scene composition)
6. **Stage 5** - Encoding (1080×1920 vertical format)

### Quality Assurance
- **ReACT Agent** - Reason-Act-Observe loop for iterative improvement
- **Feedback System** - Collect user ratings, learn preferences
- **Persistent Caching** - Resume from checkpoints, crash recovery
- **Execution Traces** - Full transparency of decisions

## Key Features

✅ **Insta360 Support** - Detect & convert 360° videos  
✅ **Professional Analysis** - Real scene detection, vision model scoring  
✅ **Autonomous Quality** - ReACT agent improves iteratively  
✅ **Crash Recovery** - Checkpoint + resume from any stage  
✅ **Learning System** - Continuously improves from feedback  
✅ **Type Safe** - 100% Pydantic validation  
✅ **Production Ready** - Logging, monitoring, error handling  

## Installation

```bash
# Clone and setup
git clone https://github.com/swamx/Insta360-Analyzer.git
cd Insta360-Analyzer

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start analysis
python src/main.py --video path/to/video.insv
```

## Status

🟢 **Production Ready** - All stages implemented, tested, documented

## License

MIT

