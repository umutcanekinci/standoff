"""GameplayScene (app/gameplay_scene.py) -- constructing a real instance
needs a real Map/tmx/assets/Player/controls stack for no benefit here (same
reasoning as every other project's app-level test suite this session).
These build a bare instance via object.__new__(GameplayScene), which skips
__init__ entirely, then attach small fakes for game/players/mobs/camera/
controls/UI so the message-routing and per-frame state-machine logic can be
tested directly.
"""
from types import SimpleNamespace

import pygame
import pytest
from pygame.math import Vector2 as Vec

from app.gameplay_scene import GameplayScene
from net.commands import Command
from util.constants import FPS, MAX_DELTA_TIME, RESPAWN_DELAY, Mode


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeButton:
    def __init__(self):
        self.enabled = True
        self.label = None
        self.clicked = False

    def set_enabled(self, value):
        self.enabled = value

    def set_label(self, value):
        self.label = value

    def is_clicked(self, event, mouse_pos):
        return self.clicked


class FakeCamera:
    def __init__(self):
        self.followed = []
        self.drawn = []

    def follow(self, rect):
        self.followed.append(rect)

    def draw(self, window, objs):
        self.drawn.append(objs)


class FakePlayer:
    def __init__(self, player_id, alive=True, is_local=False, name="P"):
        self.id = player_id
        self.alive = alive
        self.is_local = is_local
        self.name = name
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.angle = 0
        self.target_position = None
        self.is_shooting = False
        self.hp = 100
        self.max_hp = 100
        self.velocity = None
        self.delta = None
        self.knockback = None
        self.controls = None
        self.position = (0, 0)
        self.update_calls = 0
        self.shoot_calls = 0
        self.aim_calls = 0
        self.update_movement_calls = 0

    def update(self):
        self.update_calls += 1

    def shoot(self):
        self.shoot_calls += 1

    def aim(self):
        self.aim_calls += 1

    def update_movement(self):
        self.update_movement_calls += 1

    def set_alive(self, value):
        self.alive = value

    def set_hp(self, value):
        self.hp = value

    def update_position(self, position):
        self.position = position


class FakeMob:
    def __init__(self, mob_id, alive=True):
        self.id = mob_id
        self.alive = alive
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.target_position = None
        self.hp = 100
        self.velocity = None
        self.is_network = None
        self.update_calls = 0

    def update(self):
        self.update_calls += 1

    def set_hp(self, value):
        self.hp = value

    def lose_hp(self, amount):
        self.hp -= amount

    def kill(self):
        self.alive = False


class FakePlayers(list):
    def __init__(self):
        super().__init__()
        self.add_calls = []

    def get_player_with_id(self, player_id):
        return next((p for p in self if p.id == player_id), None)

    def add_player(self, info, color):
        self.add_calls.append((info, color))
        player = FakePlayer(info.id, name=getattr(info, "name", ""))
        self.append(player)
        return player


class FakeMobs(list):
    def get_mob_from_id(self, mob_id):
        return next((m for m in self if m.id == mob_id), None)

    def add_mob(self, mob_info):
        mob = FakeMob(mob_info.id)
        self.append(mob)
        return mob


class FakeControls:
    def __init__(self, firing=False):
        self.events = []
        self.firing = firing
        self.drawn = 0

    def handle_event(self, event):
        self.events.append(event)

    def is_firing(self):
        return self.firing

    def draw(self, window):
        self.drawn += 1


class FakeGame:
    def __init__(self, mode=Mode.OFFLINE):
        self.mouse = SimpleNamespace(position=(0, 0))
        self.clock = SimpleNamespace(get_time=lambda: 16)
        self.keys = {}
        self.mode = mode
        self.client = SimpleNamespace(send=Spy())
        self.player_info = SimpleNamespace(id=1, base_number=1, room=SimpleNamespace(update=Spy()))
        self.size = (800, 600)
        self.window = pygame.Surface((800, 600))
        self._is_in_debug_mode = False
        self.start = Spy()
        self.leave_match = Spy()


