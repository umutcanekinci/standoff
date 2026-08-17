"""LobbyScene (app/lobby_scene.py) -- constructing a real instance needs the
full YAML panel/asset stack (_load_panels/_build_dynamic_objects) for no
benefit here (same reasoning as every other project's app-level test suite
this session). These build a bare instance via object.__new__(LobbyScene),
which skips __init__ entirely, then attach small fakes for game/panels/
buttons/text so the menu-navigation and network-message logic -- the actual
bug surface -- can be tested directly.
"""
from types import SimpleNamespace

import pygame
import pytest

from app.lobby_scene import BROWSER_ROWS, LobbyScene
from net.commands import Command
from net.player_info import PlayerInfo
from ui.widgets import InputObject
from util.constants import CHARACTER_LIST, MAX_ROOM_SIZE, Green, Mode, Red, White, Yellow


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeButton:
    def __init__(self):
        self.clicked = False
        self.active = True
        self.enabled = True
        self.label = None

    def is_clicked(self, event, mouse_pos):
        return self.clicked

    def set_enabled(self, value):
        self.enabled = value

    def set_label(self, value):
        self.label = value


class FakeText:
    def __init__(self):
        self.text = None
        self.color = None
        self.active = True

    def set_text(self, value):
        self.text = value

    def set_color(self, value):
        self.color = value


class FakeInput:
    def __init__(self, text=""):
        self.text = text

    def set_text(self, value):
        self.text = value


class FakeSlider:
    def __init__(self):
        self.value = None
        self.on_change = None

    def set_value(self, value):
        self.value = value


class FakePanelManager(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_panel = "main_menu"

    def keys(self):
        return dict.keys(self)

    def update(self):
        pass

    def draw(self, surface):
        pass

    def handle_event(self, event, pos):
        pass


def make_panels():
    common = lambda: {"player_count_text": FakeText()}

    def merged(extra):
        d = common()
        d.update(extra)
        return d

    return FakePanelManager({
        "main_menu": merged({"play": FakeButton(), "settings": FakeButton(), "exit": FakeButton()}),
        "settings_menu": merged({
            "back": FakeButton(), "reset": FakeButton(),
            "window_mode_back": FakeButton(), "window_mode_next": FakeButton(),
            "window_size_back": FakeButton(), "window_size_next": FakeButton(),
            "sfx_volume_slider": FakeSlider(), "music_volume_slider": FakeSlider(),
            "window_mode_value": FakeText(), "window_size_value": FakeText(),
            "sfx_volume_value": FakeText(), "music_volume_value": FakeText(),
        }),
        "player_menu": merged({
            "previous": FakeButton(), "next": FakeButton(),
            "confirm": FakeButton(), "back": FakeButton(), "name_input": FakeInput(),
        }),
        "mode_menu": merged({
            "play_offline": FakeButton(), "host": FakeButton(),
            "connect": FakeButton(), "back": FakeButton(),
        }),
        "host_warning_menu": merged({"host_anyway": FakeButton(), "back": FakeButton()}),
        "server_lobby_menu": merged({
            "create_room": FakeButton(), "join_room": FakeButton(), "disconnect": FakeButton(),
        }),
        "server_menu": merged({
            "connect": FakeButton(), "back": FakeButton(),
            "ip_input": FakeInput(), "port_input": FakeInput(), "status_text": FakeText(),
        }),
        "create_room_menu": merged({"create": FakeButton(), "back": FakeButton()}),
        "connect_menu": merged({
            "join": FakeButton(), "back": FakeButton(),
            "room_id_input": FakeInput(), "status_text": FakeText(),
        }),
        "room_menu": merged({
            "action_button": FakeButton(), "leave_room": FakeButton(), "room_text": FakeText(),
        }),
    })


class FakeAudio:
    """Real read-your-writes state (not a fixed-value stub) -- the code
    under test reads sfx_volume()/music_volume() right back after calling
    set_sfx_volume()/set_music_volume(), so a stub that never changes would
    silently hide bugs in that read-after-write path."""

    def __init__(self, sfx=0.5, music=0.5):
        self._sfx = sfx
        self._music = music
        self.set_sfx_volume_calls = []
        self.set_music_volume_calls = []

    def sfx_volume(self):
        return self._sfx

    def music_volume(self):
        return self._music

    def set_sfx_volume(self, value):
        self.set_sfx_volume_calls.append(value)
        self._sfx = value

    def set_music_volume(self, value):
        self.set_music_volume_calls.append(value)
        self._music = value


class FakeGame:
    def __init__(self):
        self.mouse = SimpleNamespace(position=(0, 0))
        self.client = SimpleNamespace(send=Spy(), is_connected=False)
        self.sounds = {}
        self.mode = None
        self.player_info = None
        self.audio = FakeAudio()
        self.size = (1920, 1080)
        self.window = pygame.Surface((100, 100))
        self._window_mode = "windowed"
        self.resolution = (1920, 1080)
        self.cycle_window_mode = Spy()
        self.cycle_resolution = Spy()
        self._save_settings = Spy()
        self._reset_settings = Spy()
        self.exit = Spy()
        self.host_server = lambda: True
        self.connect_to_server = Spy()
        self.disconnect_from_server = Spy()
        self.start = Spy()


def make_scene(**overrides):
    scene = object.__new__(LobbyScene)
    scene.game = FakeGame()
    scene.panel_manager = make_panels()
    scene.selected_character = 0
    scene.room_action = None
    scene._connecting = False
    scene._connect_deadline = 0
    scene._auto_joined = False
    scene._text_input_on = False
    scene.character_preview = SimpleNamespace(set_base_state=Spy())
    scene.character_name_text = FakeText()
    scene.room_slots = [FakeText() for _ in range(MAX_ROOM_SIZE)]
    scene.room_action_button = FakeButton()
    scene.room_rows = [FakeButton() for _ in range(BROWSER_ROWS)]
    scene.room_row_ids = [None] * BROWSER_ROWS
    scene.handlers = {
        "main_menu": scene._handle_main_menu,
        "player_menu": scene._handle_player_menu,
        "mode_menu": scene._handle_mode_menu,
        "host_warning_menu": scene._handle_host_warning_menu,
        "server_lobby_menu": scene._handle_server_lobby_menu,
        "create_room_menu": scene._handle_create_room_menu,
        "connect_menu": scene._handle_connect_menu,
        "server_menu": scene._handle_server_menu,
        "room_menu": scene._handle_room_menu,
        "settings_menu": scene._handle_settings_menu,
    }
    for key, value in overrides.items():
        setattr(scene, key, value)
    return scene


def click_up():
    return pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)


