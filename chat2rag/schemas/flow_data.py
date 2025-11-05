from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FlowDataBase(BaseModel):
    name: str = Field(...)
    desc: Optional[str] = Field(None)
    current_version: Optional[int] = Field(1, alias="currentVersion")
    flow_json: Optional[Dict[str, Any]] = Field(1, alias="flowJson")


class FlowDataCreate(FlowDataBase): ...


class FlowDataUpdate(FlowDataBase):
    name: Optional[str] = Field(None)
