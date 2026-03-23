from aerich import Command
from tortoise.exceptions import OperationalError

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.core.security import get_password_hash

logger = get_logger(__name__)


async def modify_db(config=None):
    """
    初始化数据库
    """
    if config is None:
        config = CONFIG.TORTOISE_ORM

    command = Command(tortoise_config=config, app="app_system")

    # Initialize Aerich migration system
    try:
        await command.init()
        logger.debug("Aerich migration system initialized")

        await command.init_db(safe=True)
        logger.debug("Database schema initialized")

    except FileExistsError:
        logger.debug("Migration config already exists, skipping initialization")
    except Exception as e:
        logger.warning(f"Initialization encountered an issue: {e}")

    # Generate migrations
    try:
        migrated = await command.migrate()
        if migrated:
            logger.info(f"Migration generated: {migrated}")
    except Exception as e:
        logger.debug(f"No migrations needed: {e}")

    # Apply migrations
    try:
        upgraded = await command.upgrade(run_in_transaction=True)
        if upgraded:
            logger.info(f"Database upgraded: {upgraded}")
        else:
            logger.debug("Database already up to date")
    except OperationalError as e:
        logger.exception("Database upgrade failed")
        raise
    except Exception as e:
        logger.debug(f"Database already at latest version: {e}")

    await init_default_data()


async def init_default_data():
    """初始化默认数据：默认租户和管理员账号"""
    from chat2rag.models import Tenant, User

    tenant, created = await Tenant.get_or_create(
        code="default", defaults={"name": "默认租户", "status": 1}
    )
    if created:
        logger.info("Created default tenant")

    admin_user = await User.filter(username="admin", tenant_id=tenant.id).first()
    if not admin_user:
        await User.create(
            tenant=tenant,
            username="admin",
            password=get_password_hash("admin123"),
            nickname="管理员",
            is_superuser=True,
            status=1,
        )
        logger.info("Created default admin user (admin/admin123)")
    else:
        logger.debug("Admin user already exists")