# ── pure helpers ─────────────────────────────────────────────────────────────

def test_display_name_title_cases_underscored_names():
    assert LobbyScene._display_name("man_blue") == "Man Blue"
    assert LobbyScene._display_name("hitman") == "Hitman"


def test_refresh_character_updates_preview_and_label():
    scene = make_scene()
    scene.selected_character = 1  # "man_blue"

    scene._refresh_character()

    scene.character_preview.set_base_state.calls == [(("man_blue",), {})]
    assert scene.character_name_text.text == "Man Blue"


# ── open_panel ───────────────────────────────────────────────────────────────

def test_open_panel_sets_the_current_panel():
    scene = make_scene()
    scene.open_panel("player_menu")
    assert scene.panel_manager.current_panel == "player_menu"


def test_open_panel_settings_menu_binds_the_live_settings_ui():
    scene = make_scene()
    scene.open_panel("settings_menu")
    assert scene.panel_manager["settings_menu"]["sfx_volume_value"].text == "50%"


def test_open_panel_server_menu_shows_connected_when_already_connected():
    scene = make_scene()
    scene.game.client.is_connected = True

    scene.open_panel("server_menu")

    status = scene.panel_manager["server_menu"]["status_text"]
    assert (status.text, status.color) == ("Connected", Green)


def test_open_panel_server_menu_shows_blank_when_not_connected():
    scene = make_scene()
    scene.game.client.is_connected = False

    scene.open_panel("server_menu")

    status = scene.panel_manager["server_menu"]["status_text"]
    assert (status.text, status.color) == ("", White)


