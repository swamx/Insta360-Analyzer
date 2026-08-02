"""Scene analytics for detecting humans, scenery, and composition quality."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import tempfile
from dataclasses import dataclass, asdict

from src.utils.logger import get_logger

logger = get_logger("analytics.scene_analyzer")


@dataclass
class DetectionResult:
    """Result of object detection in a frame."""
    has_humans: bool
    human_count: int
    human_confidence: float
    scenery_quality: float  # 1-10 scale
    composition_score: float  # 1-10 scale
    brightness: float  # 0-255
    contrast: float  # 0-100
    motion_level: float  # 0-100
    dominant_colors: List[str]
    analysis_metadata: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


class SceneAnalyzer:
    """Analyze video frames for content and quality metrics."""

    def __init__(self):
        """Initialize scene analyzer."""
        self.model_available = self._check_model_availability()

    def _check_model_availability(self) -> bool:
        """Check if detection models are available."""
        try:
            import cv2
            import numpy as np
            return True
        except ImportError:
            logger.warning("OpenCV not available, using fallback analysis")
            return False

    def analyze_frame(self, frame_path: Path) -> Optional[DetectionResult]:
        """
        Analyze a single frame for humans, scenery, and composition.

        Args:
            frame_path: Path to keyframe image

        Returns:
            DetectionResult with analysis data
        """
        try:
            if not frame_path.exists():
                logger.warning(f"Frame not found: {frame_path}")
                return None

            if self.model_available:
                return self._analyze_with_cv2(frame_path)
            else:
                return self._analyze_fallback(frame_path)

        except Exception as e:
            logger.error(f"Frame analysis failed: {str(e)}")
            return None

    def _analyze_with_cv2(self, frame_path: Path) -> DetectionResult:
        """Analyze frame using OpenCV and pretrained cascades."""
        import cv2
        import numpy as np

        img = cv2.imread(str(frame_path))
        if img is None:
            return self._create_empty_result()

        height, width = img.shape[:2]

        # Detect faces (proxy for humans)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        faces = face_cascade.detectMultiScale(img, 1.3, 5)
        has_humans = len(faces) > 0
        human_count = len(faces)
        human_confidence = min(1.0, len(faces) * 0.3)  # Confidence increases with face count

        # Analyze image quality
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()  # Higher = sharper image
        sharpness_score = min(10.0, sharpness / 20.0)  # Normalize to 1-10

        brightness = np.mean(gray)
        brightness_normalized = brightness / 255.0

        # Contrast calculation
        contrast = gray.std()
        contrast_normalized = min(100.0, contrast * 2)

        # Motion detection (frame-to-frame difference estimate)
        # Using Laplacian energy as proxy
        motion_level = min(100.0, sharpness / 30.0)

        # Scenery quality based on:
        # - Image sharpness (sharper = better)
        # - Contrast (more contrast = more interesting)
        # - Not too many faces (crowd scenes lower scenery score)
        scenery_score = (sharpness_score * 0.5 + (contrast / 10.0) * 0.3)
        if has_humans:
            scenery_score *= (1.0 - human_confidence * 0.2)  # Slight penalty for crowded scenes
        scenery_score = min(10.0, scenery_score)

        # Composition score based on:
        # - Presence of humans (more engaging)
        # - Image clarity
        # - Moderate brightness
        composition_score = sharpness_score * 0.6
        if has_humans:
            composition_score += 2.0  # Bonus for human subjects
        if 50 < brightness < 200:
            composition_score += 1.0  # Bonus for good exposure
        composition_score = min(10.0, composition_score)

        # Extract dominant colors
        dominant_colors = self._extract_dominant_colors(img, k=3)

        result = DetectionResult(
            has_humans=has_humans,
            human_count=human_count,
            human_confidence=float(human_confidence),
            scenery_quality=float(scenery_score),
            composition_score=float(composition_score),
            brightness=float(brightness),
            contrast=float(contrast),
            motion_level=float(motion_level),
            dominant_colors=dominant_colors,
            analysis_metadata={
                "sharpness_score": float(sharpness_score),
                "image_size": f"{width}x{height}",
                "face_count": int(human_count),
            }
        )

        logger.info(
            f"Frame analysis: humans={has_humans} ({human_count}), "
            f"scenery={scenery_score:.1f}, composition={composition_score:.1f}"
        )

        return result

    def _analyze_fallback(self, frame_path: Path) -> DetectionResult:
        """Fallback analysis using file statistics."""
        try:
            file_size = frame_path.stat().st_size
            # Larger files suggest more complex scenes (proxy for quality)
            quality_score = min(10.0, (file_size / 100000) * 2)

            return DetectionResult(
                has_humans=False,
                human_count=0,
                human_confidence=0.0,
                scenery_quality=quality_score,
                composition_score=quality_score * 0.8,
                brightness=128.0,
                contrast=50.0,
                motion_level=50.0,
                dominant_colors=["unknown"],
                analysis_metadata={
                    "method": "fallback",
                    "file_size": file_size,
                }
            )
        except Exception as e:
            logger.warning(f"Fallback analysis failed: {str(e)}")
            return self._create_empty_result()

    @staticmethod
    def _extract_dominant_colors(img, k: int = 3) -> List[str]:
        """Extract k most dominant colors from image."""
        try:
            import cv2
            import numpy as np

            # Reshape image to list of pixels
            pixels = img.reshape((-1, 3))
            pixels = np.float32(pixels)

            # K-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, _, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Convert centers to hex colors
            centers = np.uint8(centers)
            colors = []
            for center in centers:
                b, g, r = center
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                colors.append(hex_color)

            return colors
        except Exception:
            return ["#808080"] * k

    @staticmethod
    def _create_empty_result() -> DetectionResult:
        """Create empty result for error cases."""
        return DetectionResult(
            has_humans=False,
            human_count=0,
            human_confidence=0.0,
            scenery_quality=5.0,
            composition_score=5.0,
            brightness=128.0,
            contrast=50.0,
            motion_level=50.0,
            dominant_colors=["#808080"],
            analysis_metadata={"error": "analysis_failed"}
        )

    def analyze_multiple_frames(self, frame_paths: List[Path]) -> Dict[str, DetectionResult]:
        """
        Analyze multiple frames efficiently.

        Args:
            frame_paths: List of keyframe paths

        Returns:
            Dictionary mapping frame path to DetectionResult
        """
        results = {}
        for frame_path in frame_paths:
            result = self.analyze_frame(frame_path)
            if result:
                results[str(frame_path)] = result

        logger.info(f"Analyzed {len(results)}/{len(frame_paths)} frames")
        return results
