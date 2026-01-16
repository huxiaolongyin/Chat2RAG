from typing import Any, Dict

from pydantic import Field

from .base import BaseSchema, IDMixin


class FlowBase(BaseSchema):
    name: str = Field(...)
    desc: str | None = Field(None)
    current_version: int | None = Field(1)
    flow_json: Dict[str, Any] | None = Field()


class FlowData(IDMixin, FlowBase): ...


class FlowCreate(FlowBase): ...


class FlowUpdate(FlowBase):
    name: str | None = Field(None)