def test_open_panel_connect_menu_resets_the_browser_and_requests_the_list():
    scene = make_scene()
    scene.room_rows[0].active = True
    scene._auto_joined = True

    scene.open_panel("connect_menu")

    assert scene._auto_joined is False
    assert all(not row.active for row in scene.room_rows)
    assert scene.game.client.send.calls[0][0] == (Command.LIST_ROOMS,)


# ── loop hooks ───────────────────────────────────────────────────────────────

def test_handle_event_dispatches_to_the_current_panels_handler():
    scene = make_scene()
    scene.panel_manager.current_panel = "main_menu"
    scene.panel_manager["main_menu"]["play"].clicked = True

    scene.handle_event(click_up())

    assert scene.panel_manager.current_panel == "player_menu"


def test_update_polls_connection_only_on_server_or_mode_menu():
    scene = make_scene()
    scene._poll_connection = Spy()

    scene.panel_manager.current_panel = "main_menu"
    scene.update()
    assert scene._poll_connection.calls == []

    scene.panel_manager.current_panel = "server_menu"
    scene.update()
    assert len(scene._poll_connection.calls) == 1

    scene.panel_manager.current_panel = "mode_menu"
    scene.update()
    assert len(scene._poll_connection.calls) == 2


def test_sync_soft_keyboard_starts_and_stops_text_input(monkeypatch):
    scene = make_scene()
    field = InputObject(parent=None, pos=(0, 0), size=(50, 20))
    scene.panel_manager["main_menu"]["field"] = field
    started, stopped = [], []
    monkeypatch.setattr(pygame.key, "start_text_input", lambda: started.append(True))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: stopped.append(True))
    monkeypatch.setattr(pygame.key, "set_text_input_rect", lambda rect: None)

    field.editing = True
    scene._sync_soft_keyboard()
    assert scene._text_input_on is True
    assert started == [True]

    field.editing = False
    scene._sync_soft_keyboard()
    assert scene._text_input_on is False
    assert stopped == [True]


def test_draw_fills_the_window_and_draws_the_panels():
    scene = make_scene()
    scene.panel_manager.draw = Spy()

    scene.draw()

    assert len(scene.panel_manager.draw.calls) == 1


# ── back navigation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("panel,expected", [
    ("player_menu", "main_menu"),
    ("mode_menu", "player_menu"),
    ("host_warning_menu", "mode_menu"),
    ("server_menu", "mode_menu"),
])
def test_handle_back_simple_navigation(panel, expected):
    scene = make_scene()
    scene.panel_manager.current_panel = panel

    scene.handle_back()

    assert scene.panel_manager.current_panel == expected


def test_handle_back_from_server_lobby_disconnects():
    scene = make_scene()
    scene.panel_manager.current_panel = "server_lobby_menu"

    scene.handle_back()

    assert len(scene.game.disconnect_from_server.calls) == 1
    assert scene.panel_manager.current_panel == "mode_menu"


def test_handle_back_from_connect_menu_returns_to_the_hub():
    scene = make_scene()
    scene.panel_manager.current_panel = "connect_menu"

    scene.handle_back()

    assert scene.panel_manager.current_panel == "server_lobby_menu"


def test_handle_back_from_create_room_depends_on_mode():
    scene = make_scene()
    scene.panel_manager.current_panel = "create_room_menu"
    scene.game.mode = Mode.ONLINE
    scene.handle_back()
    assert scene.panel_manager.current_panel == "server_lobby_menu"

    scene2 = make_scene()
    scene2.panel_manager.current_panel = "create_room_menu"
    scene2.game.mode = Mode.OFFLINE
    scene2.handle_back()
    assert scene2.panel_manager.current_panel == "mode_menu"


def test_handle_back_from_settings_saves_first():
    scene = make_scene()
    scene.panel_manager.current_panel = "settings_menu"

    scene.handle_back()

    assert len(scene.game._save_settings.calls) == 1
    assert scene.panel_manager.current_panel == "main_menu"


def test_handle_back_from_main_menu_exits():
    scene = make_scene()
    scene.panel_manager.current_panel = "main_menu"

    scene.handle_back()

    assert len(scene.game.exit.calls) == 1


