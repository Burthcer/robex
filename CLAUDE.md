# CLAUDE.md - Robex Architecture & Developer Guide

## 1. Project Purpose
**Robex** is an intelligent, vision-assisted game automation and AI macro application designed for Roblox and Windows desktop games. Unlike conventional auto-clickers that rely on static screen coordinates, Robex empowers users to provide natural language commands (e.g. *"Click the green button, then wait 1s, then jump and hold W for 3s"*).

Key goals:
- **Vision-Driven Automation**: Detects on-screen buttons, icons, and UI elements via color-range contour detection, template matching, and multimodal vision hooks.
- **DirectX / DirectInput Compatibility**: Simulates true hardware scan codes to control 3D camera rotation and WASD character movement without getting ignored by game engines.
- **Fail-Safe Safety First**: Global emergency killswitch (`F12`) and screen-corner failsafes that instantly release all held keys and abort background threads.
- **Zero-Friction for Non-Technical Users**: Modern dark-mode GUI and single-click Windows batch scripts (`setup_env.bat`, `run.bat`, `build_exe.bat`) to run from source or compile into a standalone `.exe`.

---

## 2. Tech Stack
| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ (Recommended: Python 3.12 64-bit) | Modern standard library, broad wheel support for OpenCV and PyInstaller |
| **Desktop GUI** | `CustomTkinter` (with `Tkinter` fallback) | Lightweight, modern Windows 11 dark theme, zero C++ runtime dependencies, fast launch |
| **Game Input Simulation** | `pydirectinput`, `pyautogui`, `ctypes` (Win32 SendInput) | Hardware scan code simulation required for Roblox 3D camera drag and WASD movement |
| **Safety & Hotkeys** | `pynput` | Global low-level keyboard hook for immediate emergency killswitch (`F12`) |
| **Screen Perception** | `mss`, `opencv-python-headless`, `Pillow` | Ultra-fast multi-monitor capture (60+ FPS) + HSV color masking & template matching |
| **Window Management** | `pywin32` | Detecting Roblox window handle, checking bounds, and focusing game |
| **AI Command Interpreter** | `re`, `robex.ai.commander`, multimodal API hooks | Parses plain English commands into typed atomic macro actions |
| **Packaging** | `PyInstaller` | Bundles entire runtime into a standalone Windows `.exe` |
| **Testing** | `pytest` | Automated verification of safety, actions, and command parsing |

---

## 3. Directory Layout
```
robex/
├── CLAUDE.md                     # Comprehensive developer manual, rules, and commands
├── README.md                     # User guide with 1-click execution instructions
├── pyproject.toml                # Project build metadata and dependency specifications
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development, testing, and compilation dependencies
├── robex.spec                    # PyInstaller specification for compiling Robex.exe
├── setup_env.bat                 # 1-click Windows script: creates venv & installs packages
├── run.bat                       # 1-click Windows script: launches the Robex application
├── build_exe.bat                 # 1-click Windows script: compiles standalone .exe
├── .gitignore                    # Git ignore definitions for Python, venv, and build artifacts
│
├── config/
│   ├── settings.json             # Default configuration (hotkeys, poll intervals, thresholds)
│   └── profiles/
│       └── example_macro.json    # Sample JSON macro profile (actions & repeats)
│
├── src/
│   └── robex/
│       ├── __init__.py           # Package exports and version info
│       ├── __main__.py           # Entry point for `python -m robex`
│       ├── app.py                # Central application coordinator and lifecycle manager
│       │
│       ├── core/                 # Low-level hardware & OS interaction
│       │   ├── __init__.py
│       │   ├── input_driver.py   # DirectInput mouse & keyboard simulator (clicks, holds, stunts)
│       │   ├── safety.py         # Global emergency killswitch (F12) & auto-release hooks
│       │   └── window.py         # Roblox window finder, rect calculation, and focus manager
│       │
│       ├── vision/               # Visual screen perception engine
│       │   ├── __init__.py
│       │   ├── screen.py         # Fast screen grabber via mss and PIL
│       │   └── detector.py       # HSV color-range button detector and OpenCV template matcher
│       │
│       ├── ai/                   # Command parsing & AI agent integrations
│       │   ├── __init__.py
│       │   ├── commander.py      # Natural language instruction parser
│       │   └── vision_agent.py   # Multimodal vision interface hook (Gemini / coordinates)
│       │
│       ├── engine/               # Macro execution pipeline
│       │   ├── __init__.py
│       │   ├── actions.py        # Atomic action dataclasses (Click, KeyPress, Stunt, Wait)
│       │   └── runner.py         # Threaded runner with start, pause, resume, and killswitch checks
│       │
│       └── gui/                  # Desktop user interface
│           ├── __init__.py
│           ├── main_window.py    # CustomTkinter dark-mode control window
│           └── theme.py          # Color palette, font definitions, and visual constants
│
└── tests/
    ├── __init__.py
    ├── test_safety.py            # Unit tests for killswitch activation & callbacks
    ├── test_actions.py           # Unit tests for action serialization & primitives
    └── test_commander.py         # Unit tests for natural language command parsing
```

