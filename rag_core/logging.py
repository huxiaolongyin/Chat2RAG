import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"


def setup_logger(name: str = "Chat2RAG"):
    """
    设置日志记录器
    """
    # 创建日志目录

    log_dir = LOG_DIR
    log_dir.mkdir(exist_ok=True)

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器(每日轮转)
    file_handler = TimedRotatingFileHandler(
        log_dir / "rag_core.log",
        when="midnight",  # 每天午夜轮转
        interval=1,  # 间隔天数
        backupCount=30,  # 保留30天的日志
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d.log"  # 日志文件后缀格式
    logger.addHandler(file_handler)

    return logger


# 创建全局logger实例
logger = setup_logger()