# ── main menu / settings ─────────────────────────────────────────────────────

def test_main_menu_play_settings_exit():
    scene = make_scene()
    scene.panel_manager["main_menu"]["play"].clicked = True
    scene._handle_main_menu(click_up())
    assert scene.panel_manager.current_panel == "player_menu"

    scene2 = make_scene()
    scene2.panel_manager["main_menu"]["settings"].clicked = True
    scene2._handle_main_menu(click_up())
    assert scene2.panel_manager.current_panel == "settings_menu"

    scene3 = make_scene()
    scene3.panel_manager["main_menu"]["exit"].clicked = True
    scene3._handle_main_menu(click_up())
    assert len(scene3.game.exit.calls) == 1


def test_settings_menu_back_saves_and_returns():
    scene = make_scene()
    scene.panel_manager["settings_menu"]["back"].clicked = True

    scene._handle_settings_menu(click_up())

    assert len(scene.game._save_settings.calls) == 1
    assert scene.panel_manager.current_panel == "main_menu"


def test_settings_menu_reset_rebinds_the_ui():
    scene = make_scene()
    scene.panel_manager["settings_menu"]["reset"].clicked = True

    scene._handle_settings_menu(click_up())

    assert len(scene.game._reset_settings.calls) == 1
    assert scene.panel_manager["settings_menu"]["sfx_volume_value"].text == "50%"


def test_settings_menu_window_mode_and_size_buttons():
    scene = make_scene()
    scene.panel_manager["settings_menu"]["window_mode_back"].clicked = True
    scene._handle_settings_menu(click_up())
    assert scene.game.cycle_window_mode.calls == [((-1,), {})]

    scene2 = make_scene()
    scene2.panel_manager["settings_menu"]["window_size_next"].clicked = True
    scene2._handle_settings_menu(click_up())
    assert scene2.game.cycle_resolution.calls == [((1,), {})]

    scene3 = make_scene()
    scene3.panel_manager["settings_menu"]["window_mode_next"].clicked = True
    scene3._handle_settings_menu(click_up())
    assert scene3.game.cycle_window_mode.calls == [((1,), {})]

    scene4 = make_scene()
    scene4.panel_manager["settings_menu"]["window_size_back"].clicked = True
    scene4._handle_settings_menu(click_up())
    assert scene4.game.cycle_resolution.calls == [((-1,), {})]


def test_on_music_volume_changed_updates_audio_and_label():
    scene = make_scene()

    scene._on_music_volume_changed(0.3)

    assert scene.game.audio.set_music_volume_calls == [0.3]
    assert scene.panel_manager["settings_menu"]["music_volume_value"].text == "30%"


def test_bind_settings_ui_wires_slider_callbacks():
    scene = make_scene()

    scene._bind_settings_ui()

    panel = scene.panel_manager["settings_menu"]
    assert panel["sfx_volume_slider"].value == 0.5
    panel["sfx_volume_slider"].on_change(0.8)
    assert scene.game.audio.set_sfx_volume_calls == [0.8]
    assert panel["sfx_volume_value"].text == "80%"


def test_refresh_window_mode_and_size_labels():
    scene = make_scene()
    scene.game._window_mode = "fullscreen"
    scene.game.resolution = (1280, 720)

    scene._refresh_window_mode_label()
    scene._refresh_window_size_label()

    assert scene.panel_manager["settings_menu"]["window_mode_value"].text == "FULLSCREEN"
    assert scene.panel_manager["settings_menu"]["window_size_value"].text == "1280x720"


# ── player menu (character select) ──────────────────────────────────────────

def test_player_menu_previous_and_next_clamp_at_the_ends():
    scene = make_scene()
    scene.selected_character = 0
    scene.panel_manager["player_menu"]["previous"].clicked = True
    scene._handle_player_menu(click_up())
    assert scene.selected_character == 0  # already at the start

    scene.panel_manager["player_menu"]["previous"].clicked = False
    scene.panel_manager["player_menu"]["next"].clicked = True
    scene._handle_player_menu(click_up())
    assert scene.selected_character == 1

    scene.panel_manager["player_menu"]["next"].clicked = False
    scene.panel_manager["player_menu"]["previous"].clicked = True
    scene._handle_player_menu(click_up())
    assert scene.selected_character == 0  # back down from 1


