from typing import Any

from .base import Base


class Error(Base):
    """
    Basic error response model
    """

    def __init__(
        self,
        msg: str = "服务器内部错误",
        data: Any = None,
        **kwargs: Any,
    ):
        super().__init__(
            code="4000",
            status_code=400,
            msg=msg,
            data=data,
            **kwargs,
        )
