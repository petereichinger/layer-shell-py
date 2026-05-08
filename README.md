# layer-shell-py

Wayland layer shell utility for showing overlays such as colored outlines.

The initial implementation provides a fullscreen, input-passive outline layer for
Wayland compositors that support layer-shell.

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

The layer does not request mouse or keyboard input. Stop it with `Ctrl+C`, a
process manager, or `kill`.

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
