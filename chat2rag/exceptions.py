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


class BusinessException(BaseException):
    """业务相关的异常"""

    ...


class ChatServiceError(Exception):
    """聊天服务基础异常"""

    pass


class NetworkError(ChatServiceError):
    """网络相关异常"""

    pass


class ParseError(ChatServiceError):
    """解析相关异常"""

    pass


class KnowledgeServiceError(Exception):
    """知识库服务异常"""

    pass
