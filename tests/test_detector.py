"""Unit tests for the OpenCV color detection engine."""

import numpy as np
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
