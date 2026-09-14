"""Main desktop user interface for Robex."""

import logging
import time
from tkinter import filedialog
from typing import Dict, List, Optional

from robex.core.safety import global_safety
from robex.core.window import window_manager
from robex.engine.runner import runner, RunnerState
from robex.engine.history import history_recorder, ActionRecord, HistorySummary
from robex.ai.commander import parser
from robex.gui import theme

logger = logging.getLogger(__name__)

# Attempt customtkinter import with standard tkinter fallback
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    HAS_CTK = True
except ImportError:
    import tkinter as ctk
    HAS_CTK = False

# Process RAM readout uses the pywin32 APIs already required elsewhere in the
# project (see core/window.py) instead of adding a new dependency like psutil.
try:
    import win32process
    import win32api
    HAS_WIN32_MEM = True
except ImportError:
    HAS_WIN32_MEM = False

RAM_CEILING_MB = 4096

# Preset macro commands offered in the "Presets" dropdown.
PRESET_COMMANDS: Dict[str, str] = {
    "Vision: Click Green Button": "click green button, then wait 1s",
    "Vision: Click Red Button": "click red button, then wait 1s",
    "Movement: Hold W 2s then Jump": "hold w for 2s, then press space",
    "Continuous Left Clicker": "click, then wait 0.1s",
    "Stunt: Double Jump": "double jump, then wait 0.5s"
}


def get_preset_text(choice: str) -> Optional[str]:
    """Looks up the macro command text for a given preset menu choice."""
    return PRESET_COMMANDS.get(choice)


def window_titles(windows: List) -> List[str]:
    """Extracts a flat, de-duplicated list of window titles from list_open_windows()
    results, for populating the target-application dropdown."""
    titles: List[str] = []
    for w in windows:
        if w.title and w.title not in titles:
            titles.append(w.title)
    return titles


def parse_duration_to_seconds(value: str, unit: str) -> Optional[float]:
    """Parses a runtime-budget entry + unit ('seconds'/'minutes') into seconds.

    Returns None for a blank, zero, negative, or unparsable value, meaning
    "unlimited" -- matching MacroRunner's own max_duration_sec=None contract.
    """
    value = (value or "").strip()
    if not value:
        return None

    try:
        amount = float(value)
    except ValueError:
        logger.warning("Invalid runtime duration value '%s'; treating as unlimited.", value)
        return None

    if amount <= 0:
        return None

    return amount * 60.0 if unit == "minutes" else amount


def parse_action_delay(value: str) -> float:
    """Parses the action pacing-delay entry (seconds) into a float, defaulting to 0.0
    (no delay) for blank or invalid input."""
    value = (value or "").strip()
    if not value:
        return 0.0
    try:
        return max(0.0, float(value))
    except ValueError:
        logger.warning("Invalid action delay value '%s'; defaulting to 0.", value)
        return 0.0


def format_history_summary(summary: HistorySummary) -> str:
    """Formats a HistorySummary into a single readable status line."""
    return (
        f"Total: {summary.total_actions}  |  Success: {summary.success_count}  |  "
        f"Errors: {summary.error_count}  |  Avg: {summary.avg_duration_ms:.1f}ms"
    )


def format_history_records(records: List[ActionRecord], limit: int = 200) -> str:
    """Formats recent ActionRecords into display lines, oldest to most recent."""
    if not records:
        return "No actions recorded yet."

    lines = []
    for r in records[-limit:]:
        ts = time.strftime("%H:%M:%S", time.localtime(r.timestamp))
        marker = "OK " if r.status == "success" else "ERR"
        line = f"[{ts}] {marker} {r.action_type:<14} {r.duration_ms:7.1f}ms"
        if r.error_msg:
            line += f"  - {r.error_msg}"
        lines.append(line)
    return "\n".join(lines)


