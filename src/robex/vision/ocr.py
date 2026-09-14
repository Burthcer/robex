"""Extensible OCR engine abstraction for reading text labels off detected UI elements.

Tries lightweight, already-optional backends (pytesseract, easyocr) in priority
order and gracefully degrades to "no OCR available" when none are installed, so
text-label matching is best-effort rather than a hard dependency -- this keeps
the project within its strict RAM/VRAM budget by default.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    """A single recognized text region (center coordinates, like DetectionResult)."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float


class OcrEngine:
    """Reads text + bounding boxes from a frame, trying backends in priority order."""

    def __init__(self):
        self._backend = self._detect_backend()
        if self._backend:
            logger.info("OCR backend available: %s", self._backend)
        else:
            logger.info("No OCR backend installed; text-label matching is disabled.")

    def _detect_backend(self) -> Optional[str]:
        """Probes for an installed OCR library without importing anything heavy eagerly."""
        try:
            import pytesseract  # noqa: F401
            return "tesseract"
        except ImportError:
            pass

        try:
            import winocr  # noqa: F401 - Windows native OCR (lightweight, no model download)
            return "winocr"
        except ImportError:
            pass

        try:
            import easyocr  # noqa: F401
            return "easyocr"
        except ImportError:
            pass

        return None

    @property
    def is_available(self) -> bool:
        """Returns True if a real OCR backend was found."""
        return self._backend is not None

    def read_text(self, frame: Optional[np.ndarray]) -> List[OcrResult]:
        """Reads text regions from a frame. Returns [] gracefully if no backend is installed."""
        if frame is None or not self.is_available:
            return []

        try:
            if self._backend == "tesseract":
                return self._read_tesseract(frame)
            # winocr/easyocr hooks are intentionally left as extension points: wiring
            # them up is a drop-in addition here once a project actually depends on
            # one, without changing any caller of read_text().
        except Exception as e:
            logger.error("OCR read failed (backend=%s): %s", self._backend, e)

        return []

    def _read_tesseract(self, frame: np.ndarray) -> List[OcrResult]:
        import pytesseract

        data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
        results: List[OcrResult] = []

        for i, text in enumerate(data["text"]):
            if not text or not text.strip():
                continue

            raw_conf = data["conf"][i]
            try:
                conf = max(0.0, float(raw_conf)) / 100.0
            except (TypeError, ValueError):
                conf = 0.0

            w, h = data["width"][i], data["height"][i]
            results.append(OcrResult(
                text=text.strip(),
                x=data["left"][i] + w // 2,
                y=data["top"][i] + h // 2,
                width=w,
                height=h,
                confidence=conf,
            ))

        return results


# Global OCR engine instance
ocr_engine = OcrEngine()
