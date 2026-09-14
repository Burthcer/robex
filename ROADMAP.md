# Robex Feature Roadmap: Advanced AI Command Understanding & Automation

This roadmap breaks down the development of Robex's advanced natural language input processing, universal multi-app automation, auto-picker computer vision, action execution telemetry, and resource-bounded execution into sequential, atomic tasks.

---

## Hardware & Resource Ceiling (Global Constraint)
- **VRAM Ceiling**: Maximum 4 GB VRAM.
- **System RAM Ceiling**: Maximum 4 GB RAM.
- **Guiding Architecture**: All AI text and vision pipelines must prioritize ultra-lightweight, efficient algorithms (rule-based NLP, `difflib`, OpenCV, lightweight OCR) to guarantee execution well below the 4 GB ceiling.

---

## Sequential Task Breakdown

### [Task 1] Intelligent Multiline Input, Spell Correction & Command Normalization [COMPLETED]
- **Status**: Completed & Verified (All 27 unit tests passing, zero VRAM / <50MB RAM).
- **Deliverables**:
  - `src/robex/ai/normalizer.py`: Fuzzy matching and spell correction for game commands using `difflib`.
  - Integration into `src/robex/ai/commander.py` to handle multiline inputs, dictation filler words, and sentence stops.
  - Unit test suite in `tests/test_normalizer.py` and extended `tests/test_commander.py`.

---

### [Task 2] Universal Multi-App Target & Window Focus Engine [COMPLETED]
- **Status**: Completed & Verified (All 44 unit tests passing, zero VRAM / <5MB RAM).
- **Deliverables**:
  - `src/robex/core/window.py`: Dynamic window enumeration (`list_open_windows`), `WindowInfo` dataclass, robust foreground restoration via `AttachThreadInput` / `BringWindowToTop`, and focus checks (`is_target_focused`, `ensure_target_focused`).
  - `src/robex/engine/runner.py`: Integrated optional pre-execution focus guard (`require_focus`) before macro loop iterations.
  - Unit test suite in `tests/test_window.py`.

---

### [Task 3] Smart Auto-Picker & Semantic Screen Perception [COMPLETED]
- **Status**: Completed & Verified (All 53 unit tests passing, zero VRAM / <50MB RAM).
- **Deliverables**:
  - `src/robex/vision/ocr.py`: Pluggable `OcrEngine` supporting Tesseract / WinOCR / EasyOCR with graceful degradation.
  - `src/robex/vision/detector.py`: `detect_ui_elements` contour shape detector and `AutoPicker` scoring element candidates by color, positional cues ("top", "bottom", "center"), and OCR text.
  - `src/robex/engine/actions.py`: `VisionClickAction` upgraded to route semantic queries through `AutoPicker`.
  - Unit test suite in `tests/test_auto_picker.py` and extended `tests/test_detector.py`.

---

### [Task 4] Execution Telemetry, Action History & Runtime Constraints
- **Goal**: Provide a detailed historical audit log of every action executed, timestamps, execution durations, and customizable runtime budget controls (max execution duration, loop caps, rate limits).
- **Deliverables**:
  - `src/robex/engine/history.py`: Structured execution history recorder with JSON export capability.
  - Runtime limits and timeouts inside `src/robex/engine/runner.py`.
  - Unit tests in `tests/test_history.py`.

---

### [Task 5] UI Overhaul: Multiline Prompting, History Inspector & Settings
- **Goal**: Update the CustomTkinter GUI to provide a multiline text area for speech-to-text/pasted input, a target application dropdown, a live history inspector panel, and runtime settings controls.
- **Deliverables**:
  - Updated `src/robex/gui/main_window.py` with multiline input box, target window selector, history view, and duration settings.
  - Real-time memory/resource monitor showing active RAM usage to ensure compliance with the 4 GB limit.