def test_player_menu_next_clamps_at_the_last_character():
    scene = make_scene()
    scene.selected_character = len(CHARACTER_LIST) - 1
    scene.panel_manager["player_menu"]["next"].clicked = True

    scene._handle_player_menu(click_up())

    assert scene.selected_character == len(CHARACTER_LIST) - 1  # already at the end


def test_player_menu_confirm_sets_the_player_and_advances():
    scene = make_scene()
    scene.selected_character = 2
    scene.panel_manager["player_menu"]["name_input"].text = "Alice"
    scene.panel_manager["player_menu"]["confirm"].clicked = True

    scene._handle_player_menu(click_up())

    assert scene.game.player_info.name == "Alice"
    assert scene.game.player_info.character_name == CHARACTER_LIST[2]
    assert scene.panel_manager.current_panel == "mode_menu"


def test_player_menu_back_returns_to_main_menu():
    scene = make_scene()
    scene.panel_manager["player_menu"]["back"].clicked = True

    scene._handle_player_menu(click_up())

    assert scene.panel_manager.current_panel == "main_menu"


# ── mode menu ────────────────────────────────────────────────────────────────

def test_mode_menu_play_offline_goes_straight_to_room_creation():
    scene = make_scene()
    scene.panel_manager["mode_menu"]["play_offline"].clicked = True

    scene._handle_mode_menu(click_up())

    assert scene.game.mode == Mode.OFFLINE
    assert scene.panel_manager.current_panel == "create_room_menu"


def test_mode_menu_host_starts_hosting_on_desktop(monkeypatch):
    scene = make_scene()
    monkeypatch.setattr("app.lobby_scene.is_android", lambda: False)
    scene.panel_manager["mode_menu"]["host"].clicked = True

    scene._handle_mode_menu(click_up())

    assert scene._connecting is True  # _host_game -> _begin_connect armed the poll


def test_mode_menu_host_warns_first_on_android(monkeypatch):
    scene = make_scene()
    monkeypatch.setattr("app.lobby_scene.is_android", lambda: True)
    scene.panel_manager["mode_menu"]["host"].clicked = True

    scene._handle_mode_menu(click_up())

    assert scene.panel_manager.current_panel == "host_warning_menu"
    assert scene._connecting is False  # host_server() never actually called


def test_mode_menu_connect_opens_server_menu():
    scene = make_scene()
    scene.panel_manager["mode_menu"]["connect"].clicked = True

    scene._handle_mode_menu(click_up())

    assert scene.panel_manager.current_panel == "server_menu"


def test_mode_menu_back_returns_to_player_menu():
    scene = make_scene()
    scene.panel_manager["mode_menu"]["back"].clicked = True

    scene._handle_mode_menu(click_up())

    assert scene.panel_manager.current_panel == "player_menu"


def test_host_warning_menu_host_anyway_hosts():
    scene = make_scene()
    scene.panel_manager["host_warning_menu"]["host_anyway"].clicked = True

    scene._handle_host_warning_menu(click_up())

    assert scene._connecting is True


def test_host_warning_menu_back_returns_to_mode_menu():
    scene = make_scene()
    scene.panel_manager["host_warning_menu"]["back"].clicked = True

    scene._handle_host_warning_menu(click_up())

    assert scene.panel_manager.current_panel == "mode_menu"


# ── server lobby ─────────────────────────────────────────────────────────────

def test_server_lobby_menu_create_and_join_navigate():
    scene = make_scene()
    scene.panel_manager["server_lobby_menu"]["create_room"].clicked = True
    scene._handle_server_lobby_menu(click_up())
    assert scene.panel_manager.current_panel == "create_room_menu"

    scene2 = make_scene()
    scene2.panel_manager["server_lobby_menu"]["join_room"].clicked = True
    scene2._handle_server_lobby_menu(click_up())
    assert scene2.panel_manager.current_panel == "connect_menu"


