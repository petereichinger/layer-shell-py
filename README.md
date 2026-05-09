# layer-shell-py

Wayland layer shell utility for showing overlays such as colored outlines and
fullscreen blur targets.

The tool provides fullscreen, input-passive layer-shell surfaces for Wayland
compositors that support layer-shell.

## Requirements

Python 3.14 or newer is required.

On Arch Linux:

```sh
sudo pacman -S gtk4 python-gobject gtk4-layer-shell
```

Verify the native layer-shell package and introspection bindings:

```sh
pkg-config --modversion gtk-layer-shell-0
python -c 'import gi; gi.require_version("Gtk4LayerShell", "1.0"); from gi.repository import Gtk4LayerShell; print(Gtk4LayerShell)'
```

## Installation

Install the native requirements first, then install the Python package from a
GitHub Release wheel:

```sh
python -m pip install layer_shell_py-<version>-py3-none-any.whl
```

For isolated CLI installs, use `pipx` instead:

```sh
pipx install layer_shell_py-<version>-py3-none-any.whl
```

Release artifacts include a wheel and source distribution. They do not bundle
GTK, GObject introspection, Wayland, or `gtk4-layer-shell`; those remain native
system dependencies.

## Usage

Preload a fullscreen red outline resident process on the overlay layer:

```sh
layer-shell-py outline --preload
```

Customize the color and thickness:

```sh
layer-shell-py outline --preload --color '#ff00ff' --thickness 6
```

Preload a fullscreen blur target for niri 26.04 or newer:

```sh
layer-shell-py blur --preload
```

The blur command draws a translucent fullscreen tint so niri has a visible
surface to composite the background effect through. Adjust it with `--color`:

```sh
layer-shell-py blur --preload --color '#00000030'
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
layer-shell-py blur --preload --namespace lockscreen-blur
```

The layer does not request mouse or keyboard input.

Instances are resident processes. Use `--preload` at login to start one hidden,
then show or hide it instantly from compositor commands and scripts. `--stop`
hides the layer but keeps the process warm; use `--quit` to terminate it.

```sh
layer-shell-py blur --id fuzzel --preload --namespace layer-shell-py-blur
layer-shell-py blur --id fuzzel --start
layer-shell-py blur --id fuzzel --stop
layer-shell-py blur --id fuzzel --quit

layer-shell-py outline --id screenshare --preload --color '#ff0000' --thickness 4
layer-shell-py outline --id screenshare --start
layer-shell-py outline --id screenshare --stop
```

Managed instances store PID, socket, and log files under
`$XDG_RUNTIME_DIR/layer-shell-py/`, or `/tmp/layer-shell-py-$UID/` when
`$XDG_RUNTIME_DIR` is unavailable.

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

Build Python package distributions:

```sh
uv build
```

The wheel and source distribution are written to `dist/`.

Build a PyInstaller onedir executable:

```sh
uv run pyinstaller layer-shell-py.spec
```

The executable directory is written to `dist/layer-shell-py`. It bundles the
Python entry point and Python dependencies, but GTK, GObject introspection
typelibs, Wayland, and `gtk4-layer-shell` remain native system dependencies.

Version tags matching `v*` automatically build the wheel and source distribution
and upload them to the corresponding GitHub Release.
