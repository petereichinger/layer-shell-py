# layer-shell-rs

Wayland layer-shell utility for showing overlays such as colored outlines and
fullscreen blur targets.

The tool provides fullscreen, input-passive layer-shell surfaces for Wayland
compositors that support layer-shell.

## Requirements

Rust is required to build from source. Runtime/build dependencies include GTK 4
and `gtk4-layer-shell`.

On Arch Linux:

```sh
sudo pacman -S rust gtk4 gtk4-layer-shell
```

Verify the native layer-shell package is available:

```sh
pkg-config --modversion gtk4 gtk4-layer-shell-0
```

## Installation

Build and install with Cargo:

```sh
cargo install --path .
```

Or build a local debug/release binary:

```sh
cargo build
cargo build --release
```

The binary is named `layer-shell-rs`.

## Usage

Preload a fullscreen red outline resident process on the overlay layer:

```sh
layer-shell-rs outline --preload
```

Customize the color and thickness:

```sh
layer-shell-rs outline --preload --color '#ff00ff' --thickness 6
```

Preload a fullscreen blur target for niri 26.04 or newer:

```sh
layer-shell-rs blur --preload
```

The blur command draws a translucent fullscreen tint so niri has a visible
surface to composite the background effect through. Adjust it with `--color`:

```sh
layer-shell-rs blur --preload --color '#00000030'
```

Then match its namespace in your niri config:

```kdl
layer-rule {
    match namespace="^layer-shell-rs-blur$"

    background-effect {
        blur true
        xray false
    }
}
```

Both commands accept `--namespace` for compositor-specific matching:

```sh
layer-shell-rs blur --preload --namespace lockscreen-blur
```

Both commands also accept `--layer` with `background`, `bottom`, `top`, or
`overlay`; `overlay` is the default for new instances. Passing `--layer` with
`--preload`, `--show`, or `--toggle` also updates an already-running resident
instance. By default, surfaces ignore exclusive zones reserved by bars and panels.
Use `--respect-exclusive-zones` to respect them, or
`--ignore-exclusive-zones` to set the default explicitly.

Use `--allow-non-wayland` only for development. It skips the Wayland session
guard, but GTK, Wayland, and `gtk4-layer-shell` are still required.

The layer does not request keyboard input and makes its input region empty on a
best-effort basis, so mouse input normally passes through to windows below.

Instances are resident processes. Use `--preload` at login to start one hidden,
then show or hide it instantly from compositor commands and scripts. `--show`
shows an existing instance or starts one visible if needed. `--hide` hides the
layer but keeps the process warm. `--toggle` switches visibility and starts the
instance visible if needed. Use `--quit` to terminate it.

```sh
layer-shell-rs blur --id fuzzel --preload --namespace layer-shell-rs-blur
layer-shell-rs blur --id fuzzel --show
layer-shell-rs blur --id fuzzel --hide
layer-shell-rs blur --id fuzzel --toggle
layer-shell-rs blur --id fuzzel --quit

layer-shell-rs outline --id screenshare --preload --color '#ff0000' --thickness 4
layer-shell-rs outline --id screenshare --show
layer-shell-rs outline --id screenshare --hide
```

Managed instances store PID, socket, and log files under
`$XDG_RUNTIME_DIR/layer-shell-rs/`, or `/tmp/layer-shell-rs-$UID/` when
`$XDG_RUNTIME_DIR` is unavailable.

Show the installed package version:

```sh
layer-shell-rs --version
```

## Development

Run checks:

```sh
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
```

Build artifacts are written to `target/`.
