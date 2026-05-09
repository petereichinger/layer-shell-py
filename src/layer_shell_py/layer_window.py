import sys
from collections.abc import Callable
from ctypes.util import find_library
from importlib import import_module
from os import environ, execvpe
from pathlib import Path
from socket import AF_UNIX, SOCK_STREAM, socket
from threading import Event, Thread
from typing import Any, cast

from .config import BlurConfig, Layer, LayerSurfaceConfig, OutlineConfig


class RuntimeDependencyError(RuntimeError):
    pass


def run_outline(
    config: OutlineConfig,
    *,
    socket_path: str,
    initial_visible: bool,
) -> int:
    return _run_layer_surface(config, _add_outline_child, socket_path, initial_visible)


def run_blur(
    config: BlurConfig,
    *,
    socket_path: str,
    initial_visible: bool,
) -> int:
    return _run_layer_surface(config, _add_blur_child, socket_path, initial_visible)


def _run_layer_surface(  # noqa: PLR0915
    config: LayerSurfaceConfig,
    add_child: Callable[[Any, Any, Any, LayerSurfaceConfig], None],
    socket_path: str,
    initial_visible: bool,
) -> int:
    if not config.allow_non_wayland and not _is_wayland_session():
        msg = "layer-shell-py must run under Wayland."
        raise RuntimeDependencyError(msg)

    _ensure_layer_shell_preloaded()

    gtk, gdk, layer_shell, glib = _load_gtk_modules()

    application = gtk.Application(application_id="dev.peter.LayerShellPy")
    server_stop = Event()
    server_thread: Thread | None = None

    def activate(app: Any) -> None:
        nonlocal server_thread

        window = gtk.ApplicationWindow(application=app)
        visible = initial_visible
        window.set_title(config.namespace)
        window.set_decorated(False)
        _disable_focus(window)
        _make_transparent(window, gtk, gdk)

        layer_shell.init_for_window(window)
        layer_shell.set_namespace(window, config.namespace)
        layer_shell.set_layer(window, _gtk_layer(config.layer, layer_shell))
        layer_shell.set_keyboard_mode(window, layer_shell.KeyboardMode.NONE)
        layer_shell.set_exclusive_zone(window, config.exclusive_zone)

        for edge in (
            layer_shell.Edge.TOP,
            layer_shell.Edge.RIGHT,
            layer_shell.Edge.BOTTOM,
            layer_shell.Edge.LEFT,
        ):
            layer_shell.set_anchor(window, edge, True)

        add_child(window, gtk, gdk, config)
        window.connect("realize", _make_click_through)

        def show() -> bool:
            nonlocal visible
            visible = True
            window.present()
            return False

        def hide() -> bool:
            nonlocal visible
            visible = False
            window.hide()
            return False

        def toggle() -> bool:
            if visible:
                return hide()
            return show()

        def quit_app() -> bool:
            server_stop.set()
            app.quit()
            return False

        commands = {
            "show": show,
            "hide": hide,
            "toggle": toggle,
            "quit": quit_app,
        }
        server_thread = Thread(
            target=_serve_commands,
            args=(socket_path, server_stop, glib, commands),
            daemon=True,
        )
        server_thread.start()

        if initial_visible:
            window.present()
        else:
            window.hide()

    application.connect("activate", activate)
    try:
        return cast(int, application.run([]))
    finally:
        server_stop.set()
        Path(socket_path).unlink(missing_ok=True)
        if server_thread is not None:
            server_thread.join(timeout=0.2)


def _add_outline_child(
    window: Any,
    gtk: Any,
    gdk: Any,
    config: LayerSurfaceConfig,
) -> None:
    if not isinstance(config, OutlineConfig):
        msg = "Outline window requires outline configuration."
        raise RuntimeDependencyError(msg)

    color = _parse_color(config.color, gdk)
    drawing_area = gtk.DrawingArea()
    _disable_focus(drawing_area)
    drawing_area.set_content_width(config.thickness * 2)
    drawing_area.set_content_height(config.thickness * 2)
    drawing_area.set_draw_func(_draw_outline(color, config.thickness))
    window.set_child(drawing_area)


def _add_blur_child(
    window: Any,
    gtk: Any,
    gdk: Any,
    config: LayerSurfaceConfig,
) -> None:
    if not isinstance(config, BlurConfig):
        msg = "Blur window requires blur configuration."
        raise RuntimeDependencyError(msg)

    color = _parse_color(config.color, gdk)
    drawing_area = gtk.DrawingArea()
    _disable_focus(drawing_area)
    drawing_area.set_draw_func(_draw_fill(color))
    window.set_child(drawing_area)


def _is_wayland_session() -> bool:
    return environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in environ


def _ensure_layer_shell_preloaded() -> None:
    library = find_library("gtk4-layer-shell")
    if library is None:
        msg = "Could not locate libgtk4-layer-shell for LD_PRELOAD."
        raise RuntimeDependencyError(msg)

    preloads = environ.get("LD_PRELOAD", "").split(":")
    if library in preloads:
        return

    env = environ.copy()
    env["LD_PRELOAD"] = ":".join([library, *[item for item in preloads if item]])
    execvpe(sys.executable, _preload_reexec_argv(), env)


def _preload_reexec_argv() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]

    return [sys.executable, *sys.argv]


def _load_gtk_modules() -> tuple[Any, Any, Any, Any]:
    try:
        import_module("cairo")
        gi = import_module("gi")
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        gi.require_version("Gtk4LayerShell", "1.0")
        return (
            import_module("gi.repository.Gtk"),
            import_module("gi.repository.Gdk"),
            import_module("gi.repository.Gtk4LayerShell"),
            import_module("gi.repository.GLib"),
        )
    except (ImportError, ValueError, AttributeError) as exc:
        msg = (
            "GTK 4, PyGObject, Pycairo, and Gtk4LayerShell are required. "
            "On Arch, install: sudo pacman -S gtk4 python-gobject "
            "python-cairo gtk4-layer-shell"
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
    except ImportError, AttributeError:
        # Keyboard focus is disabled above; an empty input region is best-effort
        # because the exact GDK surface API can vary by GTK binding version.
        return


def _serve_commands(
    socket_path: str,
    stop: Event,
    glib: Any,
    commands: dict[str, Callable[[], bool]],
) -> None:
    path = Path(socket_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)

    with socket(AF_UNIX, SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen(8)
        server.settimeout(0.1)

        while not stop.is_set():
            try:
                connection, _addr = server.accept()
            except TimeoutError:
                continue
            except OSError:
                return

            with connection:
                command = connection.recv(128).decode(errors="replace").strip()
            callback = commands.get(command)
            if callback is not None:
                glib.idle_add(callback)


def _parse_color(color: str, gdk: Any) -> Any:
    rgba = gdk.RGBA()
    if not rgba.parse(color):
        msg = f"Invalid color: {color}"
        raise RuntimeDependencyError(msg)
    return rgba


def _draw_outline(color: Any, thickness: int) -> Callable[[Any, Any, int, int], None]:
    def draw(_area: Any, context: Any, width: int, height: int) -> None:
        context.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        context.rectangle(0, 0, width, thickness)
        context.rectangle(0, max(0, height - thickness), width, thickness)
        context.rectangle(0, 0, thickness, height)
        context.rectangle(max(0, width - thickness), 0, thickness, height)
        context.fill()

    return draw


def _draw_fill(color: Any) -> Callable[[Any, Any, int, int], None]:
    def draw(_area: Any, context: Any, width: int, height: int) -> None:
        context.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        context.rectangle(0, 0, width, height)
        context.fill()

    return draw