---

## 4. Strict Coding Rules

### Rule 1: Never Delete Existing Comments or Docstrings
Preserve all comments, explanations, and docstrings present in the codebase. When modifying code, add clarifying commentary rather than removing existing documentation.

### Rule 2: Keep Logic Strictly Modular
- **No Input Calls in GUI**: The GUI layer (`robex.gui`) must NEVER invoke `pyautogui`, `pydirectinput`, or OS input functions directly. All actions must be dispatched through `robex.engine.runner` and `robex.core.safety`.
- **Model-View-Controller Separation**: Core input simulation, vision detection, macro sequencing, and UI display must remain completely decoupled.

### Rule 3: Safety First & Killswitch Invariant
- **Continuous Safety Checks**: Every loop, multi-step action, or timed wait must call `global_safety.assert_safe()` before and during execution (at intervals not exceeding 50ms).
- **Auto-Release Guarantee**: Any input that holds down a key (`key_down`) or mouse button (`mouse_down`) MUST register an abort callback with `global_safety` so that held keys are immediately released if aborted.

### Rule 4: DirectInput Compatibility for Game Input
- Standard OS mouse clicks and key events are frequently ignored by DirectX game loops (such as Roblox 3D camera controls and WASD movement).
- Always route game controls through `InputDriver` using hardware scan codes (`pydirectinput` or Win32 `SendInput`).

### Rule 5: Non-Blocking UI Threads
- Never execute loops, sleeps, or network calls on the main Tkinter/CustomTkinter GUI thread.
- All macro workloads must execute inside a dedicated background worker thread (`MacroRunner._worker_loop`). GUI updates must use `root.after()`.

### Rule 6: Graceful Fallbacks & Defensive Error Handling
- If optional libraries (e.g. `pydirectinput`, `customtkinter`, `pywin32`) are missing, the system must degrade gracefully (e.g. falling back to `pyautogui`, standard `tkinter`, or primary monitor coordinates) without crashing.

---

## 5. Exact Terminal & Batch Commands

### 5.1 One-Click Windows Batch Scripts (Recommended for Non-Technical Users)
Double-click these files directly in Windows Explorer:
- **Setup**: Double-click `setup_env.bat` (automatically installs Python venv and dependencies).
- **Run**: Double-click `run.bat` (launches Robex GUI).
- **Build .exe**: Double-click `build_exe.bat` (compiles standalone executable into `dist/Robex.exe`).

---

### 5.2 Command Line / Terminal Commands

#### Set Up Virtual Environment & Dependencies
```powershell
# Using Python 3.12 (Recommended):
py -3.12 -m venv venv

# Activate Virtual Environment (PowerShell):
.\venv\Scripts\Activate.ps1

# (Or Command Prompt):
.\venv\Scripts\activate.bat

# Upgrade pip and install development dependencies:
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### Run the Application from Source
```powershell
# From project root directory with active venv:
python -m robex
```

#### Run Unit Tests
```powershell
# Run all tests with verbose output:
pytest -v

# Run a specific test suite:
pytest tests/test_safety.py -v
pytest tests/test_commander.py -v
pytest tests/test_actions.py -v
```

#### Build the Standalone .exe
```powershell
# Build standalone Windows executable via PyInstaller spec:
pyinstaller robex.spec --noconfirm --clean

# The generated standalone executable will be in:
# dist/Robex.exe
```

#### Code Quality & Linting
```powershell
# Check code style with ruff:
ruff check src tests
```
