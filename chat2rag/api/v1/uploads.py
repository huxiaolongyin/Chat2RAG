import gc
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from chat2rag.logger import get_logger
from chat2rag.schemas.base import BaseResponse

router = APIRouter()


logger = get_logger(__name__)


def is_file_in_use(file_path):
    """检查文件是否被其他进程占用"""
    try:
        # 尝试以独占模式打开文件
        with open(file_path, "r+b"):
            pass
        return False
    except (IOError, OSError):
        return True


def safe_move_file(src, dst, max_retries=5, retry_delay=2):
    """安全地移动文件，包含重试机制"""
    for attempt in range(max_retries):
        try:
            # 强制垃圾回收，释放可能的文件句柄
            gc.collect()
            time.sleep(0.5)  # 给系统一点时间释放句柄

            if os.path.exists(dst) and is_file_in_use(dst):
                if attempt < max_retries - 1:
                    logger.warning(f"目标文件被占用，等待 {retry_delay} 秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise OSError(f"文件 {dst} 被其他程序占用，请关闭相关程序后重试")

            # 检查源文件是否被占用
            if is_file_in_use(src):
                if attempt < max_retries - 1:
                    logger.warning(f"源文件被占用，等待 {retry_delay} 秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise OSError(f"源文件 {src} 被其他程序占用")

            shutil.move(str(src), str(dst))
            return True

        except OSError as e:
            if attempt < max_retries - 1:
                logger.warning(f"移动文件失败，等待 {retry_delay} 秒后重试: {e}")
                time.sleep(retry_delay)
            else:
                raise e

    return False


def safe_remove_file(file_path, max_retries=3, retry_delay=1):
    """安全地删除文件，包含重试机制"""
    for attempt in range(max_retries):
        try:
            # 强制垃圾回收
            gc.collect()
            time.sleep(0.5)

            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except (OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"删除文件失败，等待 {retry_delay} 秒后重试: {e}")
                time.sleep(retry_delay)
            else:
                logger.error(f"无法删除临时文件 {file_path}: {e}")
                return False
    return False


def validate_headers_with_template(uploaded_file_path, sheet_name: str):
    """
    对比上传文件与模板文件的表头（2-3行）
    """
    template_df = None
    uploaded_df = None

    try:
        template_path = Path("uploads/ticket/template.xlsx")

        if not template_path.exists():
            return False, "模板文件不存在，请确保 uploads/ticket/template.xlsx 存在"

        # 使用 with 语句确保文件正确关闭
        with pd.ExcelFile(template_path) as template_file:
            template_df = pd.read_excel(template_file, nrows=4, header=None)

        with pd.ExcelFile(uploaded_file_path) as uploaded_file:
            uploaded_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, nrows=4, header=None)

        # 检查行数是否一致
        if len(template_df) < 4 or len(uploaded_df) < 4:
            return False, "文件格式不正确，缺少必要的表头行"

        # 检查列数是否一致
        if template_df.shape[1] != uploaded_df.shape[1]:
            return False, f"列数不匹配，模板有{template_df.shape[1]}列，上传文件有{uploaded_df.shape[1]}列"

        # 对比第3行和第4行的表头内容（索引1和2）
        for row_idx in [2, 3]:  # 第3行和第4行
            template_row = template_df.iloc[row_idx].fillna("")
            uploaded_row = uploaded_df.iloc[row_idx].fillna("")

            for col_idx in range(len(template_row)):
                template_cell = str(template_row.iloc[col_idx]).strip()
                uploaded_cell = str(uploaded_row.iloc[col_idx]).strip()

                if template_cell != uploaded_cell:
                    return (
                        False,
                        f"第{row_idx+1}行第{col_idx+1}列表头不匹配：模板为'{template_cell}'，上传文件为'{uploaded_cell}'",
                    )

        return True, "表头校验通过"

    except Exception as e:
        return False, f"表头校验失败: {str(e)}"
    finally:
        # 强制释放DataFrame占用的内存
        del template_df, uploaded_df
        gc.collect()


def validate_date_in_r2(file_path):
    """
    根据提供的逻辑校验R2单元格的日期
    """
    excel_file = None
    try:
        # 使用 with 语句确保 ExcelFile 对象正确关闭
        with pd.ExcelFile(file_path) as excel_file:
            sheet_names = excel_file.sheet_names

            for sheet_name in reversed(sheet_names):
                # 读取表头部分（前3行）
                df_header = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=3, header=None)

                # R2单元格对应第2行第17列（R列，索引从0开始所以是17）
                if len(df_header.columns) <= 17 or len(df_header) <= 1:
                    continue

                q2_value = df_header.iloc[1, 17]  # 第2行第17列

                if pd.isna(q2_value):
                    continue

                # 获取今天的日期
                today = date.today()

                # 尝试解析日期
                try:
                    sheet_date = None

                    # 如果是数字（Excel日期序列号）
                    if isinstance(q2_value, (int, float)):
                        sheet_date = pd.to_datetime(q2_value, origin="1899-12-30", unit="D").date()

                    # 如果是字符串，尝试解析
                    elif isinstance(q2_value, str):
                        date_str = q2_value.replace("年", "-").replace("月", "-").replace("日", "").replace(" ", "")
                        sheet_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # 如果是datetime对象
                    elif isinstance(q2_value, datetime):
                        sheet_date = q2_value.date()

                    # 其他情况尝试pandas转换
                    else:
                        sheet_date = pd.to_datetime(q2_value).date()

                    # 检查是否是今天
                    if sheet_date and sheet_date == today:
                        return True, f"日期校验通过: {sheet_date.strftime('%Y-%m-%d')} (今天)", sheet_name

                except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime) as e:
                    logger.warning(f"解析{sheet_name}的R2单元格的日期失败: {q2_value}, 错误: {e}")
                    continue

        return False, "未找到今天日期的工作表，请确认表的R2单元格存在今天的日期", ""

    except Exception as e:
        return False, f"日期校验失败: {str(e)}", ""
    finally:
        # 强制垃圾回收
        gc.collect()


