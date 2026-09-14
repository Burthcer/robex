"""Visual object and button detection using OpenCV color masking and template matching."""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import logging
import numpy as np

from robex.vision.ocr import OcrEngine, ocr_engine

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

    def detect_ui_elements(
        self,
        frame: np.ndarray,
        min_area: int = 200,
        max_area: int = 300000,
        min_aspect: float = 0.2,
        max_aspect: float = 6.0,
        min_rectangularity: float = 0.6,
    ) -> List["DetectionResult"]:
        """Discovers clickable-looking UI elements (buttons, cards) with no predefined
        color or template.

        Uses Canny edge detection followed by morphological closing to bridge small
        gaps in button borders into solid contours, then filters those contours by
        area, aspect ratio, and rectangularity (how much of its own bounding box the
        contour actually fills) so only shapes that look like real UI controls --
        rather than arbitrary background noise -- are kept.
        """
        if not HAS_CV2 or frame is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        results: List[DetectionResult] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (min_area <= area <= max_area):
                continue

            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw == 0 or bh == 0:
                continue

            aspect_ratio = bw / bh
            if not (min_aspect <= aspect_ratio <= max_aspect):
                continue

            rectangularity = area / (bw * bh + 1e-5)
            if rectangularity < min_rectangularity:
                continue

            results.append(DetectionResult(
                x=bx + bw // 2,
                y=by + bh // 2,
                width=bw,
                height=bh,
                confidence=min(1.0, rectangularity),
                label="ui_element",
            ))

        results.sort(key=lambda r: r.width * r.height, reverse=True)
        return results


class AutoPicker:
    """Finds the on-screen UI element that best matches a free-form semantic query.

    Scores candidates -- color-matched buttons plus generic edge-detected UI
    elements -- against color names, positional cues ('top'/'bottom'/'left'/
    'right'/'center'), and OCR text labels present in the query string, and
    returns the highest scoring match. This lets callers ask for things like
    "the button in the top right" or "Play" instead of only a bare color name.
    """

    def __init__(self, vision_detector: VisionDetector, ocr: Optional[OcrEngine] = None):
        self._detector = vision_detector
        self._ocr = ocr

    def find_element(self, frame: np.ndarray, query: str) -> Optional[DetectionResult]:
        """Returns the best-scoring detected element for `query`, or None if nothing
        scores above the baseline (no matching color/position/text signal at all)."""
        if not HAS_CV2 or frame is None or not query:
            return None

        q = query.lower()
        fh, fw = frame.shape[:2]

        # Color-matched buttons are a strong, unambiguous signal so they start with a
        # higher baseline score; generic edge-detected shapes are the fallback pool
        # for purely positional or text-only queries.
        candidates: List[Tuple[DetectionResult, float]] = []
        for color in COLOR_HSV_RANGES:
            if color in q:
                candidates += [(r, 0.6) for r in self._detector.find_buttons_by_color(frame, color)]
        candidates += [(r, 0.2) for r in self._detector.detect_ui_elements(frame)]

        if not candidates:
            return None

        ocr_hits = self._ocr.read_text(frame) if self._ocr and self._ocr.is_available else []

        best_result: Optional[DetectionResult] = None
        best_score = 0.0

        for result, score in candidates:
            if "top" in q:
                score += 0.3 if result.y < fh * 0.4 else -0.2
            if "bottom" in q:
                score += 0.3 if result.y > fh * 0.6 else -0.2
            if "left" in q:
                score += 0.3 if result.x < fw * 0.4 else -0.2
            if "right" in q:
                score += 0.3 if result.x > fw * 0.6 else -0.2
            if "center" in q or "middle" in q:
                centered = fw * 0.35 <= result.x <= fw * 0.65 and fh * 0.35 <= result.y <= fh * 0.65
                score += 0.3 if centered else -0.2

            for hit in ocr_hits:
                if hit.text and hit.text.lower() in q:
                    bx, by, bw, bh = result.bbox
                    if bx <= hit.x <= bx + bw and by <= hit.y <= by + bh:
                        score += 0.5

            if score > best_score:
                best_score = score
                best_result = result

        return best_result


# Global vision detector instance
detector = VisionDetector()

# Global auto-picker instance, wired to the shared detector and OCR engine
auto_picker = AutoPicker(detector, ocr_engine)