def make_scene(**overrides):
    scene = object.__new__(GameplayScene)
    scene.game = FakeGame()
    scene.players = FakePlayers()
    scene.mobs = FakeMobs()
    scene.bullets = []
    scene.effects = []
    scene.map = SimpleNamespace(spawn_points={1: (500, 500)})
    scene.camera = FakeCamera()
    scene.controls = FakeControls()
    scene.player = FakePlayer(1, is_local=True)
    scene.players.append(scene.player)
    scene._was_alive = True
    scene._showing_death_panel = False
    scene._spectate_index = 0
    scene._view_target = scene.player
    scene._death_time = 0
    scene._respawn_secs_shown = -1
    scene._alive_by_id = {1: True}
    scene._roster = []
    scene._roster_icon_size = 28
    scene._roster_font = pygame.font.Font(None, 18)
    scene._paused = False
    scene._pause_rect = pygame.Rect(0, 0, 50, 50)
    scene._respawn_button = FakeButton()
    scene._restart_button = FakeButton()
    scene._mainmenu_button = FakeButton()
    scene._continue_button = FakeButton()
    scene._pause_mainmenu_button = FakeButton()
    scene._death_panel = SimpleNamespace(handle_event=Spy(), draw=Spy())
    scene._pause_panel = SimpleNamespace(handle_event=Spy(), draw=Spy())
    scene.delta_time = 0.0
    scene.mouse_position = (0, 0)
    for key, value in overrides.items():
        setattr(scene, key, value)
    return scene


def click_down(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


# ── world surface (read by entities) ────────────────────────────────────────

def test_assets_and_keys_properties_delegate_to_game():
    scene = make_scene()
    scene.game.assets = object()

    assert scene.assets is scene.game.assets
    assert scene.keys is scene.game.keys


# ── pause button / event dispatch ───────────────────────────────────────────

def test_pause_button_pressed_only_while_alive_and_inside_the_rect():
    scene = make_scene()
    scene.player.alive = True

    assert scene._pause_button_pressed(click_down(scene._pause_rect.center)) is True
    assert scene._pause_button_pressed(click_down((-999, -999))) is False

    scene.player.alive = False
    assert scene._pause_button_pressed(click_down(scene._pause_rect.center)) is False


def test_handle_event_pressing_pause_pauses_the_game():
    scene = make_scene()

    scene.handle_event(click_down(scene._pause_rect.center))

    assert scene._paused is True


def test_handle_event_while_paused_routes_to_the_pause_panel():
    scene = make_scene(_paused=True)
    event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0))

    scene.handle_event(event)

    assert scene._pause_panel.handle_event.calls == [((event, (0, 0)), {})]


def test_handle_event_while_alive_forwards_to_controls():
    scene = make_scene()
    scene.player.alive = True
    event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0))

    scene.handle_event(event)

    assert scene.controls.events == [event]


def test_handle_event_while_dead_and_death_panel_showing_routes_there():
    scene = make_scene()
    scene.player.alive = False
    scene._showing_death_panel = True
    event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0))

    scene.handle_event(event)

    assert scene._death_panel.handle_event.calls == [((event, (0, 0)), {})]


def test_handle_event_while_spectating_routes_to_spectate_handler():
    scene = make_scene()
    scene.player.alive = False
    scene._showing_death_panel = False
    scene.mobs = FakeMobs()

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))

    assert scene.game.leave_match.calls == [((), {"to_lobby": False})]


def test_pause_panel_continue_unpauses():
    scene = make_scene(_paused=True)
    scene._continue_button.clicked = True

    scene._handle_pause_panel(click_down((0, 0)))

    assert scene._paused is False


def test_pause_panel_main_menu_leaves_the_match():
    scene = make_scene(_paused=True)
    scene._pause_mainmenu_button.clicked = True

    scene._handle_pause_panel(click_down((0, 0)))

    assert scene.game.leave_match.calls == [((), {"to_lobby": False})]


# ── update() state machine ───────────────────────────────────────────────────

def test_update_computes_and_clamps_delta_time():
    scene = make_scene()
    scene.game.clock.get_time = lambda: 16
    scene.player.alive = True

    scene.update()
    assert scene.delta_time == pytest.approx(16 * 0.001 * FPS)

    scene.game.clock.get_time = lambda: 100_000  # would blow way past MAX_DELTA_TIME
    scene.update()
    assert scene.delta_time == MAX_DELTA_TIME


def test_update_is_frozen_while_paused():
    scene = make_scene(_paused=True)
    scene.player.update_calls = 0

    scene.update()

    assert scene.player.update_calls == 0  # entity loop never ran


def test_update_detects_the_alive_to_dead_transition(monkeypatch):
    scene = make_scene()
    scene.player.alive = False
    scene._was_alive = True
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 12345)

    scene.update()

    assert scene._showing_death_panel is True
    assert scene._spectate_index == 0
    assert scene._death_time == 12345
    # _respawn_secs_shown is reset to -1 mid-transition, but the same update()
    # call immediately falls into the dead branch and calls _update_death_ui(),
    # which recomputes it from the (now-current) cooldown -- not observable
    # as -1 after a full update() pass.
    assert scene._was_alive is False


