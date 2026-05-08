# layer-shell-py

Wayland layer shell utility scaffolded for showing either a colored outline or a fullscreen blur effect.

Implementation is intentionally not included yet.

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
