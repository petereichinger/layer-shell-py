# layer-shell-py

Wayland layer shell utility for showing overlays such as colored outlines and
fullscreen blur targets.

The tool provides fullscreen, input-passive layer-shell surfaces for Wayland
compositors that support layer-shell.

## Requirements

On Arch Linux:

```sh
sudo pacman -S gtk4 python-gobject gtk4-layer-shell
```

Verify the native layer-shell package and introspection bindings:

```sh
pkg-config --modversion gtk-layer-shell-0
python -c 'import gi; gi.require_version("Gtk4LayerShell", "1.0"); from gi.repository import Gtk4LayerShell; print(Gtk4LayerShell)'
```

## Usage

Run a fullscreen red outline on the overlay layer:

```sh
layer-shell-py outline
```

Customize the color and thickness:

```sh
layer-shell-py outline --color '#ff00ff' --thickness 6
```

Create a fullscreen blur target for niri 26.04 or newer:

```sh
layer-shell-py blur
```

The blur command draws a translucent fullscreen tint so niri has a visible
surface to composite the background effect through. Adjust it with `--color`:

```sh
layer-shell-py blur --color '#00000030'
```

Then match its namespace in your niri config:

```kdl
layer-rule {
    match namespace="^layer-shell-py-blur$"

    background-effect {
        blur true
        xray false
    }
}
```

Both commands accept `--namespace` for compositor-specific matching:

```sh
layer-shell-py blur --namespace lockscreen-blur
```

The layer does not request mouse or keyboard input. In foreground mode, stop it
with `Ctrl+C`, a process manager, or `kill`.

For compositor commands and scripts, manage a named instance with `--id` plus
`--start`, `--stop`, or `--toggle`:

```sh
layer-shell-py blur --id fuzzel --toggle --namespace layer-shell-py-blur
layer-shell-py blur --id fuzzel --stop

layer-shell-py outline --id screenshare --start --color '#ff0000' --thickness 4
layer-shell-py outline --id screenshare --stop
```

Managed instances store PID files under `$XDG_RUNTIME_DIR/layer-shell-py/`, or
`/tmp/layer-shell-py-$UID/` when `$XDG_RUNTIME_DIR` is unavailable.

## Development

Install dependencies:

```sh
uv sync
```

Run checks:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Build a single-file Python executable:

```sh
uv run pyinstaller layer-shell-py.spec
```

The executable is written to `dist/layer-shell-py`. It bundles the Python entry
point and Python dependencies, but GTK, GObject introspection typelibs, Wayland,
and `gtk4-layer-shell` remain native system dependencies.
