"""Main desktop user interface for Robex."""

import logging

from robex.core.safety import global_safety
from robex.engine.runner import runner, RunnerState
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
                text="Natural Language AI Command / Instruction:",
                font=(theme.FONT_FAMILY, 13, "bold"),
                text_color=theme.TEXT_PRIMARY
            )
            cmd_label.pack(anchor="w", padx=16, pady=(12, 4))

            self.cmd_entry = ctk.CTkEntry(
                cmd_frame,
                placeholder_text="e.g. click green button, then wait 1s, then jump",
                font=(theme.FONT_FAMILY, 13),
                height=38
            )
            self.cmd_entry.pack(fill="x", padx=16, pady=6)
            self.cmd_entry.insert(0, "click green button, then wait 1s, then jump")

            # Presets row
            preset_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
            preset_row.pack(fill="x", padx=16, pady=(4, 12))

            preset_lbl = ctk.CTkLabel(preset_row, text="Presets:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED)
            preset_lbl.pack(side="left", padx=(0, 8))

            self.preset_menu = ctk.CTkOptionMenu(
                preset_row,
                values=[
                    "Vision: Click Green Button",
                    "Vision: Click Red Button",
                    "Movement: Hold W 2s then Jump",
                    "Continuous Left Clicker",
                    "Stunt: Double Jump"
                ],
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
            log_frame.pack(expand=True, fill="both", padx=16, pady=(8, 16))

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

    def _on_preset_selected(self, choice: str):
        mapping = {
            "Vision: Click Green Button": "click green button, then wait 1s",
            "Vision: Click Red Button": "click red button, then wait 1s",
            "Movement: Hold W 2s then Jump": "hold w for 2s, then press space",
            "Continuous Left Clicker": "click, then wait 0.1s",
            "Stunt: Double Jump": "double jump, then wait 0.5s"
        }
        if choice in mapping and hasattr(self, "cmd_entry"):
            self.cmd_entry.delete(0, "end")
            self.cmd_entry.insert(0, mapping[choice])

    def log_message(self, msg: str):
        """Appends a message to the UI log."""
        if hasattr(self, "log_textbox"):
            self.log_textbox.insert("end", f"{msg}\n")
            self.log_textbox.see("end")

    def on_start_clicked(self):
        text = self.cmd_entry.get() if hasattr(self, "cmd_entry") else ""
        actions = parser.parse_instruction(text)
        if not actions:
            self.log_message("[ERROR] Could not parse any valid actions from command.")
            return

        repeat = 0 if getattr(self, "loop_checkbox", None) and self.loop_checkbox.get() else 1
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

        self.root.after(0, update)

    def _on_killswitch_invoked(self):
        self.root.after(0, lambda: self.log_message("[SAFETY] Emergency killswitch callback invoked."))

    def run(self):
        """Starts GUI event loop."""
        self.root.mainloop()