def test_update_tracks_local_alive_state_in_the_roster():
    scene = make_scene()
    scene.player.alive = False

    scene.update()

    assert scene._alive_by_id[scene.game.player_info.id] is False


def test_update_advances_every_entity_and_prunes_the_dead():
    scene = make_scene()
    dead_remote = FakePlayer(2, alive=False, is_local=False)
    dead_local_dupe = FakePlayer(3, alive=False, is_local=True)
    scene.players.extend([dead_remote, dead_local_dupe])
    dead_mob = FakeMob(9, alive=False)
    scene.mobs.append(dead_mob)

    scene.update()

    assert scene.player.update_calls == 1
    assert dead_remote.update_calls == 1
    # Dead remotes stay (so they can respawn in place); dead locals are dropped.
    assert dead_remote in scene.players
    assert dead_local_dupe not in scene.players
    assert dead_mob not in scene.mobs


def test_update_while_alive_follows_camera_and_drives_the_player():
    scene = make_scene()
    scene.player.alive = True
    scene.controls.firing = True

    scene.update()

    assert scene.camera.followed == [scene.player.rect]
    assert scene.player.is_shooting is True
    assert scene.player.aim_calls == 1
    assert scene.player.update_movement_calls == 1


def test_update_while_dead_updates_death_ui_and_spectate(monkeypatch):
    scene = make_scene()
    scene.player.alive = False
    scene._update_death_ui = Spy()
    scene._update_spectate = Spy()

    scene.update()

    assert len(scene._update_death_ui.calls) == 1
    assert len(scene._update_spectate.calls) == 1


def test_update_online_sends_player_state():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.player.alive = True
    scene.player.angle = 42

    scene.update()

    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.UPDATE_PLAYER
    assert value == [scene.game.player_info.id, scene.player.rect.center, 42, True]


def test_update_offline_advances_the_room_spawner():
    scene = make_scene()
    scene.game.mode = Mode.OFFLINE

    scene.update()

    assert len(scene.game.player_info.room.update.calls) == 1


# ── respawn timer / death UI ─────────────────────────────────────────────────

def test_respawn_remaining_ms_counts_down_and_floors_at_zero(monkeypatch):
    scene = make_scene()
    scene._death_time = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000 + RESPAWN_DELAY - 100)
    assert scene._respawn_remaining_ms() == 100

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000 + RESPAWN_DELAY + 500)
    assert scene._respawn_remaining_ms() == 0


def test_update_death_ui_enables_the_button_once_the_cooldown_elapses(monkeypatch):
    scene = make_scene()
    scene._death_time = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: RESPAWN_DELAY + 1)

    scene._update_death_ui()

    assert scene._respawn_button.enabled is True
    assert scene._respawn_button.label == "RESPAWN"


def test_update_death_ui_shows_a_countdown_while_on_cooldown(monkeypatch):
    scene = make_scene()
    scene._death_time = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 500)  # 4500ms remaining -> 5s shown

    scene._update_death_ui()

    assert scene._respawn_button.enabled is False
    assert scene._respawn_button.label == "RESPAWN (5)"


def test_update_death_ui_only_relabels_when_the_second_changes(monkeypatch):
    scene = make_scene()
    scene._death_time = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 500)
    scene._update_death_ui()
    scene._respawn_button.label = "SENTINEL"

    scene._update_death_ui()  # same second -- must not touch the label again

    assert scene._respawn_button.label == "SENTINEL"


# ── spectator ────────────────────────────────────────────────────────────────

def test_living_players_filters_by_alive():
    scene = make_scene()
    dead = FakePlayer(2, alive=False)
    scene.players.append(dead)

    assert scene._living_players() == [scene.player]


def test_update_spectate_follows_a_living_teammate():
    scene = make_scene()
    mate = FakePlayer(2, alive=True)
    scene.players.append(mate)
    scene._spectate_index = 1

    scene._update_spectate()

    assert scene._view_target is mate
    assert scene.camera.followed == [mate.rect]


def test_update_spectate_falls_back_to_self_when_nobody_is_alive():
    scene = make_scene()
    scene.player.alive = False

    scene._update_spectate()

    assert scene._view_target is scene.player


# ── death panel / spectate input ────────────────────────────────────────────

def test_death_panel_respawn_click_calls_respawn():
    scene = make_scene()
    scene._respawn_button.clicked = True
    scene._respawn = Spy()

    scene._handle_death_panel(click_down((0, 0)))

    assert len(scene._respawn.calls) == 1


