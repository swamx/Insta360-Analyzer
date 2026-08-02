# Setup Guide: Insta360-Analyzer

## Quick Setup

### 1. Prerequisites

```bash
# Check system requirements
python main.py --health-check
```

This verifies:
- ✅ Python 3.10+
- ✅ CUDA/GPU support
- ✅ FFmpeg installation
- ✅ PyTorch setup

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Install FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH after installation
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

### 4. Detect Insta360 Stitching Tools

```bash
# Check what tools are available on your system
python scripts/detect_insta360_tools.py
```

This will show you:
- ✅ Detected tools (if any)
- ⚠️ Missing tools with installation instructions
- ⭐ Recommended tool to use

---

## Insta360 Stitching Tool Installation

The analyzer needs one of these tools to convert `.insv`, `.insp`, or `.lrv` files to standard MP4.

### Option 1: Insta360 Studio (Recommended)

**Best for:** Official, high-quality stitching with full 360 support

**Installation:**

1. Download from: https://www.insta360.com/download/insta360-studio
2. Install to default location:
   - Windows: `C:\Program Files\Insta360\Insta360Studio`
   - Mac: `/Applications/Insta360Studio.app`
3. Run the analyzer:

```bash
python main.py --health-check  # Should detect Studio
python main.py --input video.insv
```

**System Requirements:**
- Windows 7+ or macOS 10.13+
- 2GB free disk space
- Modern multi-core CPU

**How it works:**
- Stitches raw 360 video from Insta360 cameras
- Produces equirectangular MP4 output (full 360 sphere)
- Highest quality, official support

---

### Option 2: Insta360 OneX API

**Best for:** Insta360 ONE X camera owners

**Requirements:**
- Must have Insta360 ONE X camera
- Comes with camera software bundle

**Installation:**
- Install from OneX software bundle
- Default path: `C:\Program Files\Insta360\OneX`

**How it works:**
- Similar to Studio but optimized for OneX format
- Automatic stitching of OneX-specific formats

---

### Option 3: FFmpeg with Insta360 Filter (Advanced)

**Best for:** Developers who want full control

**For Ubuntu/Debian:**

```bash
# Install dependencies
sudo apt-get install ffmpeg libavcodec-dev libavformat-dev libavutil-dev

# Build FFmpeg with insta360 filter (community patch)
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg
# Apply insta360 filter patch (if available from community)
./configure --enable-gpl --enable-libx264 --enable-libx265 --enable-libvpx
make -j4
sudo make install
```

**Note:** Community support for insta360 filter is limited. Recommended for advanced users only.

---

## Verification

After installation, verify everything is working:

```bash
# Check all tools
python scripts/detect_insta360_tools.py

# Run full health check
python main.py --health-check

# Process a test file
python main.py --input test_video.insv --verbose
```

---

## If No Tools Are Detected

If `detect_insta360_tools.py` shows no tools:

**1. Install Insta360 Studio (easiest):**
- Go to: https://www.insta360.com/download/insta360-studio
- Download and install
- Restart the analyzer

**2. Verify installation paths:**
- Windows: Check `C:\Program Files\Insta360\` exists
- Mac: Check `/Applications/Insta360Studio.app` exists

**3. Troubleshoot:**

```bash
# Check if Studio executable exists (Windows)
dir "C:\Program Files\Insta360\"

# Check if Studio executable exists (Mac)
ls -la /Applications/Insta360Studio.app/Contents/MacOS/

# Verify FFmpeg is installed
ffmpeg -version
```

**4. If still no luck:**
- Studio is not compatible with your system
- Install FFmpeg with community Insta360 filter support
- Use a workaround to pre-convert videos on another machine

---

## Fallback: Pre-Convert Videos

If you can't install any stitching tool:

**Option A:** Use Insta360's official app to export to MP4 first
- Open video in Insta360 app
- Export as MP4
- Use the analyzer on the exported file

**Option B:** Use online conversion tools (not recommended for privacy)
- Upload to Insta360 Cloud (privacy concern)
- Download stitched MP4

**Option C:** Use another machine with Insta360 Studio installed
- Stitch on that machine
- Transfer MP4 to analyzer machine

---

## Disk Space Planning

Insta360 format processing requires:

```
Input .insv (1 hour @ 5760×2880):     ~4GB
Stitched equirectangular MP4:          ~1.5-2GB (depends on compression)
Extracted frames (1 per 2s, 720p):     ~450MB
Frame embeddings (HDF5):               ~7MB
Final clips (3 × 30s @ 5Mbps):        ~60MB
────────────────────────────────────
Total per 1-hour video:                ~6GB working space
```

**Recommendation:** 50GB+ free disk space if processing multiple videos

---

## GPU Setup for Qwen3-VL-2B

The vision model runs on GPU. Make sure you have:

```
NVIDIA GPU:     6GB+ VRAM (RTX 3060, 4060, or better)
CUDA:           11.8+ (https://developer.nvidia.com/cuda-11-8-0-download-archive)
cuDNN:          8.x (optional, for performance)
```

Verify GPU is detected:

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name())"
```

If not detected, install CUDA:
1. Download from NVIDIA
2. Install with default settings
3. Verify with command above

---

## Configuration

Optional: Customize analyzer behavior:

**config/default_config.yaml:**
```yaml
frame_extraction:
  interval_seconds: 2      # Extract frame every 2 seconds
  resolution: [720, 720]   # Downscale frames for processing
  quality: 85              # JPEG quality (1-100)

vision_model:
  quantization: "4bit"     # Keep memory usage low
  batch_size: 16           # Adjust based on GPU VRAM
  
clip_detection:
  min_clip_length: 15      # Minimum clip length (seconds)
  max_clip_length: 60      # Maximum clip length (seconds)
  min_score: 0.5           # Minimum highlight score (0-1)
```

---

## Troubleshooting

### "No Insta360 stitching tool available"

**Solution:**
```bash
python scripts/detect_insta360_tools.py
# Follow instructions to install Studio or OneX
```

### "FFmpeg not found"

**Solution:**
```bash
# Check FFmpeg is installed
ffmpeg -version

# If not found, install:
# Windows: choco install ffmpeg
# Mac: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### "CUDA/GPU not detected"

**Solution:**
```bash
# Verify GPU
python -c "import torch; print(torch.cuda.is_available())"

# If False, install CUDA from NVIDIA
# Then reinstall PyTorch:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### "Out of Memory during stitching"

**Solution:**
- Close other applications
- Studio/OneX stitching requires ~2-4GB RAM
- Wait for stitching to complete (can take 30+ minutes for 1-hour videos)

### "Frames look corrupted or wrong"

**Solution:**
- Verify input .insv file is not corrupted
- Try stitching the file in Insta360 Studio directly
- If Studio output looks wrong, the camera file may be corrupt

---

## Next Steps

After setup completes:

1. Run health check: `python main.py --health-check`
2. Test with a small clip: `python main.py --input test_video.insv`
3. Monitor progress: `python main.py --status file_id`
4. Resume if interrupted: `python main.py --input video.insv --resume`

See README.md for usage instructions.
