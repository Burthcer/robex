"""Unit tests for the OpenCV color detection engine."""

import numpy as np
import cv2
from robex.vision.detector import VisionDetector


def test_find_green_button_synthetic():
    detector = VisionDetector()

    # Create a 400x400 black image
    image = np.zeros((400, 400, 3), dtype=np.uint8)

    # Draw a 60x60 green square at (150, 150) -> (210, 210)
    # BGR format: Pure Green = (0, 255, 0)
    image[150:210, 150:210] = (0, 255, 0)

    results = detector.find_buttons_by_color(image, "green", min_area=50)

    assert len(results) == 1
    detected = results[0]
    # Center should be approximately (180, 180)
    assert abs(detected.x - 180) <= 2
    assert abs(detected.y - 180) <= 2
    assert detected.label == "green_button"


def test_find_unrecognized_color_returns_empty():
    detector = VisionDetector()
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    results = detector.find_buttons_by_color(image, "neon_rainbow")
    assert results == []


def _draw_bordered_button(image: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    """Draws a filled rectangle with a contrasting border, like a typical UI button,
    so Canny edge detection has a clean, closed outline to pick up."""
    image[y0:y1, x0:x1] = (200, 200, 200)
    cv2.rectangle(image, (x0, y0), (x1 - 1, y1 - 1), (30, 30, 30), thickness=2)


def test_detect_ui_elements_finds_bordered_buttons_of_varied_aspect_ratio():
    detector = VisionDetector()
    image = np.zeros((400, 400, 3), dtype=np.uint8)

    # A roughly square button and a wide rectangular button.
    _draw_bordered_button(image, 40, 40, 120, 120)
    _draw_bordered_button(image, 200, 300, 360, 350)

    results = detector.detect_ui_elements(image, min_area=200)

    assert len(results) >= 2
    for r in results:
        assert r.label == "ui_element"
        assert 0.0 < r.confidence <= 1.0


def test_detect_ui_elements_no_cv2_returns_empty(monkeypatch):
    import robex.vision.detector as detector_module
    monkeypatch.setattr(detector_module, "HAS_CV2", False)
    detector = VisionDetector()
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    assert detector.detect_ui_elements(image) == []


def test_detect_ui_elements_none_frame_returns_empty():
    detector = VisionDetector()
    assert detector.detect_ui_elements(None) == []
