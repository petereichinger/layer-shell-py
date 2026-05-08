from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Layer(StrEnum):
    BACKGROUND = "background"
    BOTTOM = "bottom"
    TOP = "top"
    OVERLAY = "overlay"


class LayerSurfaceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    ignore_exclusive_zones: bool = True
    layer: Layer = Layer.OVERLAY
    namespace: str = Field(min_length=1)
    allow_non_wayland: bool = False

    @property
    def exclusive_zone(self) -> int:
        return -1 if self.ignore_exclusive_zones else 0


class OutlineConfig(LayerSurfaceConfig):
    color: str = Field(min_length=1)
    thickness: int = Field(gt=0)


class BlurConfig(LayerSurfaceConfig):
    pass
