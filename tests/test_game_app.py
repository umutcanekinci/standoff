"""Game (app/game.py) -- constructing a real Game() needs the full asset/
audio/client/threading stack for no benefit here (same reasoning as every
other project's app-level test suite this session). These build a bare Game
instance via object.__new__(Game), which skips __init__ entirely, then
attach only what the method under test touches.
"""
from types import SimpleNamespace

import pygame
import pytest

from app.game import Game
from net.commands import Command
from pygamine import Application
from util.constants import Mode


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeClient:
    def __init__(self, is_connected=True):
        self.is_connected = is_connected
        self.sent = []
        self.disconnect_calls = 0

    def send(self, command, value=None):
        self.sent.append((command, value))

    def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False


class FakeLobby:
    def __init__(self):
        self.calls = []
        self.panel_manager = SimpleNamespace(current_panel="main_menu")

    def open_panel(self, tab):
        self.calls.append(("open_panel", tab))
        self.panel_manager.current_panel = tab

    def update_player_count(self, value):
        self.calls.append(("update_player_count", value))

    def show_room_list(self, value):
        self.calls.append(("show_room_list", value))

    def update_room(self):
        self.calls.append(("update_room",))

    def reflow(self):
        self.calls.append(("reflow",))

    def handle_back(self):
        self.calls.append(("handle_back",))


class FakePlayer:
    def __init__(self):
        self.shoot_calls = 0

    def shoot(self):
        self.shoot_calls += 1


class FakeGameplay:
    def __init__(self):
        self.calls = []
        self._player = FakePlayer()

    def update_player_position(self, *a):
        self.calls.append(("update_player_position", a))

    def update_player_angle(self, *a):
        self.calls.append(("update_player_angle", a))

    def set_player_alive(self, *a):
        self.calls.append(("set_player_alive", a))

    def spawn_mob(self, value):
        self.calls.append(("spawn_mob", value))

    def update_mobs(self, value):
        self.calls.append(("update_mobs", value))

    def kill_mob(self, value):
        self.calls.append(("kill_mob", value))

    def remove_player(self, value):
        self.calls.append(("remove_player", value))

    @property
    def players(self):
        return SimpleNamespace(get_player_with_id=lambda pid: self._player if pid == 1 else None)


def make_game(**overrides):
    game = object.__new__(Game)
    game.client = FakeClient()
    game.lobby = FakeLobby()
    game.gameplay = None
    game.active_scene = game.lobby
    game.mode = None
    game.player_info = None
    game.server = None
    game._debug_text = ""
    game._message_handlers = {
        Command.SET_PLAYER_COUNT: lambda v: game.lobby.update_player_count(v),
        Command.LIST_ROOMS: game._on_list_rooms,
        Command.UPDATE_ROOM: game._on_update_room,
        Command.LEAVE_ROOM: game._on_leave_room,
        Command.START_GAME: game._on_start_game,
        Command.UPDATE_PLAYER: game._on_update_player,
        Command.SHOOT: game._on_shoot,
        Command.SPAWN: game._on_spawn,
        Command.UPDATE_MOBS: game._on_update_mobs,
        Command.KILL_MOB: game._on_kill_mob,
        Command.DISCONNECT: game._on_disconnect_message,
    }
    for key, value in overrides.items():
        setattr(game, key, value)
    return game


# ── properties ───────────────────────────────────────────────────────────────

def test_is_game_started_true_only_when_the_gameplay_scene_is_active():
    game = make_game()
    assert game.is_game_started is False

    gameplay = FakeGameplay()
    game.gameplay = gameplay
    game.active_scene = gameplay
    assert game.is_game_started is True

    game.active_scene = game.lobby  # gameplay exists but isn't active (e.g. mid-teardown)
    assert game.is_game_started is False


# ── settings ─────────────────────────────────────────────────────────────────

def test_save_settings_merges_window_and_audio_settings():
    game = make_game()
    game.window_settings = lambda: {"window_mode": "windowed"}
    game.audio = SimpleNamespace(sfx_volume=lambda: 0.4, music_volume=lambda: 0.6)
    game.settings_store = SimpleNamespace(save=Spy())

    game._save_settings()

    (saved,), _ = game.settings_store.save.calls[0]
    assert saved == {"window_mode": "windowed", "sfx_volume": 0.4, "music_volume": 0.6}


