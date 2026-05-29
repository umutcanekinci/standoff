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


def _blit_centered(surf, face, text, font, text_color):
    if not text or font is None:
        return
    ts = font.render(text, True, text_color)
    surf.blit(ts, (face.centerx - ts.get_width() / 2, face.centery - ts.get_height() / 2))


def _pill_surface(size, color, pressed=False, text="", font=None, text_color=White):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    up = pygame.Rect(0, 0, w, h - _DEPTH)
    down = pygame.Rect(0, _DEPTH, w, h - _DEPTH)
    pygame.draw.rect(surf, Black, down, 0, _RADIUS)        # bottom lip / shadow
    face = down if pressed else up                          # pressed => face sits low
    pygame.draw.rect(surf, color, face, 0, _RADIUS)         # raised (or pushed) face
    pygame.draw.rect(surf, Black, face, 2, _RADIUS)         # face border
    _blit_centered(surf, face, text, font, text_color)      # label rides the face
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
    """Vector-drawn pill or triangle button with a baked-in label. States: None
    (normal) and 'disabled'; hover uses the mouse-over colour (keyboard focus
    reuses it). While the mouse is held down over the button the face drops and
    the label rides down with it (press effect), matching the old buttons.
    Clicks are suppressed while disabled."""

    def __init__(self, parent, pos, size, *, normal_color=Red, hover_color=Blue,
                 disabled_color=Gray, shape="ellipse", rotation="RIGHT",
                 enabled=True, anchor="top-left", text="", text_size=40,
                 text_color=White):
        super().__init__(parent=parent, pos=pos, size=size, image_path=None, anchor=anchor)
        self._size = tuple(size)
        self._shape = shape
        self._rotation = rotation
        self._normal_color = normal_color
        self._hover_color = hover_color
        self._disabled_color = disabled_color
        self._text = text
        self._font = pygame.font.Font(None, text_size) if text else None
        self._text_color = text_color
        self._is_pressed = False

        self._render_surfaces()
        self.enabled = enabled
        if not enabled:
            self.set_base_state("disabled")

    def _draw(self, color, pressed=False):
        if self._shape == "triangle":
            return _triangle_surface(self._size, color, self._rotation, pressed)
        return _pill_surface(self._size, color, pressed, self._text, self._font, self._text_color)

    def _render_surfaces(self) -> None:
        self.add_surface(None, self._draw(self._normal_color))
        self._hover_images[None] = self._draw(self._hover_color)
        self.add_surface("disabled", self._draw(self._disabled_color))
        self._hover_images["disabled"] = self._draw(self._disabled_color)  # disabled never highlights
        self._pressed_image = self._draw(self._hover_color, pressed=True)

    def set_label(self, text: str) -> None:
        self._text = text
        if self._font is None:
            self._font = pygame.font.Font(None, 40)
        self._render_surfaces()
        self._renderer.set_image(self._active_surface)

    def set_enabled(self, value: bool) -> None:
        if value == self.enabled:
            return
        self.enabled = value
        self._is_pressed = False
        self.set_base_state("disabled" if not value else None)

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
            text=cfg.get("text", ""),
            text_size=cfg.get("text_size", 40),
            text_color=tuple(cfg.get("text_color", White)),
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
