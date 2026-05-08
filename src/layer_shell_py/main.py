from typing import Annotated

import typer
from pydantic import ValidationError

from .config import BlurConfig, Layer, OutlineConfig
from .layer_window import RuntimeDependencyError, run_blur, run_outline

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
    ignore_exclusive_zones: Annotated[
        bool,
        typer.Option(
            "--ignore-exclusive-zones/--respect-exclusive-zones",
            help="Ignore compositor-reserved areas such as bars and panels.",
        ),
    ] = True,
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
            ignore_exclusive_zones=ignore_exclusive_zones,
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


@app.command()
def blur(
    color: Annotated[
        str,
        typer.Option(help="GTK/CSS color for the blur layer tint."),
    ] = "#00000040",
    ignore_exclusive_zones: Annotated[
        bool,
        typer.Option(
            "--ignore-exclusive-zones/--respect-exclusive-zones",
            help="Ignore compositor-reserved areas such as bars and panels.",
        ),
    ] = True,
    layer: Annotated[
        Layer,
        typer.Option(help="Wayland layer-shell layer."),
    ] = Layer.OVERLAY,
    namespace: Annotated[
        str,
        typer.Option(help="Layer-shell namespace for matching niri layer rules."),
    ] = "layer-shell-py-blur",
    allow_non_wayland: Annotated[
        bool,
        typer.Option(help="Skip the Wayland session guard for development."),
    ] = False,
) -> None:
    try:
        config = BlurConfig(
            color=color,
            ignore_exclusive_zones=ignore_exclusive_zones,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        raise typer.Exit(run_blur(config))
    except ValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RuntimeDependencyError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
