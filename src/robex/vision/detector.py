"""Visual object and button detection using OpenCV color masking and template matching."""

from dataclasses import dataclass
from typing import List, Tuple, Dict
import logging
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


@dataclass
class DetectionResult:
    """Represents a detected UI element or button on screen."""
    x: int             # Center X coordinate
    y: int             # Center Y coordinate
    width: int
    height: int
    confidence: float
    label: str

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)


# Pre-calibrated HSV color ranges for common Roblox game buttons
COLOR_HSV_RANGES: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {
    "green": [
        (np.array([35, 50, 50]), np.array([85, 255, 255]))
    ],
    "red": [
        (np.array([0, 70, 50]), np.array([10, 255, 255])),
        (np.array([170, 70, 50]), np.array([180, 255, 255]))
    ],
    "blue": [
        (np.array([90, 50, 50]), np.array([130, 255, 255]))
    ],
    "yellow": [
        (np.array([20, 100, 100]), np.array([34, 255, 255]))
    ],
    "orange": [
        (np.array([10, 100, 100]), np.array([20, 255, 255]))
    ]
}


class VisionDetector:
    """Detects buttons, UI elements, and screen markers by color and template matching."""

    def find_buttons_by_color(
        self,
        frame: np.ndarray,
        color_name: str,
        min_area: int = 150,
        max_area: int = 200000
    ) -> List[DetectionResult]:
        """Detects buttons matching a color name ('green', 'red', 'blue', etc.) in the frame."""
        if not HAS_CV2 or frame is None:
            return []

        color_key = color_name.lower()
        if color_key not in COLOR_HSV_RANGES:
            logger.warning("Color '%s' not recognized. Supported: %s", color_key, list(COLOR_HSV_RANGES.keys()))
            return []

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = None

        # Build mask from HSV ranges (some colors like red wrap around 0/180)
        for lower, upper in COLOR_HSV_RANGES[color_key]:
            sub_mask = cv2.inRange(hsv, lower, upper)
            mask = sub_mask if mask is None else cv2.bitwise_or(mask, sub_mask)

        # Smooth mask to remove tiny noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        results: List[DetectionResult] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                center_x = bx + bw // 2
                center_y = by + bh // 2
                confidence = min(1.0, area / (bw * bh + 1e-5))

                results.append(DetectionResult(
                    x=center_x,
                    y=center_y,
                    width=bw,
                    height=bh,
                    confidence=confidence,
                    label=f"{color_key}_button"
                ))

        # Sort largest area first
        results.sort(key=lambda r: r.width * r.height, reverse=True)
        return results

    def find_template(
        self,
        frame: np.ndarray,
        template: np.ndarray,
        confidence_threshold: float = 0.8
    ) -> List[DetectionResult]:
        """Finds instances of a template image within the frame using OpenCV matchTemplate."""
        if not HAS_CV2 or frame is None or template is None:
            return []

        th, tw = template.shape[:2]
        fh, fw = frame.shape[:2]
        if th > fh or tw > fw:
            return []

        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        locs = np.where(res >= confidence_threshold)

        results: List[DetectionResult] = []
        for pt in zip(*locs[::-1]):  # Switch columns and rows to (x, y)
            score = float(res[pt[1], pt[0]])
            center_x = pt[0] + tw // 2
            center_y = pt[1] + th // 2
            results.append(DetectionResult(
                x=center_x,
                y=center_y,
                width=tw,
                height=th,
                confidence=score,
                label="template_match"
            ))

        return results


# Global vision detector instance
detector = VisionDetector()
