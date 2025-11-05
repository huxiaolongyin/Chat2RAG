from aerich import Command

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger

logger = get_logger(__name__)


async def modify_db(config=None):
    """
    初始化数据库
    """
    if config is None:
        config = CONFIG.TORTOISE_ORM

    command = Command(tortoise_config=config, app="app_system")
    try:
        # 先初始化 Aerich（创建迁移历史表）
        await command.init()
        logger.debug("Aerich 迁移系统初始化完成")

        # 初始化数据库（第一次运行时创建表）
        await command.init_db(safe=True)
        logger.debug("数据库表结构初始化完成")

    except FileExistsError:
        logger.debug("迁移配置已存在，跳过初始化")
    except Exception as e:
        logger.warning(f"初始化过程遇到问题: {e}")

    # 检测并生成迁移
    try:
        migrated = await command.migrate()
        if migrated:
            logger.debug(f"数据库迁移生成完成: {migrated}")
    except Exception as e:
        logger.debug(f"没有需要迁移的内容: {e}")

    # 应用迁移
    try:
        upgraded = await command.upgrade(run_in_transaction=True)
        if upgraded:
            logger.debug(f"数据库升级完成: {upgraded}")
    except Exception as e:
        logger.debug(f"数据库已是最新版本: {e}")
