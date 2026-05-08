# AGENTS.md

## Project Shape
- Python 3.14 package managed by `uv`; lockfile is `uv.lock` and Pyright is configured to use `.venv`.
- CLI entrypoint is `layer-shell-py = layer_shell_py.main:main`; PyInstaller uses `scripts/pyinstaller_entry.py` instead.
- Runtime code lives in `src/layer_shell_py/`; tests are lightweight CLI/config tests in `tests/` and intentionally avoid starting GTK.

## Commands
- Install/update the dev environment with `uv sync`.
- Run the full local check set: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest`.
- Run focused tests with `uv run pytest tests/test_cli.py`, `uv run pytest tests/test_config.py`, or `uv run pytest -k <pattern>`.
- Build the single-file executable with `uv run pyinstaller layer-shell-py.spec`; output goes to `dist/layer-shell-py`.

## Runtime Gotchas
- The app requires Wayland plus native GTK/GI layer-shell libraries: on Arch, `gtk4 python-gobject gtk4-layer-shell`.
- Runtime imports for `gi.repository.Gtk`, `Gdk`, and `Gtk4LayerShell` are intentionally delayed in `layer_window.py`; keep validation paths testable without GTK.
- `_ensure_layer_shell_preloaded()` re-execs the current Python process with `LD_PRELOAD=libgtk4-layer-shell`; account for that when changing startup flow.
- `--allow-non-wayland` only bypasses the Wayland session guard for development; it does not remove the native GTK/GI dependency.

## Packaging Notes
- `layer-shell-py.spec` bundles Python code and Python deps, but GTK, Wayland, GObject introspection, and `gtk4-layer-shell` remain system dependencies.
- The spec only adds `Gtk4LayerShell-1.0.typelib` when found under `/usr/lib/girepository-1.0/` or `/usr/lib64/girepository-1.0/`.

## Style And Tests
- Ruff uses line length 88, double quotes, Python 3.14, and a broad lint set; do not assume default Ruff rules.
- Pyright runs in `strict` mode over `src` and `tests`.
- Prefer adding CLI/config tests that fail before GTK startup; tests should not require a Wayland compositor or native GTK layer-shell libraries.