def test_reset_settings_restores_defaults_and_saves():
    game = make_game()
    game.reset_window_settings = Spy()
    game.audio = SimpleNamespace(set_sfx_volume=Spy(), set_music_volume=Spy())
    game._save_settings = Spy()

    game._reset_settings()

    assert len(game.reset_window_settings.calls) == 1
    assert game.audio.set_sfx_volume.calls == [((1.0,), {})]
    assert game.audio.set_music_volume.calls == [((1.0,), {})]
    assert len(game._save_settings.calls) == 1


def test_debug_log_stores_the_latest_message():
    game = make_game()

    game.debug_log("hello")

    assert game._debug_text == "hello"


# ── connection lifecycle ─────────────────────────────────────────────────────

def test_connect_to_server_disconnects_the_old_client_first():
    game = make_game()
    old_client = game.client
    game._connect = Spy()

    game.connect_to_server("1.2.3.4", 9999)

    assert old_client.disconnect_calls == 1
    assert game._connect.calls == [((("1.2.3.4", 9999),), {})]


def test_connect_to_server_with_no_existing_client_does_not_raise():
    game = make_game()
    del game.client
    game._connect = Spy()

    game.connect_to_server("1.2.3.4", 9999)

    assert len(game._connect.calls) == 1


def test_stop_hosting_closes_and_clears_the_server():
    game = make_game()
    server = SimpleNamespace(close=Spy())
    game.server = server

    game.stop_hosting()

    assert len(server.close.calls) == 1
    assert game.server is None


def test_stop_hosting_with_no_server_is_a_no_op():
    game = make_game(server=None)
    game.stop_hosting()  # must not raise
    assert game.server is None


def test_host_server_is_idempotent_while_already_running():
    game = make_game()
    running_server = SimpleNamespace(is_running=True)
    game.server = running_server

    result = game.host_server(port=12345)

    assert result is True
    assert game.server is running_server  # untouched, no new server spun up


def test_disconnect_from_server_notifies_and_tears_down(monkeypatch):
    game = make_game()
    game.client.is_connected = True
    game.stop_hosting = Spy()

    game.disconnect_from_server()

    assert (Command.DISCONNECT, None) in game.client.sent
    assert game.client.disconnect_calls == 1
    assert len(game.stop_hosting.calls) == 1


def test_disconnect_from_server_skips_the_message_when_not_connected():
    game = make_game()
    game.client.is_connected = False
    game.stop_hosting = Spy()

    game.disconnect_from_server()

    assert game.client.sent == []
    assert game.client.disconnect_calls == 1


# ── server-lost handling ─────────────────────────────────────────────────────

def test_on_server_lost_ignores_a_stale_client():
    game = make_game()
    other_client = FakeClient()

    game._on_server_lost(other_client)  # not game.client -- ignored

    assert game.lobby.calls == []


def test_on_server_lost_ignores_our_own_host_teardown():
    game = make_game()
    game.server = SimpleNamespace()  # we're still "hosting" -- this is our own exit()

    game._on_server_lost(game.client)

    assert game.lobby.calls == []


def test_on_server_lost_leaves_the_match_when_mid_game():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay
    game.active_scene = gameplay
    game.leave_match = Spy()

    game._on_server_lost(game.client)

    assert game.leave_match.calls == [((), {"to_lobby": True})]


def test_on_server_lost_does_nothing_from_the_lobby():
    game = make_game()
    game.leave_match = Spy()

    game._on_server_lost(game.client)

    assert game.leave_match.calls == []


# ── leave_match ──────────────────────────────────────────────────────────────

def test_leave_match_offline_goes_straight_to_the_main_menu():
    game = make_game(mode=Mode.OFFLINE)
    gameplay = FakeGameplay()
    game.gameplay, game.active_scene = gameplay, gameplay

    game.leave_match(to_lobby=True)

    assert game.gameplay is None
    assert game.active_scene is game.lobby
    assert ("open_panel", "main_menu") in game.lobby.calls


def test_leave_match_online_to_lobby_sends_leave_room_and_opens_server_lobby():
    game = make_game(mode=Mode.ONLINE)
    game.client.is_connected = True
    gameplay = FakeGameplay()
    game.gameplay, game.active_scene = gameplay, gameplay

    game.leave_match(to_lobby=True)

    assert (Command.LEAVE_ROOM, None) in game.client.sent
    assert ("open_panel", "server_lobby_menu") in game.lobby.calls
    assert ("open_panel", "main_menu") not in game.lobby.calls


