from typing import Any
from rag_core.config import CONFIG
from datetime import datetime
from fastapi.responses import JSONResponse
from humps import camelize


def camelize_dict(obj):
    if isinstance(obj, dict):
        return {camelize(k): camelize_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [camelize_dict(i) for i in list(obj)]
    return obj


class Base(JSONResponse):
    """基础响应模型"""

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


class Success(Base): ...


class Error(Base):
    """基础错误响应模型"""

    def __init__(self, msg: str = "服务器内部错误", data: Any = None, **kwargs: Any):
        super().__init__(code="4000", status_code=400, msg=msg, data=data, **kwargs)
