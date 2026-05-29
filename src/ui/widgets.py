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

_RADIUS = 25  # pill corner radius (matches the old EllipseButton)
_DEPTH = 5    # 3D "lip" height (matches the old EllipseButton/TriangleButton)


def _pill_surface(size, color):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    up = pygame.Rect(0, 0, w, h - _DEPTH)
    down = pygame.Rect(0, _DEPTH, w, h - _DEPTH)
    pygame.draw.rect(surf, Black, down, 0, _RADIUS)   # bottom lip / shadow
    pygame.draw.rect(surf, color, up, 0, _RADIUS)     # raised face
    pygame.draw.rect(surf, Black, up, 2, _RADIUS)     # face border
    return surf


def _triangle_surface(size, color, rotation):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if rotation == "LEFT":
        up = [(w, 0), (0, h / 2 - _DEPTH), (w, h - 2 * _DEPTH)]
        down = [(w, 2 * _DEPTH), (0, h / 2 + _DEPTH), (w, h)]
    else:  # RIGHT
        up = [(0, 0), (w, h / 2 - _DEPTH), (0, h - 2 * _DEPTH)]
        down = [(0, 2 * _DEPTH), (w, h / 2 + _DEPTH), (0, h)]
    pygame.draw.polygon(surf, Black, down)
    pygame.draw.polygon(surf, color, up, 0)
    pygame.draw.polygon(surf, Black, up, 2)
    return surf


class ShapeButton(HoverableStateObject):
    """Vector-drawn pill or triangle button. States: None (normal) and
    'disabled'. Hover uses the mouse-over colour; keyboard focus reuses the
    hover art (HoverableStateObject behaviour). Click detection is suppressed
    while disabled."""

    def __init__(self, parent, pos, size, *, normal_color=Red, hover_color=Blue,
                 disabled_color=Gray, shape="ellipse", rotation="RIGHT",
                 enabled=True, anchor="top-left"):
        super().__init__(parent=parent, pos=pos, size=size, image_path=None, anchor=anchor)
        size = tuple(size)
        if shape == "triangle":
            draw = lambda c: _triangle_surface(size, c, rotation)
        else:
            draw = lambda c: _pill_surface(size, c)

        self.add_surface(None, draw(normal_color))
        self._hover_images[None] = draw(hover_color)
        self.add_surface("disabled", draw(disabled_color))
        self._hover_images["disabled"] = draw(disabled_color)  # disabled never highlights

        self.enabled = enabled
        if not enabled:
            self.set_base_state("disabled")

    def set_enabled(self, value: bool) -> None:
        if value == self.enabled:
            return
        self.enabled = value
        self.set_base_state(None if value else "disabled")

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
