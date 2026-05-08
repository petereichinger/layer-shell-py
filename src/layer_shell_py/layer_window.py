from collections.abc import Callable
from importlib import import_module
from os import environ
from typing import Any, cast

from .config import Layer, OutlineConfig


class RuntimeDependencyError(RuntimeError):
    pass


def run_outline(config: OutlineConfig) -> int:
    if not config.allow_non_wayland and not _is_wayland_session():
        msg = "layer-shell-py must run under Wayland."
        raise RuntimeDependencyError(msg)

    gtk, gdk, layer_shell = _load_gtk_modules()
    color = _parse_color(config.color, gdk)

    application = gtk.Application(application_id="dev.peter.LayerShellPy")

    def activate(app: Any) -> None:
        window = gtk.ApplicationWindow(application=app)
        window.set_title(config.namespace)
        window.set_decorated(False)
        _disable_focus(window)
        _make_transparent(window, gtk, gdk)

        layer_shell.init_for_window(window)
        layer_shell.set_namespace(window, config.namespace)
        layer_shell.set_layer(window, _gtk_layer(config.layer, layer_shell))
        layer_shell.set_keyboard_mode(window, layer_shell.KeyboardMode.NONE)
        layer_shell.set_exclusive_zone(window, 0)

        for edge in (
            layer_shell.Edge.TOP,
            layer_shell.Edge.RIGHT,
            layer_shell.Edge.BOTTOM,
            layer_shell.Edge.LEFT,
        ):
            layer_shell.set_anchor(window, edge, True)

        drawing_area = gtk.DrawingArea()
        _disable_focus(drawing_area)
        drawing_area.set_draw_func(_draw_outline(color, config.thickness))
        window.set_child(drawing_area)
        window.connect("realize", _make_click_through)
        window.present()

    application.connect("activate", activate)
    return cast(int, application.run([]))


def _is_wayland_session() -> bool:
    return environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in environ


def _load_gtk_modules() -> tuple[Any, Any, Any]:
    try:
        gi = import_module("gi")
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        gi.require_version("Gtk4LayerShell", "1.0")
        repository = import_module("gi.repository")
        return repository.Gtk, repository.Gdk, repository.Gtk4LayerShell
    except (ImportError, ValueError, AttributeError) as exc:
        msg = (
            "GTK 4, PyGObject, and Gtk4LayerShell are required. "
            "On Arch, install: sudo pacman -S gtk4 python-gobject gtk4-layer-shell"
        )
        raise RuntimeDependencyError(msg) from exc


def _gtk_layer(layer: Layer, layer_shell: Any) -> Any:
    return {
        Layer.BACKGROUND: layer_shell.Layer.BACKGROUND,
        Layer.BOTTOM: layer_shell.Layer.BOTTOM,
        Layer.TOP: layer_shell.Layer.TOP,
        Layer.OVERLAY: layer_shell.Layer.OVERLAY,
    }[layer]


def _disable_focus(widget: Any) -> None:
    widget.set_can_focus(False)
    widget.set_focusable(False)


def _make_transparent(window: Any, gtk: Any, gdk: Any) -> None:
    window.add_css_class("layer-shell-py-outline-window")
    display = gdk.Display.get_default()
    if display is None:
        return

    provider = gtk.CssProvider()
    provider.load_from_string(
        "window.layer-shell-py-outline-window { background-color: transparent; }"
    )
    gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def _make_click_through(window: Any) -> None:
    try:
        cairo = import_module("cairo")
        surface = window.get_surface()
        if surface is not None:
            surface.set_input_region(cairo.Region())
    except (ImportError, AttributeError):
        # Keyboard focus is disabled above; an empty input region is best-effort
        # because the exact GDK surface API can vary by GTK binding version.
        return


def _parse_color(color: str, gdk: Any) -> Any:
    rgba = gdk.RGBA()
    if not rgba.parse(color):
        msg = f"Invalid color: {color}"
        raise RuntimeDependencyError(msg)
    return rgba


def _draw_outline(color: Any, thickness: int) -> Callable[[Any, Any, int, int], None]:
    def draw(_area: Any, context: Any, width: int, height: int) -> None:
        half = thickness / 2

        context.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        context.set_line_width(thickness)
        context.rectangle(
            half,
            half,
            max(0, width - thickness),
            max(0, height - thickness),
        )
        context.stroke()

    return draw