@router.post("/ticket", response_model=BaseResponse, summary="福州南站计划作业记录表上传")
async def upload_ticket_file(file: UploadFile = File(...)):
    """
    上传福州南站综控室班计划作业记录表
    """
    temp_file = None
    try:
        # 检查文件类型
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="只支持Excel文件格式 (.xlsx, .xls)")

        # 创建目标目录
        target_dir = Path("uploads/ticket")
        target_dir.mkdir(parents=True, exist_ok=True)

        # 设置目标文件路径
        target_file = target_dir / "福州南站综控室班计划作业记录表.xlsx"

        # 保存临时文件用于校验
        temp_file = target_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

        # 保存上传的文件到临时位置
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            # 确保文件完全写入（在 with 块内部）
            buffer.flush()
            if hasattr(buffer, "fileno"):
                os.fsync(buffer.fileno())

        # 等待一下确保文件句柄释放
        time.sleep(0.5)
        gc.collect()

        # 检查文件是否可以正常读取
        try:
            # 使用 with 语句确保文件正确关闭
            with pd.ExcelFile(temp_file) as test_file:
                pd.read_excel(test_file, nrows=5)
        except Exception as e:
            safe_remove_file(temp_file)
            raise HTTPException(status_code=400, detail=f"无法读取Excel文件: {str(e)}")

        # 日期校验（R2单元格必须是今天）
        date_valid, date_msg, sheet_name = validate_date_in_r2(temp_file)
        if not date_valid:
            safe_remove_file(temp_file)
            raise HTTPException(status_code=400, detail=date_msg)

        # 表头校验（与模板对比）
        header_valid, header_msg = validate_headers_with_template(temp_file, sheet_name)
        if not header_valid:
            safe_remove_file(temp_file)
            raise HTTPException(status_code=400, detail=header_msg)

        # 校验通过，移动文件到最终位置
        if target_file.exists():
            # 检查原文件是否被占用
            if is_file_in_use(target_file):
                safe_remove_file(temp_file)
                raise HTTPException(status_code=400, detail="目标文件正在被其他程序使用，请关闭相关程序后重试")

            # 备份原文件
            backup_file = (
                target_dir / f"福州南站综控室班计划作业记录表_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            safe_move_file(target_file, backup_file)
            logger.info(f"原文件已备份到: {backup_file}")

        safe_move_file(temp_file, target_file)

        return BaseResponse.success(msg="文件上传成功，校验通过")

    except HTTPException:
        raise

    except Exception as e:
        # 清理临时文件
        if temp_file and temp_file.exists():
            safe_remove_file(temp_file)

        logger.error(f"上传文件时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
