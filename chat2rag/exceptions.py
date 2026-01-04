class BaseException(Exception):
    """项目基础异常类"""

    def __init__(self, msg: str, code: str = None):
        self.msg = msg
        self.code = code
        super().__init__(self.msg)


class ValueAlreadyExist(BaseException):
    """值已存在的异常"""

    def __init__(self, msg: str = "该值已存在"):
        super().__init__(msg)


class ValueNoExist(BaseException):
    """值不存在的异常"""

    def __init__(self, msg: str = "该值不存在"):
        super().__init__(msg)


class BusinessException(BaseException): ...