def test_death_panel_restart_click_restarts_the_match():
    scene = make_scene()
    scene._restart_button.clicked = True

    scene._handle_death_panel(click_down((0, 0)))

    assert len(scene.game.start.calls) == 1


def test_death_panel_mainmenu_click_leaves_the_match():
    scene = make_scene()
    scene._mainmenu_button.clicked = True

    scene._handle_death_panel(click_down((0, 0)))

    assert scene.game.leave_match.calls == [((), {"to_lobby": False})]


def test_spectate_left_right_cycles_only_among_the_living():
    scene = make_scene()
    scene.player.alive = False
    mate1, mate2 = FakePlayer(2, alive=True), FakePlayer(3, alive=True)
    scene.players.extend([mate1, mate2])
    scene._spectate_index = 0

    scene._handle_spectate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert scene._spectate_index == 1

    scene._handle_spectate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert scene._spectate_index == 0


def test_spectate_space_respawns_and_r_goes_to_main_menu():
    scene = make_scene()
    scene._respawn = Spy()

    scene._handle_spectate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert len(scene._respawn.calls) == 1

    scene._handle_spectate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    assert scene.game.leave_match.calls == [((), {"to_lobby": False})]


def test_spectate_ignores_non_keydown_events():
    scene = make_scene()
    scene._respawn = Spy()

    scene._handle_spectate(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)))

    assert scene._respawn.calls == []


# ── respawn ──────────────────────────────────────────────────────────────────

def test_respawn_blocked_while_on_cooldown(monkeypatch):
    scene = make_scene()
    scene.player.alive = False
    scene._death_time = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 500)  # still cooling down

    scene._respawn()

    assert scene.player.alive is False


def test_respawn_revives_at_the_spawn_point_once_off_cooldown(monkeypatch):
    scene = make_scene()
    scene.player.alive = False
    scene.players.remove(scene.player)  # pruned on death, as update() would do
    scene._death_time = 0
    scene._showing_death_panel = True
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: RESPAWN_DELAY + 1)

    scene._respawn()

    assert scene.player.alive is True
    assert scene.player.hp == scene.player.max_hp
    assert scene.player.position == scene.map.spawn_points[scene.game.player_info.base_number]
    assert scene.player in scene.players
    assert scene._showing_death_panel is False
    assert scene._was_alive is True


# ── actions ──────────────────────────────────────────────────────────────────

def test_restart_match_delegates_to_game_start():
    scene = make_scene()
    scene._restart_match()
    assert len(scene.game.start.calls) == 1


def test_main_menu_leaves_the_match_without_returning_to_the_lobby_hub():
    scene = make_scene()
    scene._main_menu()
    assert scene.game.leave_match.calls == [((), {"to_lobby": False})]


# ── shoot / mob sync ─────────────────────────────────────────────────────────

def test_shoot_online_sends_the_command_instead_of_firing_locally():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    scene.player.is_shooting = True

    scene.shoot()

    assert scene.game.client.send.calls[0][0] == (Command.SHOOT, scene.player.id)
    assert scene.player.shoot_calls == 0


def test_shoot_offline_fires_locally():
    scene = make_scene()
    scene.game.mode = Mode.OFFLINE
    scene.player.is_shooting = True

    scene.shoot()

    assert scene.player.shoot_calls == 1


def test_shoot_does_nothing_when_not_shooting():
    scene = make_scene()
    scene.player.is_shooting = False

    scene.shoot()

    assert scene.player.shoot_calls == 0
    assert scene.game.client.send.calls == []


def test_spawn_mob_marks_network_driven_only_when_online():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    info = SimpleNamespace(id=5)

    scene.spawn_mob(info)

    mob = scene.mobs.get_mob_from_id(5)
    assert mob.is_network is True

    scene.game.mode = Mode.OFFLINE
    scene.spawn_mob(SimpleNamespace(id=6))
    mob2 = scene.mobs.get_mob_from_id(6)
    assert mob2.is_network is False


def test_hit_mob_online_reports_the_hit_instead_of_applying_it():
    scene = make_scene()
    scene.game.mode = Mode.ONLINE
    mob = FakeMob(1)

    scene.hit_mob(mob, 25)

    (command, value), _ = scene.game.client.send.calls[0]
    assert command == Command.HIT_MOB
    assert value == (1, 25)
    assert mob.hp == 100  # untouched locally