def test_server_lobby_menu_disconnect():
    scene = make_scene()
    scene.panel_manager["server_lobby_menu"]["disconnect"].clicked = True

    scene._handle_server_lobby_menu(click_up())

    assert len(scene.game.disconnect_from_server.calls) == 1
    assert scene.panel_manager.current_panel == "mode_menu"


# ── server (connect) menu ────────────────────────────────────────────────────

def test_server_menu_connect_uses_the_typed_address():
    scene = make_scene()
    scene.panel_manager["server_menu"]["ip_input"].text = "10.0.0.5"
    scene.panel_manager["server_menu"]["port_input"].text = "7777"
    scene.panel_manager["server_menu"]["connect"].clicked = True

    scene._handle_server_menu(click_up())

    assert scene.game.connect_to_server.calls == [(("10.0.0.5", 7777), {})]
    assert scene.game.mode == Mode.ONLINE
    assert scene._connecting is True


def test_connect_to_server_falls_back_to_defaults_on_garbage_input():
    scene = make_scene()

    scene._connect_to_server("   ", "not-a-number")

    ip, port = scene.game.connect_to_server.calls[0][0]
    assert port == 5050  # CLIENT_PORT default


def test_server_menu_back_returns_to_mode_menu():
    scene = make_scene()
    scene.panel_manager["server_menu"]["back"].clicked = True

    scene._handle_server_menu(click_up())

    assert scene.panel_manager.current_panel == "mode_menu"


def test_host_game_does_nothing_if_the_server_fails_to_bind():
    scene = make_scene()
    scene.game.host_server = lambda: False

    scene._host_game()

    assert scene._connecting is False
    assert scene.game.mode is None


def test_poll_connection_success_announces_player_and_opens_lobby(monkeypatch):
    scene = make_scene()
    scene._connecting = True
    scene.game.client.is_connected = True
    scene.game.player_info = PlayerInfo(name="Bob", character_name="hitman")

    scene._poll_connection()

    assert scene._connecting is False
    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.SET_PLAYER
    assert value == ["Bob", "hitman"]
    assert scene.panel_manager.current_panel == "server_lobby_menu"


def test_poll_connection_times_out(monkeypatch):
    scene = make_scene()
    scene._connecting = True
    scene.game.client.is_connected = False
    scene._connect_deadline = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 999_999)

    scene._poll_connection()

    assert scene._connecting is False
    status = scene.panel_manager["server_menu"]["status_text"]
    assert (status.text, status.color) == ("Could not connect", Red)


def test_poll_connection_is_a_no_op_when_not_connecting():
    scene = make_scene()
    scene._connecting = False

    scene._poll_connection()  # must not raise or send anything

    assert scene.game.client.send.calls == []


# ── create room menu ─────────────────────────────────────────────────────────

def test_create_room_menu_back_depends_on_mode():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager["create_room_menu"]["back"].clicked = True
    scene._handle_create_room_menu(click_up())
    assert scene.panel_manager.current_panel == "server_lobby_menu"

    scene2 = make_scene()
    scene2.game.mode = Mode.OFFLINE
    scene2.panel_manager["create_room_menu"]["back"].clicked = True
    scene2._handle_create_room_menu(click_up())
    assert scene2.panel_manager.current_panel == "mode_menu"


def test_create_room_online_sends_create_room(assets):
    scene = make_scene()
    scene.game.mode = Mode.ONLINE

    scene.create_room("level2")

    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.CREATE_ROOM
    map_name, base_points = value
    assert map_name == "level2"
    assert set(base_points) == {1, 2, 3, 4}


def test_create_room_offline_starts_a_local_match(assets):
    scene = make_scene()
    scene.game.mode = Mode.OFFLINE
    scene.game.player_info = PlayerInfo(name="Solo", character_name="hitman")

    scene.create_room("level2")

    assert len(scene.game.start.calls) == 1
    assert scene.game.player_info.room is not None
    assert scene.game.player_info.is_ruler is True


# ── connect menu / room browser ──────────────────────────────────────────────

