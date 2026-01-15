from typing import Annotated

from fastapi import Query

Current = Annotated[int, Query(ge=1, description="当前页码")]
Size = Annotated[int, Query(ge=1, le=100, description="页码大小")]
