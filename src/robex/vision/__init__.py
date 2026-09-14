"""Vision and screen perception modules for button detection, color matching, and screen grab."""

# Note: intentionally does not re-export the `detector`/`auto_picker` singleton
# names here -- doing so would shadow the `robex.vision.detector` *submodule*
# attribute on this package, breaking `import robex.vision.detector` elsewhere.
# Use `from robex.vision.detector import detector, auto_picker` directly.
from robex.vision.detector import VisionDetector, DetectionResult, AutoPicker
from robex.vision.ocr import OcrEngine, OcrResult, ocr_engine

__all__ = ["VisionDetector", "DetectionResult", "AutoPicker", "OcrEngine", "OcrResult", "ocr_engine"]