def test_leave_match_online_not_to_lobby_goes_to_the_main_menu():
    game = make_game(mode=Mode.ONLINE)
    game.client.is_connected = True
    gameplay = FakeGameplay()
    game.gameplay, game.active_scene = gameplay, gameplay

    game.leave_match(to_lobby=False)

    assert ("open_panel", "main_menu") in game.lobby.calls


def test_leave_match_online_but_disconnected_goes_to_the_main_menu():
    game = make_game(mode=Mode.ONLINE)
    game.client.is_connected = False
    gameplay = FakeGameplay()
    game.gameplay, game.active_scene = gameplay, gameplay

    game.leave_match(to_lobby=True)

    assert game.client.sent == []
    assert ("open_panel", "main_menu") in game.lobby.calls


# ── start ────────────────────────────────────────────────────────────────────

def test_start_builds_and_activates_a_gameplay_scene(monkeypatch):
    game = make_game()
    fake_scene = FakeGameplay()
    monkeypatch.setattr("app.game.GameplayScene", lambda g: fake_scene)

    game.start()

    assert game.gameplay is fake_scene
    assert game.active_scene is fake_scene


# ── message dispatch ─────────────────────────────────────────────────────────

def test_get_data_ignores_falsy_payloads():
    game = make_game()
    game.get_data(None)
    game.get_data({})
    assert game.lobby.calls == []


def test_get_data_dispatches_to_the_matching_handler():
    game = make_game()

    game.get_data({"command": Command.LIST_ROOMS, "value": ["room1"]})

    assert ("show_room_list", ["room1"]) in game.lobby.calls


def test_get_data_unknown_command_is_ignored():
    game = make_game()
    game.get_data({"command": "!NOT_A_REAL_COMMAND", "value": 1})  # must not raise


def test_on_list_rooms_defaults_to_an_empty_list():
    game = make_game()
    game._on_list_rooms(None)
    assert ("show_room_list", []) in game.lobby.calls


def test_on_update_room_stores_player_info_and_refreshes():
    game = make_game()
    info = object()

    game._on_update_room(info)

    assert game.player_info is info
    assert ("update_room",) in game.lobby.calls


def test_on_update_room_ignores_a_falsy_value():
    game = make_game()
    game.player_info = "existing"

    game._on_update_room(None)

    assert game.player_info == "existing"
    assert game.lobby.calls == []


def test_on_start_game_calls_start(monkeypatch):
    game = make_game()
    game.start = Spy()

    game._on_start_game(None)

    assert len(game.start.calls) == 1


def test_on_leave_room_reopens_the_hub_only_from_room_menu():
    game = make_game()
    game.lobby.panel_manager.current_panel = "room_menu"

    game._on_leave_room(None)

    assert ("open_panel", "server_lobby_menu") in game.lobby.calls


def test_on_leave_room_does_nothing_when_already_navigated_elsewhere():
    game = make_game()
    game.lobby.panel_manager.current_panel = "main_menu"

    game._on_leave_room(None)

    assert game.lobby.calls == []


def test_on_update_player_forwards_position_angle_and_alive(monkeypatch):
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_update_player([1, (10, 20), 45, False])

    assert ("update_player_position", (1, (10, 20))) in gameplay.calls
    assert ("update_player_angle", (1, 45)) in gameplay.calls
    assert ("set_player_alive", (1, False)) in gameplay.calls


def test_on_update_player_defaults_alive_true_when_omitted():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_update_player([1, (10, 20), 45])

    assert ("set_player_alive", (1, True)) in gameplay.calls


def test_on_update_player_is_a_no_op_outside_a_match():
    game = make_game()
    game.gameplay = None
    game._on_update_player([1, (10, 20), 45])  # must not raise


def test_on_shoot_calls_shoot_on_the_matching_player():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_shoot(1)

    assert gameplay._player.shoot_calls == 1


def test_on_shoot_ignores_an_unknown_player_id():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_shoot(999)  # must not raise

    assert gameplay._player.shoot_calls == 0