def test_connect_menu_clicking_a_listed_room_joins_it():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.room_rows[0].active = True
    scene.room_rows[0].clicked = True
    scene.room_row_ids[0] = 42

    scene._handle_connect_menu(click_up())

    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.JOIN_ROOM
    assert value == 42


def test_connect_menu_join_by_id_field():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager["connect_menu"]["room_id_input"].text = "77"
    scene.panel_manager["connect_menu"]["join"].clicked = True

    scene._handle_connect_menu(click_up())

    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.JOIN_ROOM
    assert value == 77


def test_connect_menu_join_with_a_non_numeric_id_sends_zero():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager["connect_menu"]["room_id_input"].text = "abc"
    scene.panel_manager["connect_menu"]["join"].clicked = True

    scene._handle_connect_menu(click_up())

    (command, value), _ = scene.game.client.send.calls[0]
    assert value == 0


def test_connect_menu_back_returns_to_the_hub():
    scene = make_scene()
    scene.panel_manager["connect_menu"]["back"].clicked = True

    scene._handle_connect_menu(click_up())

    assert scene.panel_manager.current_panel == "server_lobby_menu"


def make_room_summary(room_id, players, size, started=False):
    return {"id": room_id, "map_name": "level2", "players": players, "size": size, "started": started}


def test_show_room_list_ignores_a_stale_reply():
    scene = make_scene()
    scene.panel_manager.current_panel = "main_menu"  # already navigated away

    scene.show_room_list([make_room_summary(1, 1, 4)])

    assert scene.room_row_ids == [None] * BROWSER_ROWS


def test_show_room_list_populates_rows_and_disables_full_ones():
    scene = make_scene()
    scene.panel_manager.current_panel = "connect_menu"

    scene.show_room_list([make_room_summary(1, 4, 4), make_room_summary(2, 1, 4, started=True)])

    assert scene.room_rows[0].active is True
    assert scene.room_rows[0].enabled is False  # full
    assert "Room 1" in scene.room_rows[0].label
    assert scene.room_row_ids[0] == 1
    assert "(in game)" in scene.room_rows[1].label
    assert scene.room_rows[2].active is False


def test_show_room_list_no_rooms_shows_a_hint():
    scene = make_scene()
    scene.panel_manager.current_panel = "connect_menu"

    scene.show_room_list([])

    status = scene.panel_manager["connect_menu"]["status_text"]
    assert "No public rooms" in status.text


def test_show_room_list_more_rooms_than_rows_reports_the_overflow():
    scene = make_scene()
    scene.panel_manager.current_panel = "connect_menu"
    rooms = [make_room_summary(i, 1, 4) for i in range(BROWSER_ROWS + 2)]

    scene.show_room_list(rooms)

    status = scene.panel_manager["connect_menu"]["status_text"]
    assert f"Showing {BROWSER_ROWS} of {BROWSER_ROWS + 2}" in status.text


def test_show_room_list_auto_joins_a_single_open_room_once():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager.current_panel = "connect_menu"

    scene.show_room_list([make_room_summary(9, 1, 4)])

    assert scene._auto_joined is True
    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.JOIN_ROOM and value == 9


def test_show_room_list_does_not_auto_join_twice():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager.current_panel = "connect_menu"
    scene.show_room_list([make_room_summary(9, 1, 4)])
    scene.game.client.send.calls.clear()

    scene.show_room_list([make_room_summary(9, 1, 4)])  # same refresh again

    assert scene.game.client.send.calls == []


def test_show_room_list_does_not_auto_join_a_full_room():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.panel_manager.current_panel = "connect_menu"

    scene.show_room_list([make_room_summary(9, 4, 4)])  # full

    assert scene._auto_joined is False
    assert scene.game.client.send.calls == []


# ── room menu ────────────────────────────────────────────────────────────────

def test_room_menu_action_button_sends_the_command_for_the_current_action():
    scene = make_scene()
    scene.room_action = "ready"
    scene.panel_manager["room_menu"]["action_button"].clicked = True

    scene._handle_room_menu(click_up())

    (command,), _ = scene.game.client.send.calls[0]
    assert command == Command.GET_READY


