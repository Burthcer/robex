# Robex 🎮🤖

**Robex** is an intelligent, vision-assisted AI macro and game automation app for Roblox and Windows desktop games — built to run entirely on your own machine, with **zero cloud calls and zero VRAM usage**.

Instead of hard-coded pixel coordinates like old-school auto-clickers, Robex understands **plain English** ("click the green button, then wait 1s, then jump") and can **see the screen** to find buttons and UI elements on its own — typos, filler words, and multiline dictation included.

> [!WARNING]
> Robex simulates real mouse/keyboard input. Only run macros against games or apps you own and are allowed to automate. A global **F12 killswitch** is always armed to instantly stop everything.

---

## ✨ Features

- 🗣️ **Typo-tolerant natural language commands** — dictate or paste multiline paragraphs; Robex strips filler words ("um", "please", "could you"), fixes typos (`"clck gern botton"` → `click green button`), and segments the text into a sequence of actions automatically.
- 👁️ **Smart auto-picker** — beyond fixed color matching, `AutoPicker` scores on-screen elements by color, position ("top", "bottom-right", "center"), and OCR text so you can ask for things like *"the button in the top right"* or *"Play"*.
- 🎯 **Automatic UI element detection** — OpenCV contour/edge detection finds clickable buttons and cards with no manual template cropping required.
- 🪟 **Target window manager** — lists every open window, lets you pick the one to automate, and can auto-refocus it before each macro loop so input never leaks to the wrong app.
- ⏱️ **Runtime budgets** — cap a macro to a max duration (seconds/minutes) and add pacing delays between actions, right from the GUI.
- 📊 **Execution history & telemetry** — every action is timed and logged to a bounded in-memory ring buffer, viewable live in the GUI and exportable as JSON.
- 🕹️ **DirectInput-accurate controls** — real hardware scan codes for WASD movement and camera control, so Roblox's engine doesn't ignore synthetic input the way it does with plain OS events.
- 🛑 **Safety first** — a global `F12` emergency killswitch and abort-callback system guarantee held keys/mouse buttons are released the instant something goes wrong.
- 💻 **Runs anywhere from source to a single `.exe`** — no Python required for end users.

---

## 🚀 Quick Start

### Option A — Just run the app (no Python needed)

Grab the latest `Robex.exe` from the [Releases](../../releases) page and double-click it. That's it.

### Option B — Run from source (zero technical knowledge needed)

Everything below is a **double-click** in Windows Explorer, no terminal required:

1. **Setup** — double-click [`setup_env.bat`](setup_env.bat). Creates an isolated Python virtual environment and installs all dependencies (~1 minute).
2. **Run** — double-click [`run.bat`](run.bat). The Robex control window opens.
3. **Build your own `.exe`** — double-click [`build_exe.bat`](build_exe.bat). PyInstaller compiles a standalone app into `dist/Robex.exe`.

### Option C — Terminal / developer setup

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

python -m robex          # run from source
pytest -v                # run the test suite
pyinstaller robex.spec --noconfirm --clean   # build the .exe
```

---

## ⌨️ Global Hotkeys

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`F8`** | **Start** | Starts the current macro command sequence |
| **`F9`** | **Pause / Resume** | Temporarily pauses or resumes the macro |
| **`F12`** | **🚨 EMERGENCY KILLSWITCH** | **Immediately stops everything** and releases all held keys/mouse buttons |

> [!IMPORTANT]
> If a macro is running and you want to take back control of your mouse and keyboard instantly, press **`F12`**.

---

## 💬 Example Commands

Type (or paste, or dictate) natural English into the command box — typos and filler words are fine:

```
click green button, then wait 1s, then jump
click red button, then wait 0.5s
hold w for 3 seconds, then jump
click at 500, 400, then wait 2s
double jump, then wait 1s
turn around, then hold w for 2s
walk for 3 seconds
please click the botton, then wait 1s
```

Multiline paste also works — each line (or sentence) becomes its own step:

```
click green button
wait 2 seconds
jump
```

Check **"Repeat Continuous Loop"** to keep looping the sequence until you press `F12` or click Stop.

---

## 🧠 How it works

```
 Natural language / dictation
          │
          ▼
 TextNormalizer      → filler removal, typo correction, multiline segmentation
          │
          ▼
 CommandParser        → parses clauses into typed Action objects
          │
          ▼
 MacroRunner           → threaded execution: pause/resume, duration budgets,
   │      │               pacing delays, focus guard, history telemetry
   │      ▼
   │  VisionClickAction → AutoPicker scores color / position / OCR text
   │      │               against on-screen elements found via OpenCV
   ▼      ▼
 InputDriver (DirectInput / SendInput) ──► the game
```

---

## 📂 Project Structure

```
robex/
├── setup_env.bat          # 1-click setup
├── run.bat                # 1-click app launcher
├── build_exe.bat           # 1-click .exe builder
├── robex.spec              # PyInstaller build spec
├── CLAUDE.md                # Full technical/architecture manual
├── config/                  # Default settings & saved macro profiles
├── src/robex/
│   ├── core/                # DirectInput driver, F12 killswitch, window manager
│   ├── vision/               # Screen capture, color/contour detection, OCR, AutoPicker
│   ├── ai/                   # Text normalizer & natural-language command parser
│   ├── engine/                # Actions, threaded runner, execution history
│   └── gui/                   # CustomTkinter dark-mode desktop UI
└── tests/                    # 87 automated unit tests (pytest)
```

---

## 🛠️ For Developers

Full architecture notes, coding rules, and exact CLI commands live in [CLAUDE.md](CLAUDE.md).

```powershell
pytest -v                 # run all tests
ruff check src tests      # lint
```

---

## 📄 License

[MIT](LICENSE)
