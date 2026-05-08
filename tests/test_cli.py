from typer.testing import CliRunner

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


def test_blur_rejects_unknown_layer_without_starting_gtk() -> None:
    result = CliRunner().invoke(app, ["blur", "--layer", "dock"])

    assert result.exit_code != 0
    assert "dock" in result.output
