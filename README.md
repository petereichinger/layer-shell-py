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

Then match its namespace in your niri config:

```kdl
layer-rule {
    match namespace="^layer-shell-py-blur$"

    background-effect {
        blur true
    }
}
```

Both commands accept `--namespace` for compositor-specific matching:

```sh
layer-shell-py blur --namespace lockscreen-blur
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
