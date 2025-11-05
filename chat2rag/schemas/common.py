from typing import Annotated

from fastapi import Query

Current = Annotated[int, Query(ge=1)]
Size = Annotated[int, Query(ge=1, le=100)]
