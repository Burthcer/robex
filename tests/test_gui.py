"""Headless unit tests for the Robex GUI.

Widget creation is stubbed out with a lightweight fake toolkit (both the
CTk* and plain-tkinter APIs main_window.py can call) so these tests never
open a real window and can run without an active desktop display.
"""

import types
from unittest.mock import MagicMock

import pytest

import robex.gui.main_window as mw
from robex.engine.history import HistoryRecorder, ActionRecord


# --------------------------------------------------------------------------
# Fake toolkit: implements just enough of both the CTk* and plain-tkinter
# widget APIs for main_window.py to build its UI against, without ever
# touching a real window/display.
# --------------------------------------------------------------------------

class _FakeWidget:
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs

    def pack(self, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def cget(self, key):
        return self.kwargs.get(key)


class _FakeButton(_FakeWidget):
    pass


class _FakeCheckBox(_FakeWidget):
    """Stands in for CTkCheckBox, which exposes its own .get()."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._value = 0

    def get(self):
        return self._value

    def select(self):
        self._value = 1

    def deselect(self):
        self._value = 0


class _FakeOptionMenu(_FakeWidget):
    """Stands in for CTkOptionMenu (values=[...] kwarg, native .get()/.set())."""

    def __init__(self, parent=None, values=None, command=None, **kw):
        super().__init__(parent, command=command, **kw)
        self.values = list(values or [])
        self._current = self.values[0] if self.values else ""
        self.command = command

    def set(self, value):
        self._current = value

    def get(self):
        return self._current

    def configure(self, **kwargs):
        super().configure(**kwargs)
        if "values" in kwargs:
            self.values = list(kwargs["values"])
            if self.values:
                self._current = self.values[0]


class _FakeTextEditable(_FakeWidget):
    """Stands in for CTkTextbox/CTkEntry (and plain Text/Entry)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._text = ""

    def insert(self, index, text):
        self._text += text

    def delete(self, start, end=None):
        self._text = ""

    def get(self, start=None, end=None):
        return self._text

    def see(self, index):
        pass


class _FakeRoot(_FakeWidget):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.after_calls = []

    def title(self, *a, **kw):
        pass

    def geometry(self, *a, **kw):
        pass

    def minsize(self, *a, **kw):
        pass

    def after(self, delay, fn=None, *args):
        # Record but do NOT auto-invoke -- _update_resource_monitor reschedules
        # itself, so auto-invoking here would recurse without a real event loop.
        self.after_calls.append((delay, fn))

    def mainloop(self):
        pass

    def withdraw(self):
        pass

    def destroy(self):
        pass


class _FakeVar:
    """Stands in for tkinter.StringVar/IntVar."""

    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeMenu:
    def __init__(self):
        self.items = []

    def delete(self, start, end):
        self.items = []

    def add_command(self, label=None, command=None):
        self.items.append((label, command))


class _FakeTkOptionMenu(_FakeWidget):
    """Stands in for plain tkinter.OptionMenu (variable + *values, ["menu"] access)."""

    def __init__(self, parent, variable, *values, command=None, **kw):
        super().__init__(parent, command=command, **kw)
        self.variable = variable
        self.command = command
        if values:
            self.variable.set(values[0])
        self._menu = _FakeMenu()

    def __getitem__(self, key):
        if key == "menu":
            return self._menu
        raise KeyError(key)


def _build_fake_ctk_module():
    """Builds a fake module exposing both the CTk* API and the plain-tkinter
    API, so it can stand in for `ctk` regardless of HAS_CTK."""
    fake = types.SimpleNamespace()

    # customtkinter-style names
    fake.CTk = _FakeRoot
    fake.CTkFrame = _FakeWidget
    fake.CTkLabel = _FakeWidget
    fake.CTkButton = _FakeButton
    fake.CTkCheckBox = _FakeCheckBox
    fake.CTkOptionMenu = _FakeOptionMenu
    fake.CTkTextbox = _FakeTextEditable
    fake.CTkEntry = _FakeTextEditable
    fake.set_appearance_mode = lambda *a, **kw: None
    fake.set_default_color_theme = lambda *a, **kw: None

    # plain-tkinter-style names (used when HAS_CTK is False)
    fake.Tk = _FakeRoot
    fake.Frame = _FakeWidget
    fake.Label = _FakeWidget
    fake.Button = _FakeButton
    fake.Checkbutton = _FakeWidget
    fake.OptionMenu = _FakeTkOptionMenu
    fake.Text = _FakeTextEditable
    fake.Entry = _FakeTextEditable
    fake.StringVar = _FakeVar
    fake.IntVar = _FakeVar

    return fake


@pytest.fixture
def fake_window(monkeypatch):
    """Builds a MainWindow with the widget toolkit, target-window list, and
    history recorder all stubbed out -- no real GUI, no real OS window
    enumeration, isolated history state."""
    monkeypatch.setattr(mw, "ctk", _build_fake_ctk_module())
    monkeypatch.setattr(mw, "HAS_CTK", True)
    monkeypatch.setattr(mw.window_manager, "list_open_windows", lambda *a, **kw: [])
    fresh_history = HistoryRecorder()
    monkeypatch.setattr(mw, "history_recorder", fresh_history)

    window = mw.MainWindow()
    window._history = fresh_history  # stash for assertions
    return window


@pytest.fixture
def fake_window_plain_tkinter(monkeypatch):
    """Same as fake_window, but forces the HAS_CTK=False (plain tkinter) branch."""
    monkeypatch.setattr(mw, "ctk", _build_fake_ctk_module())
    monkeypatch.setattr(mw, "HAS_CTK", False)
    monkeypatch.setattr(mw.window_manager, "list_open_windows", lambda *a, **kw: [])
    monkeypatch.setattr(mw, "history_recorder", HistoryRecorder())
    return mw.MainWindow()


# --------------------------------------------------------------------------
# UI initialization / component binding
# --------------------------------------------------------------------------

def test_main_window_initializes_without_a_real_display(fake_window):
    w = fake_window
    assert hasattr(w, "cmd_textbox")
    assert hasattr(w, "window_menu")
    assert hasattr(w, "focus_checkbox")
    assert hasattr(w, "duration_entry")
    assert hasattr(w, "duration_unit_menu")
    assert hasattr(w, "delay_entry")
    assert hasattr(w, "history_textbox")
    assert hasattr(w, "history_summary_label")
    assert hasattr(w, "resource_badge")


def test_main_window_initializes_with_plain_tkinter_fallback(fake_window_plain_tkinter):
    w = fake_window_plain_tkinter
    assert hasattr(w, "cmd_textbox")
    assert hasattr(w, "window_menu")
    assert hasattr(w, "_focus_var")
    assert hasattr(w, "_duration_unit_var")


def test_control_buttons_bound_to_handlers(fake_window):
    w = fake_window
    assert w.start_btn.kwargs["command"] == w.on_start_clicked
    assert w.pause_btn.kwargs["command"] == w.on_pause_clicked
    assert w.stop_btn.kwargs["command"] == w.on_stop_clicked


def test_window_dropdown_falls_back_to_placeholder_when_no_windows(fake_window):
    assert fake_window.window_menu.get() == "No windows found"


# --------------------------------------------------------------------------
# Preset insertion into the multiline command textbox
# --------------------------------------------------------------------------

def test_default_command_text_is_preloaded(fake_window):
    assert "click green button" in fake_window.cmd_textbox.get("1.0", "end")


def test_preset_selection_inserts_into_multiline_textbox(fake_window):
    fake_window._on_preset_selected("Movement: Hold W 2s then Jump")
    assert fake_window.cmd_textbox.get("1.0", "end") == "hold w for 2s, then press space"


def test_get_preset_text_returns_none_for_unknown_choice():
    assert mw.get_preset_text("not a real preset") is None


# --------------------------------------------------------------------------
# Execution history rendering
# --------------------------------------------------------------------------

def test_refresh_history_view_renders_records(fake_window):
    fake_window._history.record(action_type="click", duration_ms=5.0, status="success")
    fake_window._history.record(action_type="wait", duration_ms=1000.0, status="error", error_msg="boom")

    fake_window._refresh_history_view()

    rendered = fake_window.history_textbox.get("1.0", "end")
    assert "click" in rendered
    assert "wait" in rendered
    assert "boom" in rendered

    summary_text = fake_window.history_summary_label.cget("text")
    assert "Total: 2" in summary_text
    assert "Errors: 1" in summary_text


def test_format_history_records_empty_history():
    assert mw.format_history_records([]) == "No actions recorded yet."


def test_format_history_records_includes_status_and_duration():
    record = ActionRecord(
        action_type="click", details="d", timestamp=0.0, duration_ms=12.3, status="success"
    )
    text = mw.format_history_records([record])
    assert "click" in text
    assert "12.3" in text
    assert "OK" in text


# --------------------------------------------------------------------------
# Resource monitor formatting
# --------------------------------------------------------------------------

def test_format_resource_badge_with_known_usage():
    assert mw.format_resource_badge(512.0) == "RAM 512/4096MB  ·  VRAM 0MB"


def test_format_resource_badge_unavailable():
    assert mw.format_resource_badge(None) == "RAM N/A/4096MB  ·  VRAM 0MB"


def test_update_resource_monitor_updates_badge_and_reschedules(fake_window, monkeypatch):
    monkeypatch.setattr(mw, "get_process_ram_mb", lambda: 256.0)
    before_calls = len(fake_window.root.after_calls)

    fake_window._update_resource_monitor()

    assert fake_window.resource_badge.cget("text") == mw.format_resource_badge(256.0)
    assert len(fake_window.root.after_calls) == before_calls + 1


# --------------------------------------------------------------------------
# Runtime settings parsing (pure helpers)
# --------------------------------------------------------------------------

def test_parse_duration_to_seconds_blank_is_unlimited():
    assert mw.parse_duration_to_seconds("", "seconds") is None
    assert mw.parse_duration_to_seconds("0", "seconds") is None
    assert mw.parse_duration_to_seconds("not a number", "seconds") is None


def test_parse_duration_to_seconds_converts_minutes():
    assert mw.parse_duration_to_seconds("2", "minutes") == 120.0
    assert mw.parse_duration_to_seconds("30", "seconds") == 30.0


def test_parse_action_delay_defaults_and_parses():
    assert mw.parse_action_delay("") == 0.0
    assert mw.parse_action_delay("bogus") == 0.0
    assert mw.parse_action_delay("0.25") == 0.25


# --------------------------------------------------------------------------
# on_start_clicked wiring (loop checkbox, runtime settings) across toolkits
# --------------------------------------------------------------------------

def test_on_start_clicked_applies_runtime_settings_and_loop_flag(fake_window, monkeypatch):
    mock_runner = MagicMock()
    monkeypatch.setattr(mw, "runner", mock_runner)

    fake_window.duration_entry.insert(0, "5")
    fake_window.delay_entry.insert(0, "0.2")
    fake_window.loop_checkbox.select()

    fake_window.on_start_clicked()

    mock_runner.set_max_duration.assert_called_once_with(5.0)
    mock_runner.set_action_delay.assert_called_once_with(0.2)
    mock_runner.load_actions.assert_called_once()
    _, kwargs = mock_runner.load_actions.call_args
    assert kwargs["repeat_count"] == 0  # loop checkbox was checked -> infinite repeat
    mock_runner.start.assert_called_once()


def test_on_start_clicked_works_with_plain_tkinter_loop_checkbox(fake_window_plain_tkinter, monkeypatch):
    # Regression test: plain tkinter.Checkbutton has no .get() of its own --
    # the loop flag must be read from the backing IntVar instead.
    mock_runner = MagicMock()
    monkeypatch.setattr(mw, "runner", mock_runner)

    fake_window_plain_tkinter._loop_var.set(1)
    fake_window_plain_tkinter.on_start_clicked()

    _, kwargs = mock_runner.load_actions.call_args
    assert kwargs["repeat_count"] == 0

    fake_window_plain_tkinter._loop_var.set(0)
    fake_window_plain_tkinter.on_start_clicked()
    _, kwargs = mock_runner.load_actions.call_args
    assert kwargs["repeat_count"] == 1


def test_window_titles_deduplicates_and_skips_blank():
    windows = [
        types.SimpleNamespace(title="Roblox"),
        types.SimpleNamespace(title="Roblox"),
        types.SimpleNamespace(title=""),
        types.SimpleNamespace(title="Notepad"),
    ]
    assert mw.window_titles(windows) == ["Roblox", "Notepad"]
