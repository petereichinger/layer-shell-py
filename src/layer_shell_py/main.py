from typing import Annotated

import typer
from pydantic import ValidationError

from .config import Layer, OutlineConfig
from .layer_window import RuntimeDependencyError, run_outline

app = typer.Typer(no_args_is_help=True)


@app.callback()
def callback() -> None:
    """Wayland layer-shell utility."""


@app.command()
def outline(
    color: Annotated[
        str,
        typer.Option(help="GTK/CSS color for the outline."),
    ] = "#ff0000",
    thickness: Annotated[
        int,
        typer.Option(help="Outline thickness in physical pixels."),
    ] = 4,
    layer: Annotated[
        Layer,
        typer.Option(help="Wayland layer-shell layer."),
    ] = Layer.OVERLAY,
    namespace: Annotated[
        str,
        typer.Option(help="Layer-shell namespace."),
    ] = "layer-shell-py",
    allow_non_wayland: Annotated[
        bool,
        typer.Option(help="Skip the Wayland session guard for development."),
    ] = False,
) -> None:
    try:
        config = OutlineConfig(
            color=color,
            thickness=thickness,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        raise typer.Exit(run_outline(config))
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RuntimeDependencyError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
