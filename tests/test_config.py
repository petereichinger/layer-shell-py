import pytest
from pydantic import ValidationError

from layer_shell_py.config import Layer, OutlineConfig


def test_outline_config_defaults_to_overlay_layer() -> None:
    config = OutlineConfig(color="#ff0000", thickness=4, namespace="test")

    assert config.layer is Layer.OVERLAY


def test_outline_config_rejects_non_positive_thickness() -> None:
    with pytest.raises(ValidationError):
        OutlineConfig(color="#ff0000", thickness=0, namespace="test")


def test_outline_config_rejects_empty_namespace() -> None:
    with pytest.raises(ValidationError):
        OutlineConfig(color="#ff0000", thickness=4, namespace="")