def test_on_spawn_update_mobs_kill_mob_forward_when_in_a_match():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_spawn("mob1")
    game._on_update_mobs(["mob1", "mob2"])
    game._on_kill_mob("mob1")

    assert ("spawn_mob", "mob1") in gameplay.calls
    assert ("update_mobs", ["mob1", "mob2"]) in gameplay.calls
    assert ("kill_mob", "mob1") in gameplay.calls


def test_on_spawn_update_mobs_kill_mob_are_no_ops_outside_a_match():
    game = make_game()
    game.gameplay = None
    game._on_spawn("mob1")
    game._on_update_mobs([])
    game._on_kill_mob("mob1")  # none of these should raise


def test_on_disconnect_message_for_us_disconnects_and_exits():
    game = make_game()
    game.player_info = SimpleNamespace(id=7)
    game.exit = Spy()

    game._on_disconnect_message(7)

    assert game.client.disconnect_calls == 1
    assert len(game.exit.calls) == 1


def test_on_disconnect_message_for_someone_else_removes_that_player():
    game = make_game()
    game.player_info = SimpleNamespace(id=7)
    gameplay = FakeGameplay()
    game.gameplay = gameplay

    game._on_disconnect_message(99)

    assert ("remove_player", 99) in gameplay.calls
    assert game.client.disconnect_calls == 0


# ── canvas resize / core events ──────────────────────────────────────────────

def test_on_canvas_resized_before_lobby_exists_is_a_no_op():
    game = object.__new__(Game)  # deliberately no `lobby` attribute yet

    game.on_canvas_resized((800, 600))  # must not raise


def test_on_canvas_resized_reflows_the_lobby():
    game = make_game()

    game.on_canvas_resized((800, 600))

    assert ("reflow",) in game.lobby.calls


@pytest.mark.parametrize("event", [
    pygame.event.Event(pygame.QUIT),
    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
])
def test_core_event_quit_or_escape_triggers_back_navigation(event):
    game = make_game()
    game._handle_back = Spy()

    game._handle_core_event(event)

    assert len(game._handle_back.calls) == 1


def test_core_event_f1_toggles_debug_mode():
    game = make_game()
    game._is_in_debug_mode = False

    game._handle_core_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))

    assert game._is_in_debug_mode is True


def test_core_event_f11_cycles_window_mode():
    game = make_game()
    game.cycle_window_mode = Spy()

    game._handle_core_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))

    assert len(game.cycle_window_mode.calls) == 1


def test_handle_back_leaves_the_match_when_started():
    game = make_game()
    gameplay = FakeGameplay()
    game.gameplay, game.active_scene = gameplay, gameplay
    game.leave_match = Spy()

    game._handle_back()

    assert game.leave_match.calls == [((), {"to_lobby": True})]


def test_handle_back_delegates_to_the_lobby_otherwise():
    game = make_game()

    game._handle_back()

    assert ("handle_back",) in game.lobby.calls


# ── loop dispatch ────────────────────────────────────────────────────────────

def test_handle_event_update_draw_dispatch_to_the_active_scene():
    game = make_game()
    scene = SimpleNamespace(handle_event=Spy(), update=Spy(), draw=Spy())
    game.active_scene = scene

    event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0))
    game.handle_event(event)
    game.update()
    game.draw()

    assert scene.handle_event.calls == [((event,), {})]
    assert len(scene.update.calls) == 1
    assert len(scene.draw.calls) == 1


# ── exit ─────────────────────────────────────────────────────────────────────

def test_exit_notifies_the_server_and_tears_everything_down(monkeypatch):
    game = make_game()
    game._save_settings = Spy()
    game.stop_hosting = Spy()
    game.client.is_connected = True
    base_exit = Spy()
    monkeypatch.setattr(Application, "exit", lambda self: base_exit())

    game.exit()

    assert len(game._save_settings.calls) == 1
    assert (Command.DISCONNECT, None) in game.client.sent
    assert game.client.disconnect_calls == 1
    assert len(game.stop_hosting.calls) == 1
    assert len(base_exit.calls) == 1


def test_exit_skips_the_disconnect_message_when_not_connected(monkeypatch):
    game = make_game()
    game._save_settings = Spy()
    game.stop_hosting = Spy()
    game.client.is_connected = False
    monkeypatch.setattr(Application, "exit", lambda self: None)

    game.exit()

    assert game.client.sent == []
    assert game.client.disconnect_calls == 1
