# Task 3: Smart Auto-Picker & Semantic Screen Perception

## Objective
Build an intelligent screen auto-picker and UI element detector that automatically locates clickable buttons, icons, and UI components from active game screens using contour geometry and color heuristics without requiring manual image crops, operating under 100 MB RAM and 0 GB VRAM.

## Target Files
- `src/robex/vision/detector.py` [MODIFY]
- `src/robex/vision/ocr.py` [NEW]
- `src/robex/vision/__init__.py` [MODIFY]
- `src/robex/engine/actions.py` [MODIFY]
- `tests/test_detector.py` [MODIFY]
- `tests/test_auto_picker.py` [NEW]

## Actionable Checklist
1. Create `src/robex/vision/ocr.py` defining an extensible `OcrEngine` interface with Windows native OCR / Tesseract / EasyOCR hooks and a graceful fallback returning bounding boxes with text confidence.
2. Implement `detect_ui_elements(frame) -> List[DetectionResult]` in `src/robex/vision/detector.py` using OpenCV Canny edge detection, morphological closing, and contour filtering (area, aspect ratio, rectangularity) to automatically discover clickable UI buttons and card elements without predefined templates.
3. Implement `AutoPicker` in `src/robex/vision/detector.py` with `find_element(frame, query: str) -> Optional[DetectionResult]` that scores detected elements against color names, positional cues (e.g. "top", "bottom", "center"), and text labels.
4. Update `VisionClickAction` in `src/robex/engine/actions.py` to support semantic `query` strings routed through `AutoPicker` in addition to pure color names.
5. Add unit tests in `tests/test_auto_picker.py` and extend `tests/test_detector.py` using synthetic game UI frames (buttons with borders, colors, and varied aspect ratios) to verify auto-detection, query matching, and fallback handling.

## Constraints
- **Strict Memory Ceiling**: Do NOT load neural network weights requiring more than 200 MB RAM; ensure 0 GB VRAM usage for the default heuristic and OpenCV vision pipeline to remain far below the 4 GB threshold.
- **Documentation Integrity**: Preserve all existing comments and docstrings in `detector.py`, `actions.py`, and `screen.py`.
- **Backward Compatibility**: Existing methods (`find_buttons_by_color`, `find_template`) and `COLOR_HSV_RANGES` must remain intact; all 44 existing unit tests must continue to pass without error.

## Verification Command
```powershell
.\venv\Scripts\pytest tests/test_auto_picker.py tests/test_detector.py tests/ -v
```
