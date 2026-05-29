"""Project UI widgets for the panel system.

These are choose-your-way-specific widgets that plug into pygame_core's panel
loader (each `make_*_factory()` returns a `(cfg, parent) -> object` callable to
register with PanelLoaderExt). The engine has no button/input widget — buttons
there are image assets — so we vector-draw the pill/triangle look the project
already uses and register the surfaces via StateObject.add_surface().
"""
import pygame

from util.constants import Red, Blue, Gray, Black, White
from pygame_core.ecs.state_object import StateObject, HoverableStateObject
from pygame_core.ui_widgets.text_object import TextObject

_RADIUS = 25  # pill corner radius (matches the old EllipseButton)
_DEPTH = 5    # 3D "lip" height (matches the old EllipseButton/TriangleButton)


def _pill_surface(size, color, pressed=False):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    up = pygame.Rect(0, 0, w, h - _DEPTH)
    down = pygame.Rect(0, _DEPTH, w, h - _DEPTH)
    pygame.draw.rect(surf, Black, down, 0, _RADIUS)        # bottom lip / shadow
    face = down if pressed else up                          # pressed => face sits low
    pygame.draw.rect(surf, color, face, 0, _RADIUS)         # raised (or pushed) face
    pygame.draw.rect(surf, Black, face, 2, _RADIUS)         # face border
    return surf


def _triangle_surface(size, color, rotation, pressed=False):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if rotation == "LEFT":
        up = [(w, 0), (0, h / 2 - _DEPTH), (w, h - 2 * _DEPTH)]
        down = [(w, 2 * _DEPTH), (0, h / 2 + _DEPTH), (w, h)]
    else:  # RIGHT
        up = [(0, 0), (w, h / 2 - _DEPTH), (0, h - 2 * _DEPTH)]
        down = [(0, 2 * _DEPTH), (w, h / 2 + _DEPTH), (0, h)]
    pygame.draw.polygon(surf, Black, down)
    face = down if pressed else up
    pygame.draw.polygon(surf, color, face, 0)
    pygame.draw.polygon(surf, Black, face, 2)
    return surf


class ShapeButton(HoverableStateObject):
    """Vector-drawn pill or triangle button. States: None (normal) and
    'disabled'; hover uses the mouse-over colour (keyboard focus reuses it).
    While the mouse is held down over the button the face drops (press effect),
    matching the old EllipseButton/TriangleButton. Clicks are suppressed while
    disabled."""

    def __init__(self, parent, pos, size, *, normal_color=Red, hover_color=Blue,
                 disabled_color=Gray, shape="ellipse", rotation="RIGHT",
                 enabled=True, anchor="top-left"):
        super().__init__(parent=parent, pos=pos, size=size, image_path=None, anchor=anchor)
        size = tuple(size)
        if shape == "triangle":
            draw = lambda c, pressed=False: _triangle_surface(size, c, rotation, pressed)
        else:
            draw = lambda c, pressed=False: _pill_surface(size, c, pressed)

        self.add_surface(None, draw(normal_color))
        self._hover_images[None] = draw(hover_color)
        self.add_surface("disabled", draw(disabled_color))
        self._hover_images["disabled"] = draw(disabled_color)  # disabled never highlights

        # pressed variants (None state only — disabled buttons don't press)
        self._pressed_image = draw(hover_color, pressed=True)
        self._is_pressed = False

        self.enabled = enabled
        if not enabled:
            self.set_base_state("disabled")

    def set_enabled(self, value: bool) -> None:
        if value == self.enabled:
            return
        self.enabled = value
        self._is_pressed = False
        self.set_base_state(None if value else "disabled")

    def handle_event(self, event, mouse_pos) -> None:
        super().handle_event(event, mouse_pos)  # MOUSEMOTION hover swap
        if not self.enabled:
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.is_mouse_over(mouse_pos)):
            self._is_pressed = True
            self._renderer.set_image(self._pressed_image)
        elif event.type == pygame.MOUSEBUTTONUP and self._is_pressed:
            self._is_pressed = False
            self._renderer.set_image(self._active_surface)

    def is_clicked(self, event, mouse_pos) -> bool:
        return self.enabled and super().is_clicked(event, mouse_pos)


class InputObject(StateObject):
    """Single-line text input as a panel widget (ports gui/input_box.py):
    click to focus, type to edit, placeholder shown when empty + unfocused."""

    def __init__(self, parent, pos, size, *, font_size=32, placeholder="",
                 active_color=Blue, inactive_color=Gray, text_color=White,
                 anchor="top-left"):
        super().__init__(parent=parent, pos=pos, size=size, image_path=None, anchor=anchor)
        self.font = pygame.font.Font(None, font_size)
        self.text = ""
        self.placeholder = placeholder
        self.editing = False
        self._active_color = active_color
        self._inactive_color = inactive_color
        self._text_color = text_color
        self._render()

    def _render(self) -> None:
        w, h = self.rect.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        border = self._active_color if self.editing else self._inactive_color
        pygame.draw.rect(surf, border, surf.get_rect(), 2)
        if self.text or self.editing:
            label, color = self.text, self._text_color
        else:
            label, color = self.placeholder, self._inactive_color
        ts = self.font.render(label, True, color)
        surf.blit(ts, (w / 2 - ts.get_width() / 2, h / 2 - ts.get_height() / 2))
        self.add_surface(None, surf)

    def handle_event(self, event, mouse_pos) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.editing = self.is_mouse_over(mouse_pos)
            self._render()
        elif event.type == pygame.KEYDOWN and self.editing:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            self._render()


# ── panel-loader factories ────────────────────────────────────────────────────

def make_ellipse_button_factory():
    def factory(cfg, parent):
        return ShapeButton(
            parent, tuple(cfg["position"]), tuple(cfg["size"]),
            shape="ellipse",
            normal_color=tuple(cfg.get("color", Red)),
            hover_color=tuple(cfg.get("hover_color", Blue)),
            enabled=cfg.get("is_active", True),
            anchor=cfg.get("anchor", "top-left"),
        )
    return factory


def make_triangle_button_factory():
    def factory(cfg, parent):
        return ShapeButton(
            parent, tuple(cfg["position"]), tuple(cfg["size"]),
            shape="triangle",
            rotation=cfg.get("rotation", "RIGHT"),
            normal_color=tuple(cfg.get("color", Blue)),
            hover_color=tuple(cfg.get("hover_color", Red)),
            enabled=cfg.get("is_active", True),
            anchor=cfg.get("anchor", "top-left"),
        )
    return factory


def make_input_factory():
    def factory(cfg, parent):
        return InputObject(
            parent, tuple(cfg["position"]), tuple(cfg["size"]),
            font_size=cfg.get("font_size", 32),
            placeholder=cfg.get("placeholder", ""),
            anchor=cfg.get("anchor", "top-left"),
        )
    return factory


def make_text_factory():
    """Text factory using pygame's default font (Font(None, size)) to match the
    original menu — the engine's load_font() falls back to SysFont('Arial')."""
    def factory(cfg, parent):
        return TextObject(
            parent,
            cfg["position"],
            cfg.get("text", ""),
            pygame.font.Font(None, cfg.get("font_size", 32)),
            cfg.get("color", [255, 255, 255]),
            cfg.get("background_color"),
            padding=cfg.get("padding"),
            anchor=cfg.get("anchor", "top-left"),
            states=cfg.get("states"),
        )
    return factory
