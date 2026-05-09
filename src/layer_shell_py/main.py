from typing import Annotated

import typer
from pydantic import ValidationError

from .config import BlurConfig, Layer, OutlineConfig
from .instance import InstanceAction, InstanceError, manage_instance

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
    instance_id: Annotated[
        str,
        typer.Option("--id", help="Managed instance id for start, stop, or toggle."),
    ] = "outline",
    start: Annotated[
        bool,
        typer.Option(help="Start this managed outline instance in the background."),
    ] = False,
    stop: Annotated[
        bool,
        typer.Option(help="Stop this managed outline instance."),
    ] = False,
    toggle: Annotated[
        bool,
        typer.Option(help="Toggle this managed outline instance."),
    ] = False,
) -> None:
    from .layer_window import RuntimeDependencyError, run_outline  # noqa: PLC0415

    try:
        action = _instance_action(start=start, stop=stop, toggle=toggle)
        config = OutlineConfig(
            color=color,
            thickness=thickness,
            ignore_exclusive_zones=ignore_exclusive_zones,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        result = manage_instance(
            action=action,
            effect="outline",
            instance_id=instance_id,
            child_args=_outline_child_args(config),
        )
        if result is not None:
            raise typer.Exit(result)
        raise typer.Exit(run_outline(config))
    except (InstanceError, ValidationError) as exc:
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
    instance_id: Annotated[
        str,
        typer.Option("--id", help="Managed instance id for start, stop, or toggle."),
    ] = "blur",
    start: Annotated[
        bool,
        typer.Option(help="Start this managed blur instance in the background."),
    ] = False,
    stop: Annotated[
        bool,
        typer.Option(help="Stop this managed blur instance."),
    ] = False,
    toggle: Annotated[
        bool,
        typer.Option(help="Toggle this managed blur instance."),
    ] = False,
) -> None:
    from .layer_window import RuntimeDependencyError, run_blur  # noqa: PLC0415

    try:
        action = _instance_action(start=start, stop=stop, toggle=toggle)
        config = BlurConfig(
            color=color,
            ignore_exclusive_zones=ignore_exclusive_zones,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        result = manage_instance(
            action=action,
            effect="blur",
            instance_id=instance_id,
            child_args=_blur_child_args(config),
        )
        if result is not None:
            raise typer.Exit(result)
        raise typer.Exit(run_blur(config))
    except (InstanceError, ValidationError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RuntimeDependencyError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


def _instance_action(*, start: bool, stop: bool, toggle: bool) -> InstanceAction:
    actions = [start, stop, toggle]
    if sum(actions) > 1:
        msg = "Use only one of --start, --stop, or --toggle."
        raise InstanceError(msg)

    if start:
        return InstanceAction.START
    if stop:
        return InstanceAction.STOP
    if toggle:
        return InstanceAction.TOGGLE
    return InstanceAction.FOREGROUND


def _outline_child_args(config: OutlineConfig) -> list[str]:
    args = [
        "outline",
        "--color",
        config.color,
        "--thickness",
        str(config.thickness),
        "--layer",
        config.layer.value,
        "--namespace",
        config.namespace,
    ]
    args.append(_exclusive_zone_arg(config.ignore_exclusive_zones))
    if config.allow_non_wayland:
        args.append("--allow-non-wayland")
    return args


def _blur_child_args(config: BlurConfig) -> list[str]:
    args = [
        "blur",
        "--color",
        config.color,
        "--layer",
        config.layer.value,
        "--namespace",
        config.namespace,
    ]
    args.append(_exclusive_zone_arg(config.ignore_exclusive_zones))
    if config.allow_non_wayland:
        args.append("--allow-non-wayland")
    return args


def _exclusive_zone_arg(ignore_exclusive_zones: bool) -> str:
    if ignore_exclusive_zones:
        return "--ignore-exclusive-zones"
    return "--respect-exclusive-zones"


if __name__ == "__main__":
    main()
