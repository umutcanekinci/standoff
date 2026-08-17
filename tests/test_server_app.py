"""server_app.py (the Tkinter server GUI) -- constructing a real Application
would build a real Tk root window and every widget in it, which needs a
live display (works on this Windows dev box, but not on the project's own
ubuntu-latest CI runner with no X server). These build a bare instance via
object.__new__(Application), which skips Tk.__init__ and all widget
construction entirely, then attach small fakes for the widgets/server/log
file so the state-machine and command-dispatch logic -- the actual bug
surface -- can be tested on any platform with no display at all.

set_app_window() and the widget-construction half of Application.__init__
are deliberately not covered here for the same reason (real Tk chrome).
Both the Linux-safe windll guard and the show_in_task_bar() platform gate
were verified manually (see the commit message) rather than via an
importlib.reload-based test, which would be fragile for the value gained.
"""
import threading

import pytest

tk = pytest.importorskip("tkinter")
END = tk.END

from app.server_app import Application, Grip  # noqa: E402 -- see importorskip above
from util.constants import SERVER_ADDR  # noqa: E402


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class SyncThread:
    """Runs the target synchronously instead of spawning a real thread --
    deterministic, and avoids leaking background threads across tests."""

    def __init__(self, target=None, args=(), daemon=None):
        self.target = target
        self.args = args

    def start(self):
        self.target(*self.args)


class FakeWidget:
    """Stands in for a tkinter widget only where the code under test uses
    item-assignment (`widget["state"] = ...`), which real Tk widgets support
    via __setitem__/__getitem__ on their config options."""

    def __init__(self):
        self.options = {}

    def __setitem__(self, key, value):
        self.options[key] = value

    def __getitem__(self, key):
        return self.options[key]


class FakeEntry:
    def __init__(self, text=""):
        self._text = text

    def get(self):
        return self._text


class FakeText:
    def __init__(self):
        self.state = None
        self.inserted = []
        self.deleted = []
        self.yview_calls = []

    def config(self, state=None, **kwargs):
        if state is not None:
            self.state = state

    def insert(self, index, text):
        self.inserted.append((index, text))

    def delete(self, start, end):
        self.deleted.append((start, end))

    def yview(self, index):
        self.yview_calls.append(index)


class FakeServer:
    def __init__(self, is_running=False):
        self.is_running = is_running
        self.serve = Spy()
        self.close = Spy()
        self.broadcast = Spy()


class FakeLogFile:
    def __init__(self):
        self.written = []
        self.flush_calls = 0
        self.closed = False

    def write(self, text):
        self.written.append(text)

    def flush(self):
        self.flush_calls += 1

    def close(self):
        self.closed = True


def make_app(**overrides):
    app = object.__new__(Application)
    app._log_lock = threading.Lock()
    app._log_file = FakeLogFile()
    app.server = FakeServer()
    app.command_log = FakeText()
    app.command_entry = FakeEntry()
    app.start_button = FakeWidget()
    app.restart_button = FakeWidget()
    app.close_button = FakeWidget()
    app.send_button = FakeWidget()
    app.destroy = Spy()
    for key, value in overrides.items():
        setattr(app, key, value)
    return app


# ── start / restart / close ─────────────────────────────────────────────────

def test_start_server_spawns_the_accept_loop_and_enables_controls(monkeypatch):
    app = make_app()
    monkeypatch.setattr("app.server_app.threading.Thread", SyncThread)

    app.start_server()

    assert app.server.serve.calls == [((SERVER_ADDR,), {})]
    assert app.start_button["state"] == "disabled"
    assert app.restart_button["state"] == "normal"
    assert app.close_button["state"] == "normal"
    assert app.send_button["state"] == "normal"


def test_start_server_is_idempotent_while_already_running(monkeypatch):
    app = make_app()
    app.server.is_running = True
    thread_calls = []
    monkeypatch.setattr(
        "app.server_app.threading.Thread",
        lambda **kw: thread_calls.append(kw),
    )

    app.start_server()

    assert thread_calls == []
    assert app.server.serve.calls == []


def test_restart_server_closes_then_starts_again(monkeypatch):
    app = make_app()
    monkeypatch.setattr("app.server_app.threading.Thread", SyncThread)

    app.restart_server()

    assert len(app.server.close.calls) == 1
    assert len(app.server.serve.calls) == 1


def test_close_server_resets_every_button_to_its_idle_state():
    app = make_app()
    app.start_button["state"] = "disabled"
    app.restart_button["state"] = "normal"
    app.close_button["state"] = "normal"
    app.send_button["state"] = "normal"

    app.close_server()

    assert len(app.server.close.calls) == 1
    assert app.start_button["state"] == "normal"
    assert app.restart_button["state"] == "disabled"
    assert app.close_button["state"] == "disabled"
    assert app.send_button["state"] == "disabled"


# ── command entry ────────────────────────────────────────────────────────────

def test_send_command_with_a_value_splits_command_and_value():
    app = make_app(command_entry=FakeEntry("KICK player1"))

    app.send_command()

    assert app.server.broadcast.calls == [(("KICK", "player1"), {})]