def get_process_ram_mb() -> Optional[float]:
    """Returns this process's current working-set RAM usage in MB, or None if
    unavailable (e.g. pywin32 not installed)."""
    if not HAS_WIN32_MEM:
        return None
    try:
        handle = win32api.GetCurrentProcess()
        info = win32process.GetProcessMemoryInfo(handle)
        return info["WorkingSetSize"] / (1024 * 1024)
    except Exception as e:
        logger.debug("Failed to read process RAM usage: %s", e)
        return None


def format_resource_badge(ram_mb: Optional[float], ceiling_mb: int = RAM_CEILING_MB) -> str:
    """Formats the RAM/VRAM resource monitor badge text."""
    ram_display = f"{ram_mb:.0f}" if ram_mb is not None else "N/A"
    return f"RAM {ram_display}/{ceiling_mb}MB  ·  VRAM 0MB"


class MainWindow:
    """Robex graphical control window."""

    def __init__(self):
        if HAS_CTK:
            self.root = ctk.CTk()
        else:
            self.root = ctk.Tk()
            self.root.configure(bg=theme.BG_DARK)

        self.root.title("Robex - AI Vision Game Macro")
        self.root.geometry("640x620")
        self.root.minsize(580, 520)

        # Hook runner callbacks
        runner.add_state_callback(self._on_runner_state_changed)
        global_safety.register_abort_callback(self._on_killswitch_invoked)

        self._build_ui()

        # Populate dynamic sections and start the periodic resource monitor.
        self._refresh_window_list()
        self._refresh_history_view()
        self.root.after(2000, self._update_resource_monitor)

    def _build_ui(self):
        # ----------------- Header -----------------
        if HAS_CTK:
            header_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            header_frame.pack(fill="x", padx=16, pady=(16, 8))

            title_label = ctk.CTkLabel(
                header_frame,
                text="ROBEX // AI GAME MACRO",
                font=(theme.FONT_FAMILY, 18, "bold"),
                text_color=theme.TEXT_PRIMARY
            )
            title_label.pack(side="left", padx=16, pady=12)

            self.resource_badge = ctk.CTkLabel(
                header_frame,
                text=format_resource_badge(None),
                font=("Consolas", 11),
                text_color=theme.TEXT_MUTED
            )
            self.resource_badge.pack(side="right", padx=16, pady=12)

            self.status_badge = ctk.CTkLabel(
                header_frame,
                text="● READY",
                font=(theme.FONT_FAMILY, 13, "bold"),
                text_color=theme.PRIMARY_ACCENT
            )
            self.status_badge.pack(side="right", padx=16, pady=12)
        else:
            header_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            header_frame.pack(fill="x", padx=16, pady=(16, 8))

            title_label = ctk.Label(
                header_frame,
                text="ROBEX // AI GAME MACRO",
                font=(theme.FONT_FAMILY, 16, "bold"),
                bg=theme.SURFACE_DARK,
                fg=theme.TEXT_PRIMARY
            )
            title_label.pack(side="left", padx=12, pady=10)

            self.resource_badge = ctk.Label(
                header_frame,
                text=format_resource_badge(None),
                font=("Consolas", 10),
                bg=theme.SURFACE_DARK,
                fg=theme.TEXT_MUTED
            )
            self.resource_badge.pack(side="right", padx=12, pady=10)

            self.status_badge = ctk.Label(
                header_frame,
                text="● READY",
                font=(theme.FONT_FAMILY, 12, "bold"),
                bg=theme.SURFACE_DARK,
                fg=theme.PRIMARY_ACCENT
            )
            self.status_badge.pack(side="right", padx=12, pady=10)

        # ----------------- Command Input -----------------
        if HAS_CTK:
            cmd_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            cmd_frame.pack(fill="x", padx=16, pady=8)

            cmd_label = ctk.CTkLabel(
                cmd_frame,
                text="Natural Language AI Command / Instruction (paste or dictate multiline text):",
                font=(theme.FONT_FAMILY, 13, "bold"),
                text_color=theme.TEXT_PRIMARY
            )
            cmd_label.pack(anchor="w", padx=16, pady=(12, 4))

            # Multiline textbox (replaces the old single-line CTkEntry) so pasted
            # paragraphs or speech-to-text dictation spanning several lines can be
            # entered directly; TextNormalizer/CommandParser already know how to
            # segment multiline text into sequential actions (see ai/normalizer.py).
            self.cmd_textbox = ctk.CTkTextbox(
                cmd_frame,
                font=(theme.FONT_FAMILY, 13),
                text_color=theme.TEXT_PRIMARY,
                fg_color=theme.BG_DARK,
                corner_radius=8,
                height=80
            )
            self.cmd_textbox.pack(fill="x", padx=16, pady=6)
            self.cmd_textbox.insert("1.0", "click green button, then wait 1s, then jump")

            # Presets row
            preset_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
            preset_row.pack(fill="x", padx=16, pady=(4, 12))

            preset_lbl = ctk.CTkLabel(preset_row, text="Presets:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED)
            preset_lbl.pack(side="left", padx=(0, 8))

            self.preset_menu = ctk.CTkOptionMenu(
                preset_row,
                values=list(PRESET_COMMANDS.keys()),
                command=self._on_preset_selected,
                width=240
            )
            self.preset_menu.pack(side="left", padx=4)

            self.loop_checkbox = ctk.CTkCheckBox(
                preset_row,
                text="Repeat Continuous Loop",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_PRIMARY
            )
            self.loop_checkbox.pack(side="right", padx=4)
        else:
            cmd_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            cmd_frame.pack(fill="x", padx=16, pady=8)

            cmd_label = ctk.Label(
                cmd_frame,
                text="Natural Language AI Command / Instruction (paste or dictate multiline text):",
                font=(theme.FONT_FAMILY, 12, "bold"),
                bg=theme.SURFACE_DARK,
                fg=theme.TEXT_PRIMARY
            )
            cmd_label.pack(anchor="w", padx=12, pady=(10, 4))

            self.cmd_textbox = ctk.Text(
                cmd_frame,
                font=(theme.FONT_FAMILY, 12),
                bg=theme.BG_DARK,
                fg=theme.TEXT_PRIMARY,
                height=4
            )
            self.cmd_textbox.pack(fill="x", padx=12, pady=6)
            self.cmd_textbox.insert("1.0", "click green button, then wait 1s, then jump")

            preset_row = ctk.Frame(cmd_frame, bg=theme.SURFACE_DARK)
            preset_row.pack(fill="x", padx=12, pady=(4, 10))

            preset_lbl = ctk.Label(preset_row, text="Presets:", font=(theme.FONT_FAMILY, 11), bg=theme.SURFACE_DARK, fg=theme.TEXT_MUTED)
            preset_lbl.pack(side="left", padx=(0, 8))

            self._preset_var = ctk.StringVar(value=list(PRESET_COMMANDS.keys())[0])
            self.preset_menu = ctk.OptionMenu(
                preset_row, self._preset_var, *PRESET_COMMANDS.keys(), command=self._on_preset_selected
            )
            self.preset_menu.pack(side="left", padx=4)

            self._loop_var = ctk.IntVar(value=0)
            self.loop_checkbox = ctk.Checkbutton(
                preset_row, text="Repeat Continuous Loop", variable=self._loop_var,
                bg=theme.SURFACE_DARK, fg=theme.TEXT_PRIMARY, selectcolor=theme.SURFACE_LIGHT
            )
            self.loop_checkbox.pack(side="right", padx=4)

        # ----------------- Target Application -----------------
        if HAS_CTK:
            target_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            target_frame.pack(fill="x", padx=16, pady=8)

            target_label = ctk.CTkLabel(
                target_frame, text="Target Application Window:",
                font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY
            )
            target_label.pack(anchor="w", padx=16, pady=(12, 4))

            target_row = ctk.CTkFrame(target_frame, fg_color="transparent")
            target_row.pack(fill="x", padx=16, pady=(0, 12))

            self.window_menu = ctk.CTkOptionMenu(target_row, values=["No windows found"], width=300)
            self.window_menu.pack(side="left", padx=(0, 8))

            self.refresh_windows_btn = ctk.CTkButton(
                target_row, text="Refresh", width=90,
                fg_color=theme.SURFACE_LIGHT, hover_color=theme.INFO_ACCENT,
                command=self._on_refresh_windows_clicked
            )
            self.refresh_windows_btn.pack(side="left", padx=4)

            self.focus_checkbox = ctk.CTkCheckBox(
                target_row, text="Require Window Focus", font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_PRIMARY, command=self._on_require_focus_toggled
            )
            self.focus_checkbox.pack(side="right", padx=4)
        else:
            target_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            target_frame.pack(fill="x", padx=16, pady=8)

            target_label = ctk.Label(
                target_frame, text="Target Application Window:", font=(theme.FONT_FAMILY, 12, "bold"),
                bg=theme.SURFACE_DARK, fg=theme.TEXT_PRIMARY
            )
            target_label.pack(anchor="w", padx=12, pady=(10, 4))

            target_row = ctk.Frame(target_frame, bg=theme.SURFACE_DARK)
            target_row.pack(fill="x", padx=12, pady=(0, 10))

            self._window_var = ctk.StringVar(value="No windows found")
            self.window_menu = ctk.OptionMenu(target_row, self._window_var, "No windows found")
            self.window_menu.pack(side="left", padx=(0, 8))

            self.refresh_windows_btn = ctk.Button(target_row, text="Refresh", command=self._on_refresh_windows_clicked)
            self.refresh_windows_btn.pack(side="left", padx=4)

            self._focus_var = ctk.IntVar(value=0)
            self.focus_checkbox = ctk.Checkbutton(
                target_row, text="Require Window Focus", variable=self._focus_var,
                command=self._on_require_focus_toggled,
                bg=theme.SURFACE_DARK, fg=theme.TEXT_PRIMARY, selectcolor=theme.SURFACE_LIGHT
            )
            self.focus_checkbox.pack(side="right", padx=4)

        # ----------------- Runtime Settings -----------------
        if HAS_CTK:
            settings_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            settings_frame.pack(fill="x", padx=16, pady=8)

            settings_label = ctk.CTkLabel(
                settings_frame, text="Runtime Settings:",
                font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY
            )
            settings_label.pack(anchor="w", padx=16, pady=(12, 4))

            settings_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
            settings_row.pack(fill="x", padx=16, pady=(0, 12))

            duration_lbl = ctk.CTkLabel(settings_row, text="Max Duration:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED)
            duration_lbl.pack(side="left", padx=(0, 6))

            self.duration_entry = ctk.CTkEntry(settings_row, placeholder_text="unlimited", width=80)
            self.duration_entry.pack(side="left", padx=(0, 4))

            self.duration_unit_menu = ctk.CTkOptionMenu(settings_row, values=["seconds", "minutes"], width=100)
            self.duration_unit_menu.pack(side="left", padx=(0, 16))

            delay_lbl = ctk.CTkLabel(settings_row, text="Action Delay (s):", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED)
            delay_lbl.pack(side="left", padx=(0, 6))

            self.delay_entry = ctk.CTkEntry(settings_row, placeholder_text="0.0", width=70)
            self.delay_entry.pack(side="left")
        else:
            settings_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            settings_frame.pack(fill="x", padx=16, pady=8)

            settings_label = ctk.Label(
                settings_frame, text="Runtime Settings:", font=(theme.FONT_FAMILY, 12, "bold"),
                bg=theme.SURFACE_DARK, fg=theme.TEXT_PRIMARY
            )
            settings_label.pack(anchor="w", padx=12, pady=(10, 4))

            settings_row = ctk.Frame(settings_frame, bg=theme.SURFACE_DARK)
            settings_row.pack(fill="x", padx=12, pady=(0, 10))

            duration_lbl = ctk.Label(settings_row, text="Max Duration:", bg=theme.SURFACE_DARK, fg=theme.TEXT_MUTED)
            duration_lbl.pack(side="left", padx=(0, 6))

            self.duration_entry = ctk.Entry(settings_row, width=8)
            self.duration_entry.pack(side="left", padx=(0, 4))

            self._duration_unit_var = ctk.StringVar(value="seconds")
            self.duration_unit_menu = ctk.OptionMenu(settings_row, self._duration_unit_var, "seconds", "minutes")
            self.duration_unit_menu.pack(side="left", padx=(0, 16))

            delay_lbl = ctk.Label(settings_row, text="Action Delay (s):", bg=theme.SURFACE_DARK, fg=theme.TEXT_MUTED)
            delay_lbl.pack(side="left", padx=(0, 6))

            self.delay_entry = ctk.Entry(settings_row, width=6)
            self.delay_entry.pack(side="left")

        # ----------------- Control Buttons -----------------
        if HAS_CTK:
            btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
            btn_frame.pack(fill="x", padx=16, pady=8)

            self.start_btn = ctk.CTkButton(
                btn_frame,
                text="▶ START (F8)",
                fg_color=theme.PRIMARY_ACCENT,
                hover_color="#059669",
                font=(theme.FONT_FAMILY, 14, "bold"),
                height=42,
                command=self.on_start_clicked
            )
            self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

            self.pause_btn = ctk.CTkButton(
                btn_frame,
                text="⏸ PAUSE (F9)",
                fg_color=theme.WARNING_ACCENT,
                hover_color="#d97706",
                font=(theme.FONT_FAMILY, 14, "bold"),
                height=42,
                command=self.on_pause_clicked
            )
            self.pause_btn.pack(side="left", expand=True, fill="x", padx=6)

            self.stop_btn = ctk.CTkButton(
                btn_frame,
                text="⏹ KILLSWITCH (F12)",
                fg_color=theme.DANGER_ACCENT,
                hover_color="#dc2626",
                font=(theme.FONT_FAMILY, 14, "bold"),
                height=42,
                command=self.on_stop_clicked
            )
            self.stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # ----------------- Event Log -----------------
        if HAS_CTK:
            log_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            log_frame.pack(expand=True, fill="both", padx=16, pady=(8, 8))

            log_header = ctk.CTkLabel(
                log_frame,
                text="Live Activity & Safety Log",
                font=(theme.FONT_FAMILY, 12, "bold"),
                text_color=theme.TEXT_MUTED
            )
            log_header.pack(anchor="w", padx=16, pady=(10, 4))

            self.log_textbox = ctk.CTkTextbox(
                log_frame,
                font=("Consolas", 12),
                text_color=theme.TEXT_PRIMARY,
                fg_color=theme.BG_DARK,
                corner_radius=8
            )
            self.log_textbox.pack(expand=True, fill="both", padx=12, pady=(0, 12))
            self.log_textbox.insert("end", "[INFO] Robex initialized. F12 Killswitch armed.\n")
        else:
            log_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            log_frame.pack(expand=True, fill="both", padx=16, pady=(8, 8))

            log_header = ctk.Label(
                log_frame, text="Live Activity & Safety Log", font=(theme.FONT_FAMILY, 11, "bold"),
                bg=theme.SURFACE_DARK, fg=theme.TEXT_MUTED
            )
            log_header.pack(anchor="w", padx=12, pady=(8, 4))

            self.log_textbox = ctk.Text(log_frame, font=("Consolas", 11), bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY)
            self.log_textbox.pack(expand=True, fill="both", padx=10, pady=(0, 10))
            self.log_textbox.insert("end", "[INFO] Robex initialized. F12 Killswitch armed.\n")

        # ----------------- Execution History -----------------
        if HAS_CTK:
            history_frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE_DARK, corner_radius=10)
            history_frame.pack(expand=True, fill="both", padx=16, pady=(0, 16))

            history_header_row = ctk.CTkFrame(history_frame, fg_color="transparent")
            history_header_row.pack(fill="x", padx=16, pady=(10, 4))

            history_header = ctk.CTkLabel(
                history_header_row, text="Execution History", font=(theme.FONT_FAMILY, 12, "bold"),
                text_color=theme.TEXT_MUTED
            )
            history_header.pack(side="left")

            self.export_history_btn = ctk.CTkButton(
                history_header_row, text="Export History (JSON)", width=170,
                fg_color=theme.SURFACE_LIGHT, hover_color=theme.INFO_ACCENT,
                command=self._on_export_history_clicked
            )
            self.export_history_btn.pack(side="right")

            self.refresh_history_btn = ctk.CTkButton(
                history_header_row, text="Refresh", width=80,
                fg_color=theme.SURFACE_LIGHT, hover_color=theme.INFO_ACCENT,
                command=self._refresh_history_view
            )
            self.refresh_history_btn.pack(side="right", padx=6)

            self.history_summary_label = ctk.CTkLabel(
                history_frame, text=format_history_summary(history_recorder.get_summary()),
                font=("Consolas", 11), text_color=theme.TEXT_SUCCESS
            )
            self.history_summary_label.pack(anchor="w", padx=16, pady=(0, 4))

            self.history_textbox = ctk.CTkTextbox(
                history_frame, font=("Consolas", 11), text_color=theme.TEXT_PRIMARY,
                fg_color=theme.BG_DARK, corner_radius=8, height=100
            )
            self.history_textbox.pack(expand=True, fill="both", padx=12, pady=(0, 12))
        else:
            history_frame = ctk.Frame(self.root, bg=theme.SURFACE_DARK)
            history_frame.pack(expand=True, fill="both", padx=16, pady=(0, 16))

            history_header_row = ctk.Frame(history_frame, bg=theme.SURFACE_DARK)
            history_header_row.pack(fill="x", padx=12, pady=(8, 4))

            history_header = ctk.Label(
                history_header_row, text="Execution History", font=(theme.FONT_FAMILY, 11, "bold"),
                bg=theme.SURFACE_DARK, fg=theme.TEXT_MUTED
            )
            history_header.pack(side="left")

            self.export_history_btn = ctk.Button(
                history_header_row, text="Export History (JSON)", command=self._on_export_history_clicked
            )
            self.export_history_btn.pack(side="right")

            self.refresh_history_btn = ctk.Button(history_header_row, text="Refresh", command=self._refresh_history_view)
            self.refresh_history_btn.pack(side="right", padx=6)

            self.history_summary_label = ctk.Label(
                history_frame, text=format_history_summary(history_recorder.get_summary()),
                font=("Consolas", 10), bg=theme.SURFACE_DARK, fg=theme.TEXT_SUCCESS
            )
            self.history_summary_label.pack(anchor="w", padx=12, pady=(0, 4))

            self.history_textbox = ctk.Text(history_frame, font=("Consolas", 10), bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY, height=6)
            self.history_textbox.pack(expand=True, fill="both", padx=10, pady=(0, 10))

    def _on_preset_selected(self, choice: str):
        text = get_preset_text(choice)
        if text is not None and hasattr(self, "cmd_textbox"):
            self.cmd_textbox.delete("1.0", "end")
            self.cmd_textbox.insert("1.0", text)

    def log_message(self, msg: str):
        """Appends a message to the UI log."""
        if hasattr(self, "log_textbox"):
            self.log_textbox.insert("end", f"{msg}\n")
            self.log_textbox.see("end")

    # ----------------- Target window helpers -----------------

    def _refresh_window_list(self):
        """Repopulates the target-window dropdown from window_manager.list_open_windows()."""
        titles = window_titles(window_manager.list_open_windows())
        if not titles:
            titles = ["No windows found"]

        if HAS_CTK:
            self.window_menu.configure(values=titles)
            self.window_menu.set(titles[0])
        else:
            menu = self.window_menu["menu"]
            menu.delete(0, "end")
            for title in titles:
                menu.add_command(label=title, command=lambda t=title: self._window_var.set(t))
            self._window_var.set(titles[0])

    def _on_refresh_windows_clicked(self):
        self._refresh_window_list()
        self.log_message("[INFO] Target window list refreshed.")

    def _on_require_focus_toggled(self):
        enabled = bool(self.focus_checkbox.get()) if HAS_CTK else bool(self._focus_var.get())
        runner.set_require_focus(enabled)
        self.log_message(f"[INFO] Require window focus: {'ON' if enabled else 'OFF'}")

    def _is_loop_enabled(self) -> bool:
        """Reads the 'Repeat Continuous Loop' checkbox across CTk/plain-tkinter,
        since CTkCheckBox exposes its own .get() but plain Checkbutton does not."""
        if not hasattr(self, "loop_checkbox"):
            return False
        if HAS_CTK:
            return bool(self.loop_checkbox.get())
        return bool(self._loop_var.get()) if hasattr(self, "_loop_var") else False

    # ----------------- Execution history helpers -----------------

    def _refresh_history_view(self):
        """Repopulates the history textbox and summary label from history_recorder."""
        if hasattr(self, "history_textbox"):
            self.history_textbox.delete("1.0", "end")
            self.history_textbox.insert("1.0", format_history_records(history_recorder.get_records()))
        if hasattr(self, "history_summary_label"):
            self.history_summary_label.configure(text=format_history_summary(history_recorder.get_summary()))

    def _on_export_history_clicked(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="robex_history.json"
        )
        if not filepath:
            return

        if history_recorder.export_to_json(filepath):
            self.log_message(f"[INFO] Execution history exported to {filepath}")
        else:
            self.log_message("[ERROR] Failed to export execution history.")

    # ----------------- Resource monitor -----------------

    def _update_resource_monitor(self):
        """Refreshes the RAM/VRAM badge and reschedules itself via root.after()."""
        if hasattr(self, "resource_badge"):
            self.resource_badge.configure(text=format_resource_badge(get_process_ram_mb()))
        self.root.after(2000, self._update_resource_monitor)

    def on_start_clicked(self):
        text = self.cmd_textbox.get("1.0", "end").strip() if hasattr(self, "cmd_textbox") else ""
        actions = parser.parse_instruction(text)
        if not actions:
            self.log_message("[ERROR] Could not parse any valid actions from command.")
            return

        # Apply runtime settings (duration budget / action pacing) for this run.
        if hasattr(self, "duration_entry"):
            unit = self.duration_unit_menu.get() if HAS_CTK else self._duration_unit_var.get()
            runner.set_max_duration(parse_duration_to_seconds(self.duration_entry.get(), unit))
        if hasattr(self, "delay_entry"):
            runner.set_action_delay(parse_action_delay(self.delay_entry.get()))

        repeat = 0 if self._is_loop_enabled() else 1
        runner.load_actions(actions, repeat_count=repeat)
        self.log_message(f"[START] Parsed {len(actions)} actions. Running...")
        runner.start()

    def on_pause_clicked(self):
        if runner.state == RunnerState.RUNNING:
            runner.pause()
            self.log_message("[PAUSE] Macro paused.")
        elif runner.state == RunnerState.PAUSED:
            runner.resume()
            self.log_message("[RESUME] Macro resumed.")

    def on_stop_clicked(self):
        runner.stop("User clicked Killswitch")
        self.log_message("[STOP] Killswitch triggered! Inputs released.")

    def _on_runner_state_changed(self, state: RunnerState, message: str):
        def update():
            if hasattr(self, "status_badge"):
                if state == RunnerState.RUNNING:
                    self.status_badge.configure(text="● RUNNING", text_color=theme.PRIMARY_ACCENT)
                elif state == RunnerState.PAUSED:
                    self.status_badge.configure(text="● PAUSED", text_color=theme.WARNING_ACCENT)
                elif state == RunnerState.STOPPED:
                    self.status_badge.configure(text="● STOPPED", text_color=theme.DANGER_ACCENT)
                else:
                    self.status_badge.configure(text="● READY", text_color=theme.TEXT_MUTED)

            if message:
                self.log_message(f"[{state.value}] {message}")

            # Keep the history view current as actions complete.
            self._refresh_history_view()

        self.root.after(0, update)

    def _on_killswitch_invoked(self):
        self.root.after(0, lambda: self.log_message("[SAFETY] Emergency killswitch callback invoked."))

    def run(self):
        """Starts GUI event loop."""
        self.root.mainloop()
