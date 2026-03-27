import gc
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseResponse
from chat2rag.services.excel_schema_service import recognize_and_save_schema

router = APIRouter()


logger = get_logger(__name__)


def is_file_in_use(file_path):
    """检查文件是否被其他进程占用"""
    try:
        with open(file_path, "r+b"):
            pass
        return False
    except (IOError, OSError):
        return True


def safe_move_file(src, dst, max_retries=5, retry_delay=2):
    """安全地移动文件，包含重试机制"""
    for attempt in range(max_retries):
        try:
            gc.collect()
            time.sleep(0.5)

            if os.path.exists(dst) and is_file_in_use(dst):
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Target file is locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {dst}"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    raise OSError(f"文件 {dst} 被其他程序占用，请关闭相关程序后重试")

            if is_file_in_use(src):
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Source file is locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {src}"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    raise OSError(f"源文件 {src} 被其他程序占用")

            shutil.move(str(src), str(dst))
            return True

        except OSError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Failed to move file, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {src} -> {dst}",
                    exc_info=True,
                )
                time.sleep(retry_delay)
            else:
                raise e

    return False


def safe_remove_file(file_path, max_retries=3, retry_delay=1):
    """安全地删除文件，包含重试机制"""
    for attempt in range(max_retries):
        try:
            gc.collect()
            time.sleep(0.5)

            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except (OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Failed to delete file, retrying in {retry_delay}s: {file_path}",
                    exc_info=True,
                )
                time.sleep(retry_delay)
            else:
                logger.exception(f"Failed to delete temporary file: {file_path}")
                return False
    return False


@router.post(
    "/ticket", response_model=BaseResponse, summary="福州南站计划作业记录表上传"
)
async def upload_ticket_file(file: UploadFile = File(...)):
    """
    上传福州南站综控室班计划作业记录表
    """
    temp_file = None
    try:
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, detail="只支持Excel文件格式 (.xlsx, .xls)"
            )

        target_dir = Path("uploads/ticket")
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / "福州南站综控室班计划作业记录表.xlsx"

        temp_file = (
            target_dir
            / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )

        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            buffer.flush()
            if hasattr(buffer, "fileno"):
                os.fsync(buffer.fileno())

        time.sleep(0.5)
        gc.collect()

        try:
            with pd.ExcelFile(temp_file) as test_file:
                pd.read_excel(test_file, nrows=5)
        except Exception as e:
            safe_remove_file(temp_file)
            raise HTTPException(status_code=400, detail=f"无法读取Excel文件: {str(e)}")

        if target_file.exists():
            if is_file_in_use(target_file):
                safe_remove_file(temp_file)
                raise HTTPException(
                    status_code=400,
                    detail="目标文件正在被其他程序使用，请关闭相关程序后重试",
                )

            backup_file = (
                target_dir
                / f"福州南站综控室班计划作业记录表_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            safe_move_file(target_file, backup_file)
            logger.info(f"Original job plan backed up: {backup_file}")

        safe_move_file(temp_file, target_file)

        schema = await recognize_and_save_schema(target_file)
        logger.info(f"Schema recognized: {schema}")

        return BaseResponse.success(msg="文件上传成功")

    except HTTPException:
        raise

    except Exception as e:
        if temp_file and temp_file.exists():
            safe_remove_file(temp_file)

        logger.exception(f"Failed to upload file: {target_file}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
