# Task 5: UI Overhaul: Multiline Prompting, History Inspector & Settings

## Objective
Overhaul the CustomTkinter GUI with a multiline text area for dictated/pasted paragraphs, a target application window selector, a live execution history inspector, runtime duration controls, and a real-time RAM/VRAM resource monitor.

## Target Files
- `src/robex/gui/main_window.py` [MODIFY]
- `src/robex/gui/__init__.py` [MODIFY]
- `tests/test_gui.py` [NEW]

## Actionable Checklist
1. Replace `CTkEntry` in `src/robex/gui/main_window.py` with a multiline `CTkTextbox` capable of accepting long pasted paragraphs or speech-to-text dictation, integrating automatic text extraction and formatting before dispatching to `parser.parse_instruction()`.
2. Implement a Target Application section with a dropdown menu dynamically populated using `window_manager.list_open_windows()`, a "Refresh" button, and a checkbox to toggle `runner.set_require_focus()` to prevent off-screen execution.
3. Add a Runtime Settings panel containing `max_duration_sec` input controls (with a unit selector for seconds/minutes) and action pacing delay sliders/entries, connecting them to `runner.set_max_duration()` and `runner.set_action_delay()`.
4. Implement an Execution History view/tab displaying historical action records from `history_recorder.get_records()`, aggregate stats from `history_recorder.get_summary()`, and an "Export History (JSON)" button.
5. Add a real-time resource monitor badge in the header/status bar displaying current process RAM usage against the 4,096 MB hardware ceiling (and 0 MB VRAM indicator) updating periodically via `root.after()`.
6. Create `tests/test_gui.py` with headless/unit tests verifying UI initialization, component binding, preset insertion into the multiline text box, history record rendering, and resource monitor formatting without requiring an active desktop display.

## Constraints
- **Strict Resource Budget**: GUI memory footprint must not exceed 30 MB RAM and 0 MB VRAM, strictly honoring the 4 GB ceiling.
- **Headless & Fallback Safety**: Must not crash in headless testing environments or when `customtkinter` is replaced by standard `tkinter`.
- **Documentation Integrity**: Preserve all existing comments, docstrings, and architectural structure in `main_window.py`.
- **Backward Compatibility**: Existing hotkeys (F8 Start, F9 Pause, F12 Killswitch), presets, and loop toggles must remain intact; all 68 existing unit tests must continue to pass without error.

## Verification Command
```powershell
.\venv\Scripts\pytest tests/test_gui.py tests/ -v
```
