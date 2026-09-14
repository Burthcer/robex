# Robex 🎮🤖

**Robex** is an intelligent AI-assisted vision macro and game automation application for Roblox and Windows desktop games.

Instead of setting up rigid coordinates like old-fashioned auto-clickers, Robex lets you give **natural language commands** or let computer vision find buttons on screen for you.

---

## 🚀 Quick Start (Zero Technical Knowledge Needed!)

You don't need to use the command line. You can run everything by **double-clicking** files in Windows Explorer:

### 1. First Time Setup (Takes ~1 minute)
- Double-click **`setup_env.bat`**.
- This will automatically create an isolated Python environment and download all required packages.

### 2. Launching Robex
- Double-click **`run.bat`**.
- The Robex control center window will appear!

### 3. Creating a Standalone `.exe` App
- Double-click **`build_exe.bat`**.
- Once compilation finishes, your ready-to-use `.exe` will be located in the `dist/` folder!

---

## ⌨️ Global Hotkeys (Work In-Game)

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`F8`** | **Start** | Starts the current macro command sequence |
| **`F9`** | **Pause / Resume** | Temporarily pauses or resumes the macro |
| **`F12`** | **🚨 EMERGENCY KILLSWITCH** | **Immediately stops everything** and releases all held keys/mouse buttons |

> [!IMPORTANT]
> **Safety First**: If a macro is running and you want to take back control of your mouse and keyboard instantly, press **`F12`**!

---

## 💬 Example Commands You Can Type

In the **Command Box** in Robex, you can type natural English instructions. Robex will convert them into game actions automatically:

- `click green button, then wait 1s, then jump`
- `click red button, then wait 0.5s`
- `hold w for 3 seconds, then jump`
- `click at 500, 400, then wait 2s`
- `double jump, then wait 1s`
- `turn around, then hold w for 2s`

You can also check **"Repeat Continuous Loop"** to make Robex keep doing the action repeatedly until you press `F12` or click Stop!

---

## 📂 Project Structure

```
robex/
├── setup_env.bat        # 1-Click setup
├── run.bat              # 1-Click app launcher
├── build_exe.bat        # 1-Click .exe builder
├── CLAUDE.md            # Technical manual & developer instructions
├── config/              # Configuration & saved macro profiles
├── src/robex/           # Application source code
│   ├── core/            # DirectInput game movement & F12 killswitch
│   ├── vision/          # Screen capture & button detector
│   ├── ai/              # Natural language command parser
│   ├── engine/          # Macro action execution
│   └── gui/             # Desktop dark-mode user interface
└── tests/               # Automated tests
```

---

## 🛠️ For Developers & Terminal Users

Refer to [CLAUDE.md](file:///c:/Users/Asus/Desktop/robex/CLAUDE.md) for complete technical documentation, architectural rules, and CLI commands for testing and development.
