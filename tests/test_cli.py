import pytest
from typer.testing import CliRunner

from layer_shell_py import main as main_module
from layer_shell_py.instance import InstanceAction
from layer_shell_py.main import app


def test_help_lists_outline_command() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "outline" in result.stdout
    assert "blur" in result.stdout


def test_outline_help_lists_exclusive_zone_options() -> None:
    result = CliRunner().invoke(app, ["outline", "--help"], terminal_width=120)

    assert result.exit_code == 0
    assert "ignore-exclusi" in result.stdout
    assert "respect-exclu" in result.stdout
    assert "--id" in result.stdout
    assert "--start" in result.stdout
    assert "--stop" in result.stdout
    assert "--toggle" in result.stdout


def test_outline_rejects_invalid_thickness_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["outline", "--thickness", "0"])

    assert result.exit_code != 0
    assert "greater than 0" in result.output


def test_outline_rejects_unknown_layer_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["outline", "--layer", "dock"])

    assert result.exit_code != 0
    assert "dock" in result.output


def test_blur_help_lists_color_and_namespace_options() -> None:
    result = CliRunner().invoke(app, ["blur", "--help"], terminal_width=120)

    assert result.exit_code == 0
    assert "color" in result.stdout
    assert "namespace" in result.stdout
    assert "--id" in result.stdout
    assert "--start" in result.stdout
    assert "--stop" in result.stdout
    assert "--toggle" in result.stdout


def test_blur_rejects_unknown_layer_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["blur", "--layer", "dock"])

    assert result.exit_code != 0
    assert "dock" in result.output


def test_blur_rejects_multiple_lifecycle_actions_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["blur", "--start", "--stop"])

    assert result.exit_code != 0
    assert "Use only one" in result.output


def test_outline_rejects_invalid_lifecycle_id_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["outline", "--id", "bad/id", "--stop"])

    assert result.exit_code != 0
    assert "Instance id" in result.output


def test_blur_stop_routes_to_lifecycle_without_starting_gtk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[InstanceAction, str, str, list[str]]] = []

    def fake_manage_instance(
        *,
        action: InstanceAction,
        effect: str,
        instance_id: str,
        child_args: list[str],
    ) -> int | None:
        calls.append((action, effect, instance_id, child_args))
        return 0

    monkeypatch.setattr(main_module, "manage_instance", fake_manage_instance)

    result = CliRunner().invoke(app, ["blur", "--id", "fuzzel", "--stop"])

    assert result.exit_code == 0
    assert calls == [
        (
            InstanceAction.STOP,
            "blur",
            "fuzzel",
            [
                "blur",
                "--color",
                "#00000040",
                "--layer",
                "overlay",
                "--namespace",
                "layer-shell-py-blur",
                "--ignore-exclusive-zones",
            ],
        )
    ]


def test_outline_toggle_routes_visual_options_to_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[InstanceAction, str, str, list[str]]] = []

    def fake_manage_instance(
        *,
        action: InstanceAction,
        effect: str,
        instance_id: str,
        child_args: list[str],
    ) -> int | None:
        calls.append((action, effect, instance_id, child_args))
        return 0

    monkeypatch.setattr(main_module, "manage_instance", fake_manage_instance)

    result = CliRunner().invoke(
        app,
        [
            "outline",
            "--id",
            "screenshare",
            "--toggle",
            "--color",
            "#00ff00",
            "--thickness",
            "8",
            "--namespace",
            "screen-border",
            "--respect-exclusive-zones",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            InstanceAction.TOGGLE,
            "outline",
            "screenshare",
            [
                "outline",
                "--color",
                "#00ff00",
                "--thickness",
                "8",
                "--layer",
                "overlay",
                "--namespace",
                "screen-border",
                "--respect-exclusive-zones",
            ],
        )
    ]