def test_hit_mob_offline_applies_damage_and_stuns():
    scene = make_scene()
    scene.game.mode = Mode.OFFLINE
    mob = FakeMob(1)
    mob.velocity = Vec(5, 5)

    scene.hit_mob(mob, 25)

    assert mob.hp == 75
    assert mob.velocity == Vec(0, 0)


def test_update_mobs_applies_position_and_hp_to_known_mobs_only():
    scene = make_scene()
    known = FakeMob(1)
    scene.mobs.append(known)

    scene.update_mobs([(1, (10, 20), 50), (999, (0, 0), 10)])  # 999 unknown -- ignored

    assert known.target_position == Vec(10, 20)
    assert known.hp == 50


def test_kill_mob_kills_a_known_mob_and_ignores_unknown_ids():
    scene = make_scene()
    known = FakeMob(1)
    scene.mobs.append(known)

    scene.kill_mob(999)  # must not raise
    assert known.alive is True

    scene.kill_mob(1)
    assert known.alive is False


# ── remote player sync ───────────────────────────────────────────────────────

def test_ensure_remote_player_returns_existing_without_re_adding():
    scene = make_scene()
    mate = FakePlayer(2)
    scene.players.append(mate)

    result = scene._ensure_remote_player(2)

    assert result is mate
    assert scene.players.add_calls == []


def test_ensure_remote_player_builds_one_from_the_room_snapshot(assets):
    scene = make_scene()
    scene.game.assets = assets  # _make_roster_entry loads a real character icon
    info = SimpleNamespace(id=7, name="Newcomer", character_name="hitman")
    scene.game.player_info.room = [info]

    result = scene._ensure_remote_player(7)

    assert result is not None
    assert result.id == 7
    assert scene._alive_by_id[7] is True
    assert any(row["id"] == 7 for row in scene._roster)


def test_ensure_remote_player_returns_none_for_an_unknown_id():
    scene = make_scene()
    scene.game.player_info.room = []

    assert scene._ensure_remote_player(42) is None


def test_update_player_position_updates_an_existing_player():
    scene = make_scene()
    mate = FakePlayer(2)
    scene.players.append(mate)

    scene.update_player_position(2, (33, 44))

    assert mate.target_position == Vec(33, 44)


def test_update_player_position_ensures_a_late_joiner_then_updates_it(assets):
    scene = make_scene()
    scene.game.assets = assets  # _make_roster_entry loads a real character icon
    info = SimpleNamespace(id=8, name="Late", character_name="hitman")
    scene.game.player_info.room = [info]

    scene.update_player_position(8, (1, 2))

    joined = scene.players.get_player_with_id(8)
    assert joined is not None
    assert joined.target_position == Vec(1, 2)


def test_update_player_angle_updates_an_existing_player():
    scene = make_scene()
    mate = FakePlayer(2)
    scene.players.append(mate)

    scene.update_player_angle(2, 77)

    assert mate.angle == 77


def test_set_player_alive_updates_the_roster_and_greys_the_remote_player():
    scene = make_scene()
    mate = FakePlayer(2, alive=True, is_local=False)
    scene.players.append(mate)

    scene.set_player_alive(2, False)

    assert scene._alive_by_id[2] is False
    assert mate.alive is False


def test_set_player_alive_resets_hp_only_on_the_dead_to_alive_transition():
    scene = make_scene()
    mate = FakePlayer(2, alive=False, is_local=False)
    mate.hp = 0
    scene.players.append(mate)

    scene.set_player_alive(2, True)

    assert mate.hp == mate.max_hp


def test_set_player_alive_does_not_touch_hp_on_a_same_state_update():
    scene = make_scene()
    mate = FakePlayer(2, alive=True, is_local=False)
    mate.hp = 40
    scene.players.append(mate)

    scene.set_player_alive(2, True)  # already alive -- no transition

    assert mate.hp == 40


def test_set_player_alive_never_touches_the_local_player():
    scene = make_scene()

    scene.set_player_alive(scene.player.id, False)

    assert scene.player.alive is True  # is_local=True -- untouched by design
    assert scene._alive_by_id[scene.player.id] is False  # roster still updates though


def test_remove_player_drops_from_players_roster_and_alive_map():
    scene = make_scene()
    mate = FakePlayer(2)
    scene.players.append(mate)
    scene._roster.append({"id": 2})
    scene._alive_by_id[2] = True

    scene.remove_player(2)

    assert mate not in scene.players
    assert scene._roster == []
    assert 2 not in scene._alive_by_id


def test_remove_player_unknown_id_is_a_no_op():
    scene = make_scene()
    scene.remove_player(999)  # must not raise
