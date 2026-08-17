import pygame

from ui.widgets import (
    InputObject, ShapeButton,
    make_ellipse_button_factory, make_input_factory,
    make_text_factory, make_triangle_button_factory,
)


def down_at(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def up_at(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)


def make_button(**overrides):
    kwargs = dict(parent=None, pos=(100, 100), size=(120, 60), anchor="top-left")
    kwargs.update(overrides)
    return ShapeButton(**kwargs)


def center_of(button):
    return button.rect.center


# ── ShapeButton construction ─────────────────────────────────────────────────

def test_enabled_button_starts_in_the_normal_state():
    button = make_button(enabled=True)
    assert button.enabled is True
    assert button.state is None


def test_disabled_button_starts_in_the_disabled_state():
    button = make_button(enabled=False)
    assert button.enabled is False
    assert button.state == "disabled"


def test_triangle_shape_renders_without_raising():
    make_button(shape="triangle", rotation="LEFT")
    make_button(shape="triangle", rotation="RIGHT")


# ── enable / disable ─────────────────────────────────────────────────────────

def test_set_enabled_false_switches_to_the_disabled_state():
    button = make_button(enabled=True)

    button.set_enabled(False)

    assert button.enabled is False
    assert button.state == "disabled"


def test_set_enabled_same_value_is_a_no_op():
    button = make_button(enabled=True)
    button._is_pressed = True  # would be reset by a real toggle

    button.set_enabled(True)

    assert button._is_pressed is True


# ── is_clicked ───────────────────────────────────────────────────────────────

def test_is_clicked_true_only_when_enabled_and_hit():
    # MouseInteractive.is_clicked tracks press-then-release -- a bare UP
    # with no prior DOWN never registers as a click.
    button = make_button(enabled=True)
    pos = center_of(button)

    button.is_clicked(down_at(pos), pos)
    assert button.is_clicked(up_at(pos), pos) is True


def test_is_clicked_false_when_disabled_even_on_a_hit():
    button = make_button(enabled=False)
    pos = center_of(button)

    button.is_clicked(down_at(pos), pos)

    assert button.is_clicked(up_at(pos), pos) is False


# ── press / release visuals ──────────────────────────────────────────────────

def test_pressing_and_releasing_toggles_the_pressed_flag():
    button = make_button(enabled=True)
    pos = center_of(button)

    button.handle_event(down_at(pos), pos)
    assert button._is_pressed is True

    button.handle_event(up_at(pos), pos)
    assert button._is_pressed is False


def test_pressing_outside_the_button_does_not_press_it():
    button = make_button(enabled=True)

    button.handle_event(down_at((-999, -999)), (-999, -999))

    assert button._is_pressed is False


def test_disabled_button_ignores_press_events():
    button = make_button(enabled=False)
    pos = center_of(button)

    button.handle_event(down_at(pos), pos)

    assert button._is_pressed is False


# ── label ────────────────────────────────────────────────────────────────────

def test_set_label_creates_a_font_lazily_and_rerenders():
    button = make_button(text="")
    assert button._font is None

    button.set_label("Go")

    assert button._font is not None
    assert button._text == "Go"


# ── InputObject ──────────────────────────────────────────────────────────────

def make_input(**overrides):
    kwargs = dict(parent=None, pos=(50, 50), size=(200, 40), anchor="top-left")
    kwargs.update(overrides)
    return InputObject(**kwargs)


def test_new_input_starts_empty_and_unfocused():
    field = make_input(placeholder="name")
    assert field.text == ""
    assert field.editing is False


def test_clicking_inside_focuses_the_field():
    field = make_input()
    pos = field.rect.center

    field.handle_event(down_at(pos), pos)

    assert field.editing is True


def test_clicking_outside_unfocuses_the_field():
    field = make_input()
    field.editing = True

    field.handle_event(down_at((-999, -999)), (-999, -999))

    assert field.editing is False


def test_text_input_only_applies_while_editing():
    field = make_input()
    field.editing = True

    field.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="hi"), (0, 0))

    assert field.text == "hi"


def test_text_input_ignored_while_not_editing():
    field = make_input()
    field.editing = False

    field.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="hi"), (0, 0))

    assert field.text == ""


def test_backspace_removes_the_last_character():
    field = make_input()
    field.editing = True
    field.text = "abc"

    field.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE), (0, 0))

    assert field.text == "ab"


def test_enter_commits_and_stops_editing():
    field = make_input()
    field.editing = True
    field.text = "abc"

    field.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), (0, 0))

    assert field.editing is False
    assert field.text == "abc"  # unchanged -- Enter commits, doesn't clear


def test_set_text_overwrites_the_current_contents():
    field = make_input()

    field.set_text("preset")

    assert field.text == "preset"


# ── panel-loader factories ───────────────────────────────────────────────────

def test_ellipse_button_factory_reads_cfg_fields():
    factory = make_ellipse_button_factory()
    cfg = {"position": (10, 10), "size": (100, 50), "text": "Play", "is_active": False}

    button = factory(cfg, None)

    assert isinstance(button, ShapeButton)
    assert button._shape == "ellipse"
    assert button.enabled is False
    assert button._text == "Play"


def test_triangle_button_factory_reads_rotation():
    factory = make_triangle_button_factory()
    cfg = {"position": (10, 10), "size": (40, 40), "rotation": "LEFT"}

    button = factory(cfg, None)

    assert button._shape == "triangle"
    assert button._rotation == "LEFT"


def test_input_factory_reads_placeholder():
    factory = make_input_factory()
    cfg = {"position": (10, 10), "size": (200, 40), "placeholder": "Room code"}

    field = factory(cfg, None)

    assert isinstance(field, InputObject)
    assert field.placeholder == "Room code"


def test_text_factory_reads_text_and_color():
    factory = make_text_factory()
    cfg = {"position": (10, 10), "text": "Hello", "color": [1, 2, 3]}

    text_obj = factory(cfg, None)

    assert text_obj.text == "Hello"
