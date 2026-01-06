from pydantic import Field

from .base import BaseSchema


class healthData(BaseSchema):
    api: str = Field(..., alias="API", examples=["health"])