def test_room_menu_action_button_does_nothing_without_a_pending_action():
    scene = make_scene()
    scene.room_action = None
    scene.panel_manager["room_menu"]["action_button"].clicked = True

    scene._handle_room_menu(click_up())

    assert scene.game.client.send.calls == []


def test_room_menu_leave_room_button():
    scene = make_scene()
    scene.panel_manager["room_menu"]["leave_room"].clicked = True

    scene._handle_room_menu(click_up())

    (command,), _ = scene.game.client.send.calls[0]
    assert command == Command.LEAVE_ROOM


# ── lobby actions ────────────────────────────────────────────────────────────

def test_set_player_stores_info_and_announces_it():
    scene = make_scene()

    scene.set_player("Alice", "robot")

    assert scene.game.player_info.name == "Alice"
    assert scene.game.player_info.character_name == "robot"
    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.SET_PLAYER
    assert value == ["Alice", "robot"]


def test_join_room_only_sends_online():
    scene = make_scene()
    scene.game.mode = Mode.OFFLINE

    scene.join_room(5)

    assert scene.game.client.send.calls == []

    scene.game.mode = Mode.ONLINE
    scene.join_room(5)
    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.JOIN_ROOM and value == 5


# ── lobby state updates ──────────────────────────────────────────────────────

def test_update_player_count_writes_every_panel():
    scene = make_scene()

    scene.update_player_count(7)

    for tab in scene.panel_manager.keys():
        text = scene.panel_manager[tab]["player_count_text"]
        assert text.text == "7 Players are Online"
        assert text.color == Yellow


def test_update_room_opens_the_room_menu_and_lists_players(assets):
    scene = make_scene()
    scene.game.player_info = PlayerInfo(name="Ruler", character_name="hitman")
    room = SimpleNamespace(id=3)
    room = type("Room", (list,), {})()
    room.id = 3
    room.append(scene.game.player_info)
    scene.game.player_info.room = room
    scene.game.player_info.is_ruler = True

    scene.update_room()

    assert scene.panel_manager["room_menu"]["room_text"].text == "Room 3"
    assert scene.panel_manager.current_panel == "room_menu"
    assert scene.room_action == "start"


def test_update_room_is_a_no_op_without_a_room():
    scene = make_scene()
    scene.game.player_info = PlayerInfo(name="X", character_name="hitman")
    scene.game.player_info.room = None

    scene.update_room()  # must not raise
    assert scene.panel_manager.current_panel == "main_menu"


def test_update_players_in_room_labels_ruler_ready_and_pending():
    scene = make_scene()
    ruler = PlayerInfo(1, name="Ruler")
    ruler.is_ruler = True
    ready = PlayerInfo(2, name="Ready")
    ready.is_ready = True
    pending = PlayerInfo(3, name="Pending")
    room = [ruler, ready, pending]
    scene.game.player_info = pending  # a guest -> "join" action

    scene.update_players_in_room(room)

    assert (scene.room_slots[0].text, scene.room_slots[0].color) == ("Ruler (Ruler)", Red)
    assert (scene.room_slots[1].text, scene.room_slots[1].color) == ("Ready (Ready)", Green)
    assert (scene.room_slots[2].text, scene.room_slots[2].color) == ("Pending", White)
    assert scene.room_slots[3].active is False
    assert scene.room_action == "join"
    assert scene.room_action_button.enabled is True


def test_update_players_in_room_ruler_action_gates_on_everyone_ready():
    scene = make_scene()
    ruler = PlayerInfo(1, name="Ruler")
    ruler.is_ruler = True
    not_ready = PlayerInfo(2, name="Guest")
    scene.game.player_info = ruler

    scene.update_players_in_room([ruler, not_ready])

    assert scene.room_action == "start"
    assert scene.room_action_button.enabled is False  # not everyone is ready yet


def test_update_players_in_room_ruler_action_enabled_once_all_ready():
    scene = make_scene()
    ruler = PlayerInfo(1, name="Ruler")
    ruler.is_ruler = True
    ready_guest = PlayerInfo(2, name="Guest")
    ready_guest.is_ready = True
    scene.game.player_info = ruler

    scene.update_players_in_room([ruler, ready_guest])

    assert scene.room_action_button.enabled is True
