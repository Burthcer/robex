# Task 2: Universal Multi-App Target & Window Focus Engine

## Objective
Build a universal multi-application window manager and focus guard supporting dynamic window discovery, robust foreground restoration, client-relative coordinate mapping, and pre-execution focus validation.

## Target Files
- `src/robex/core/window.py` [MODIFY]
- `src/robex/core/__init__.py` [MODIFY]
- `src/robex/engine/runner.py` [MODIFY]
- `tests/test_window.py` [NEW]

## Actionable Checklist
1. Extend `WindowManager` in `src/robex/core/window.py` with a `WindowInfo` dataclass (hwnd, title, rect, is_visible) and implement `list_open_windows(filter_empty: bool = True) -> List[WindowInfo]` to enumerate and discover any running game or desktop application.
2. Implement robust foreground restoration in `focus_window(hwnd)` using `AttachThreadInput` / `BringWindowToTop` / `ShowWindow(SW_RESTORE)` fallback routines to ensure off-screen and background windows reliably regain input focus across Windows versions.
3. Add `is_target_focused() -> bool` and `ensure_target_focused(timeout_sec: float = 1.0) -> bool` to verify active window focus before mouse/keyboard events are dispatched.
4. Integrate target focus validation into `src/robex/engine/runner.py` as an optional pre-execution guard that automatically refocuses the target game/app before running action iterations.
5. Create `tests/test_window.py` with mock Win32 APIs testing window enumeration, coordinate transformation, focus validation, and runner integration under non-Windows and mock environments.

## Constraints
- **Strict Resource Budget**: Must use only the Python standard library and `pywin32` with zero additional heavy dependencies, maintaining 0 MB VRAM and <5 MB RAM overhead.
- **Documentation Integrity**: Preserve all existing comments, docstrings, and architectural structure in `src/robex/core/window.py` and `src/robex/engine/runner.py`.
- **Backward Compatibility**: Maintain the default target title as `"Roblox"` and preserve existing public methods (`find_target_window`, `get_window_rect`, `focus_window`, `window_to_screen_coords`) so existing code remains fully compatible. All 27 existing tests must continue to pass without regression.

## Verification Command
```powershell
.\venv\Scripts\pytest tests/test_window.py tests/ -v
```
