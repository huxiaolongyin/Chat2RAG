from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse

from chat2rag.config import CONFIG
from chat2rag.utils.camelize import camelize_dict


class Base(JSONResponse):
    """
    Basic response model
    """

    def __init__(
        self,
        code: str = "0000",
        status_code: int = 200,
        msg: str = "OK",
        data: Any = None,
        **kwargs: Any,
    ):
        content = {
            "code": code,
            "version": CONFIG.VERSION,
            "msg": msg,
            "response_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data,
        }
        content.update(kwargs)
        super().__init__(content=camelize_dict(content), status_code=status_code)
