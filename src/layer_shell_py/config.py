from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Layer(StrEnum):
    BACKGROUND = "background"
    BOTTOM = "bottom"
    TOP = "top"
    OVERLAY = "overlay"


class OutlineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    color: str = Field(min_length=1)
    thickness: int = Field(gt=0)
    layer: Layer = Layer.OVERLAY
    namespace: str = Field(min_length=1)
    allow_non_wayland: bool = False
