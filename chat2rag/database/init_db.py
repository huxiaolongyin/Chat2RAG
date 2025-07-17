import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migrations():
    """运行数据库迁移"""
    try:
        # 确定alembic.ini文件位置
        project_root = Path(__file__).parent
        alembic_ini = project_root / "alembic.ini"

        if not alembic_ini.exists():
            raise FileNotFoundError(f"找不到alembic.ini文件: {alembic_ini}")

        # 运行迁移命令
        result = subprocess.run(
            ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"数据库迁移成功: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"数据库迁移失败: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"运行迁移时出错: {str(e)}")
        return False


def check_migrations_status():
    """检查是否有未应用的迁移"""
    try:
        project_root = Path(__file__).parent.parent.parent
        alembic_ini = project_root / "alembic.ini"

        result = subprocess.run(
            ["alembic", "-c", str(alembic_ini), "current"],
            capture_output=True,
            text=True,
            check=True,
        )

        # 查看未应用的迁移
        pending = subprocess.run(
            ["alembic", "-c", str(alembic_ini), "history", "--indicate-current"],
            capture_output=True,
            text=True,
            check=True,
        )

        return {"current": result.stdout.strip(), "pending": pending.stdout}
    except Exception as e:
        logger.error(f"检查迁移状态时出错: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 运行迁移
    success = run_migrations()
    print(f"迁移{'成功' if success else '失败'}")

    # 检查状态
    status = check_migrations_status()
    print(f"当前版本: {status.get('current', '未知')}")
    if "pending" in status and status["pending"]:
        print(f"待应用迁移:\n{status['pending']}")