def test_send_command_without_a_value_sends_none():
    app = make_app(command_entry=FakeEntry("PING"))

    app.send_command()

    assert app.server.broadcast.calls == [(("PING", None), {})]


def test_send_command_blank_text_is_a_no_op():
    app = make_app(command_entry=FakeEntry("   "))

    app.send_command()

    assert app.server.broadcast.calls == []


def test_send_command_only_uses_the_first_two_words():
    app = make_app(command_entry=FakeEntry("SAY hello there world"))

    app.send_command()

    assert app.server.broadcast.calls == [(("SAY", "hello"), {})]


# ── logging ──────────────────────────────────────────────────────────────────

def test_print_log_writes_to_the_on_screen_log_and_persists_to_the_file():
    app = make_app()

    app.print_log("hello")

    assert app.command_log.inserted == [(END, "[SERVER] => hello\n")]
    assert app.command_log.state == "disabled"  # re-disabled after inserting
    assert len(app.command_log.yview_calls) == 1
    assert len(app._log_file.written) == 1
    assert "[SERVER] => hello" in app._log_file.written[0]
    assert app._log_file.flush_calls == 1


def test_clear_log_wipes_only_the_on_screen_log():
    app = make_app()
    app.print_log("one")

    app.clear_log()

    assert app.command_log.deleted == [("1.0", END)]
    assert app.command_log.state == "disabled"
    assert len(app._log_file.written) == 1  # the file log is untouched


# ── exit ─────────────────────────────────────────────────────────────────────

def test_exit_closes_the_server_and_the_log_file_then_destroys_the_window():
    app = make_app()

    app.exit()

    assert len(app.server.close.calls) == 1
    assert app._log_file.closed is True
    assert len(app.destroy.calls) == 1


# ── Grip (draggable-window math) ─────────────────────────────────────────────

class FakeTkWidget:
    def __init__(self, pointer=(0, 0), geometry="300x200+100+50"):
        self._pointer = pointer
        self._geometry = geometry
        self.geometry_calls = []
        self.bind_calls = []
        self.unbind_calls = []

    def winfo_pointerxy(self):
        return self._pointer

    def winfo_toplevel(self):
        return self

    def geometry(self, value=None):
        if value is None:
            return self._geometry
        self.geometry_calls.append(value)
        self._geometry = value

    def bind(self, sequence, func):
        self.bind_calls.append((sequence, func))

    def unbind(self, sequence):
        self.unbind_calls.append(sequence)


def make_grip(disable=None, releasecmd=None):
    parent = FakeTkWidget()
    grip = Grip(parent, disable=disable, releasecmd=releasecmd)
    return grip, parent


def test_grip_construction_binds_press_and_release_and_lowercases_disable():
    grip, parent = make_grip(disable="X")

    assert grip.disable == "x"
    assert [seq for seq, _ in parent.bind_calls] == ["<Button-1>", "<ButtonRelease-1>"]


def test_grip_relative_position_captures_the_press_offset():
    grip, parent = make_grip()
    parent._pointer = (150, 80)
    parent._geometry = "300x200+100+50"

    grip.relative_position(None)

    assert (grip.ori_x, grip.ori_y) == (100, 50)
    assert (grip.rel_x, grip.rel_y) == (50, 30)
    assert ("<Motion>", grip.drag_wid) in parent.bind_calls


def test_grip_drag_wid_moves_the_window_by_the_captured_offset():
    grip, parent = make_grip()
    parent._pointer = (150, 80)
    parent._geometry = "300x200+100+50"
    grip.relative_position(None)

    parent._pointer = (170, 90)
    grip.drag_wid(None)

    assert parent.geometry_calls[-1] == "+120+60"


def test_grip_drag_wid_locks_the_x_axis_when_disabled():
    grip, parent = make_grip(disable="x")
    parent._pointer = (150, 80)
    parent._geometry = "300x200+100+50"
    grip.relative_position(None)

    parent._pointer = (170, 90)
    grip.drag_wid(None)

    assert parent.geometry_calls[-1] == "+100+60"  # x pinned to ori_x


def test_grip_drag_wid_locks_the_y_axis_when_disabled():
    grip, parent = make_grip(disable="y")
    parent._pointer = (150, 80)
    parent._geometry = "300x200+100+50"
    grip.relative_position(None)

    parent._pointer = (170, 90)
    grip.drag_wid(None)

    assert parent.geometry_calls[-1] == "+120+50"  # y pinned to ori_y


def test_grip_drag_unbind_unbinds_motion_and_calls_the_release_callback():
    release = Spy()
    grip, parent = make_grip(releasecmd=release)

    grip.drag_unbind(None)

    assert parent.unbind_calls == ["<Motion>"]
    assert len(release.calls) == 1


def test_grip_drag_unbind_without_a_release_callback_does_not_raise():
    grip, parent = make_grip(releasecmd=None)

    grip.drag_unbind(None)  # must not raise

    assert parent.unbind_calls == ["<Motion>"]
