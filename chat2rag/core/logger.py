import logging
import logging.config
import sys
from importlib.metadata import version
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 标记是否已初始化
_is_initialized = False


def get_banner():
    """
    返回Chat2RAG的ASCII艺术标题
    """
    banner = f"""
    ########################################################################
    #                                                                      #
    #   ██████╗██╗  ██╗ █████╗ ████████╗██████╗ ██████╗  █████╗  ██████╗   #
    #  ██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚════██╗██╔══██╗██╔══██╗██╔════╝   #
    #  ██║     ███████║███████║   ██║    █████╔╝██████╔╝███████║██║  ███╗  #
    #  ██║     ██╔══██║██╔══██║   ██║   ██╔═══╝ ██╔══██╗██╔══██║██║   ██║  #
    #  ╚██████╗██║  ██║██║  ██║   ██║   ███████╗██║  ██║██║  ██║╚██████╔╝  #
    #   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝   #
    #                                                                      #
    #                         Version: {version("chat2rag")}                               #
    #                                                                      #
    #   Author: https://github.com/huxiaolongyin                           #
    #   Email: 1453366421@qq.com                                           #
    #                                                                      #
    ########################################################################
    """
    return banner


def initialize_logging():
    """全局日志系统初始化，只执行一次"""
    global _is_initialized

    if _is_initialized:
        return

    # 定义日志配置
    config = {
        "version": 1,
        "formatters": {
            "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": str(LOG_DIR / "chat2rag.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "Chat2RAG": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
            # 添加 httpcore 的特定配置，设置更高的日志级别
            "httpcore": {"level": "ERROR", "propagate": True},  # 只显示错误及以上级别
            "haystack": {"level": "ERROR", "propagate": True},
            "httpx": {"level": "ERROR", "propagate": True},
            "urllib3": {"level": "ERROR", "propagate": True},
            "asyncio": {"level": "ERROR", "propagate": True},
            "openai": {"level": "ERROR", "propagate": True},
            "tortoise": {"level": "WARNING", "propagate": True},
            "aiosqlite": {"level": "WARNING", "propagate": True},
            "dashscope": {"level": "WARNING", "propagate": True},
            "websocket": {"level": "WARNING", "propagate": True},
            # 可以在这里添加其他logger的配置
        },
        # 根logger设置
        "root": {"level": "DEBUG", "handlers": ["console", "file"]},
    }

    # 应用配置
    logging.config.dictConfig(config)

    # 打印banner (只执行一次)
    banner = get_banner()
    print(banner)

    _is_initialized = True


def get_logger(name: str = "chat2rag"):
    """
    获取配置好的logger实例
    """
    # 确保日志系统已初始化
    initialize_logging()

    # 返回已配置的logger
    return logging.getLogger(name)


logger = logging.getLogger(__name__)


# 初始化日志系统
initialize_logging()

# 创建全局logger实例
logger = get_logger()
