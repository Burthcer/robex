"""Unit tests for AutoPicker semantic query matching and OCR fallback handling."""

import numpy as np
import cv2
from robex.vision.detector import VisionDetector, AutoPicker, DetectionResult
from robex.vision.ocr import OcrEngine, OcrResult


def _bordered_button(image: np.ndarray, x0: int, y0: int, x1: int, y1: int, fill=(200, 200, 200)) -> None:
    image[y0:y1, x0:x1] = fill
    cv2.rectangle(image, (x0, y0), (x1 - 1, y1 - 1), (30, 30, 30), thickness=2)


class FakeOcrEngine(OcrEngine):
    """Stubbed OCR engine returning canned text hits instead of running a real backend."""

    def __init__(self, hits):
        self._hits = hits  # skip real __init__/backend probing entirely

    @property
    def is_available(self) -> bool:
        return True

    def read_text(self, frame):
        return self._hits


def test_find_element_by_color_query():
    detector = VisionDetector()
    picker = AutoPicker(detector)

    image = np.zeros((400, 400, 3), dtype=np.uint8)
    # BGR pure green square
    image[150:210, 150:210] = (0, 255, 0)

    result = picker.find_element(image, "click the green button")
    assert result is not None
    assert abs(result.x - 180) <= 2
    assert abs(result.y - 180) <= 2


def test_find_element_by_position_query():
    detector = VisionDetector()
    picker = AutoPicker(detector)

    image = np.zeros((400, 400, 3), dtype=np.uint8)
    _bordered_button(image, 20, 20, 100, 90)          # top-left
    _bordered_button(image, 300, 320, 380, 390)       # bottom-right

    result = picker.find_element(image, "button in the bottom right")
    assert result is not None
    assert result.x > 200
    assert result.y > 200


def test_find_element_with_ocr_text_match():
    detector = VisionDetector()
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    _bordered_button(image, 50, 50, 200, 120)

    # Text hit centered inside that button's bounding box.
    fake_hit = OcrResult(text="Play", x=125, y=85, width=40, height=20, confidence=0.9)
    picker = AutoPicker(detector, ocr=FakeOcrEngine([fake_hit]))

    result = picker.find_element(image, "Play")
    assert result is not None
    assert abs(result.x - 125) < 80
    assert abs(result.y - 85) < 40


def test_find_element_returns_none_for_blank_frame_and_query():
    detector = VisionDetector()
    picker = AutoPicker(detector)

    assert picker.find_element(np.zeros((100, 100, 3), dtype=np.uint8), "") is None
    assert picker.find_element(None, "green button") is None


def test_find_element_falls_back_to_generic_detection_without_color_or_ocr():
    detector = VisionDetector()
    picker = AutoPicker(detector, ocr=None)  # no OCR backend -> pure geometric fallback

    image = np.zeros((300, 300, 3), dtype=np.uint8)
    _bordered_button(image, 100, 100, 200, 180)

    result = picker.find_element(image, "the button")
    assert result is not None
    assert isinstance(result, DetectionResult)


def test_ocr_engine_gracefully_reports_unavailable_when_no_backend_installed():
    # In this project's default environment no OCR library is installed, so the
    # engine must degrade gracefully instead of raising.
    engine = OcrEngine()
    assert engine.read_text(np.zeros((50, 50, 3), dtype=np.uint8)) == []
