import pytest
from pydantic import ValidationError

from layer_shell_py.config import BlurConfig, Layer, OutlineConfig


def test_outline_config_defaults_to_overlay_layer() -> None:
    config = OutlineConfig(color="#ff0000", thickness=4, namespace="test")

    assert config.layer is Layer.OVERLAY


def test_blur_config_defaults_to_overlay_layer() -> None:
    config = BlurConfig(namespace="test")

    assert config.layer is Layer.OVERLAY


def test_outline_config_defaults_to_ignoring_exclusive_zones() -> None:
    config = OutlineConfig(color="#ff0000", thickness=4, namespace="test")

    assert config.ignore_exclusive_zones is True
    assert config.exclusive_zone == -1


def test_outline_config_can_respect_exclusive_zones() -> None:
    config = OutlineConfig(
        color="#ff0000",
        thickness=4,
        namespace="test",
        ignore_exclusive_zones=False,
    )

    assert config.exclusive_zone == 0


def test_outline_config_rejects_non_positive_thickness() -> None:
    with pytest.raises(ValidationError):
        OutlineConfig(color="#ff0000", thickness=0, namespace="test")


def test_outline_config_rejects_empty_namespace() -> None:
    with pytest.raises(ValidationError):
        OutlineConfig(color="#ff0000", thickness=4, namespace="")


def test_blur_config_rejects_empty_namespace() -> None:
    with pytest.raises(ValidationError):
        BlurConfig(namespace="")
