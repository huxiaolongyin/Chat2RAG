from pathlib import Path

from aerich import Command
from tortoise import Tortoise

from chat2rag.mcp.config import SETTINGS
from chat2rag.mcp.logger import get_logger

logger = get_logger(__name__)


async def execute_init_sql_once():
    """
    执行初始化 SQL 文件（每个文件仅一次）
    """
    # 连接数据库
    conn = Tortoise.get_connection("default")

    # 检查并创建标记表
    try:
        # 尝试查询，如果失败（例如表不存在），则在except块中创建
        await conn.execute_query("SELECT 1 FROM init_sql_executed LIMIT 1")
    except Exception:
        # 表不存在，创建标记表
        await conn.execute_script(
            """
            CREATE TABLE IF NOT EXISTS init_sql_executed (
                id SERIAL PRIMARY KEY,
                script_name VARCHAR(255) UNIQUE NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        logger.info("创建 SQL 执行标记表 `init_sql_executed`")

    # 读取并执行 SQL 文件
    init_sql_dir = Path("chat2rag/mcp/init_sql")
    if not init_sql_dir.is_dir():
        logger.warning(f"SQL 初始化目录未找到: {init_sql_dir}, skipping.")
        return
    sql_files = sorted(init_sql_dir.glob("*.sql"))
    if not sql_files:
        logger.warning(f"在 {init_sql_dir} 目录中未找到 .sql 文件, skipping.")
        return

    try:
        for sql_file in sql_files:
            script_name = sql_file.name
            # 检查此脚本是否已执行过
            _, result = await conn.execute_query(
                "SELECT COUNT(*) FROM init_sql_executed WHERE script_name = $1",
                [script_name],
            )
            if result[0][0] > 0:
                logger.info(f"脚本 '{script_name}' 已执行过，跳过")
                continue

            logger.info(f"正在执行 SQL 脚本: {script_name}")
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_script = f.read()

            if sql_script.strip():
                await conn.execute_script(sql_script)
                # 标记为已执行
                await conn.execute_insert(
                    "INSERT INTO init_sql_executed (script_name) VALUES ($1)",
                    [script_name],
                )
                logger.info(f"成功执行并标记脚本 '{script_name}'")

    except Exception as e:
        logger.error(f"执行初始化 SQL 失败: {e}")
        raise


async def modify_db(config=None):
    """
    初始化数据库
    """
    if config is None:
        config = SETTINGS.TORTOISE_ORM

    command = Command(
        tortoise_config=config, app="app_system", location=SETTINGS.MIGRATION_LOCATION
    )
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
