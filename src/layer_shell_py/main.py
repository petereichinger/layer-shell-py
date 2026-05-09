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
    preload: Annotated[
        bool,
        typer.Option(help="Start this managed outline instance hidden."),
    ] = False,
    quit_: Annotated[
        bool,
        typer.Option("--quit", help="Quit this managed outline instance."),
    ] = False,
    resident: Annotated[
        bool,
        typer.Option("--resident", hidden=True),
    ] = False,
    socket_path: Annotated[
        str | None,
        typer.Option("--socket-path", hidden=True),
    ] = None,
    initial_visible: Annotated[
        bool,
        typer.Option("--initial-visible", hidden=True),
    ] = False,
) -> None:
    from .layer_window import RuntimeDependencyError, run_outline  # noqa: PLC0415

    try:
        config = OutlineConfig(
            color=color,
            thickness=thickness,
            ignore_exclusive_zones=ignore_exclusive_zones,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        action = _instance_action(
            start=start,
            stop=stop,
            toggle=toggle,
            preload=preload,
            quit_=quit_,
            resident=resident,
        )
        if resident:
            if socket_path is None:
                msg = "Resident mode requires --socket-path."
                raise InstanceError(msg)
            raise typer.Exit(
                run_outline(
                    config,
                    socket_path=socket_path,
                    initial_visible=initial_visible,
                )
            )
        result = manage_instance(
            action=action,
            effect="outline",
            instance_id=instance_id,
            child_args=_outline_child_args(config),
        )
        raise typer.Exit(result)
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
    preload: Annotated[
        bool,
        typer.Option(help="Start this managed blur instance hidden."),
    ] = False,
    quit_: Annotated[
        bool,
        typer.Option("--quit", help="Quit this managed blur instance."),
    ] = False,
    resident: Annotated[
        bool,
        typer.Option("--resident", hidden=True),
    ] = False,
    socket_path: Annotated[
        str | None,
        typer.Option("--socket-path", hidden=True),
    ] = None,
    initial_visible: Annotated[
        bool,
        typer.Option("--initial-visible", hidden=True),
    ] = False,
) -> None:
    from .layer_window import RuntimeDependencyError, run_blur  # noqa: PLC0415

    try:
        config = BlurConfig(
            color=color,
            ignore_exclusive_zones=ignore_exclusive_zones,
            layer=layer,
            namespace=namespace,
            allow_non_wayland=allow_non_wayland,
        )
        action = _instance_action(
            start=start,
            stop=stop,
            toggle=toggle,
            preload=preload,
            quit_=quit_,
            resident=resident,
        )
        if resident:
            if socket_path is None:
                msg = "Resident mode requires --socket-path."
                raise InstanceError(msg)
            raise typer.Exit(
                run_blur(
                    config,
                    socket_path=socket_path,
                    initial_visible=initial_visible,
                )
            )
        result = manage_instance(
            action=action,
            effect="blur",
            instance_id=instance_id,
            child_args=_blur_child_args(config),
        )
        raise typer.Exit(result)
    except (InstanceError, ValidationError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RuntimeDependencyError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


def _instance_action(
    *,
    start: bool,
    stop: bool,
    toggle: bool,
    preload: bool,
    quit_: bool,
    resident: bool,
) -> InstanceAction:
    if resident:
        return InstanceAction.PRELOAD

    actions = [start, stop, toggle, preload, quit_]
    if sum(actions) > 1:
        msg = "Use only one of --preload, --start, --stop, --toggle, or --quit."
        raise InstanceError(msg)

    if sum(actions) == 0:
        msg = "Use one of --preload, --start, --stop, --toggle, or --quit."
        raise InstanceError(msg)

    if preload:
        return InstanceAction.PRELOAD
    if start:
        return InstanceAction.START
    if stop:
        return InstanceAction.STOP
    if toggle:
        return InstanceAction.TOGGLE
    return InstanceAction.QUIT


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
