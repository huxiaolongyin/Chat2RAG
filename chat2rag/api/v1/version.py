import re
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter

from chat2rag.logger import auto_log

router = APIRouter()

CHANGELOG_PATH = Path(__file__).parents[3] / "CHANGELOG.md"


def parse_changelog(content: str) -> List[Dict[str, str]]:
    """
    简单解析 CHANGELOG.md 中的版本块
    """
    lines = content.splitlines()
    versions = []
    current_version = None
    version_pattern = r"##\s+\[(?P<version>[^\]]+)\]\s+-\s+(?P<date>\d{4}-\d{2}-\d{2})"

    buffer = []
    for line in lines:
        match = re.match(version_pattern, line)
        if match:
            if current_version:
                versions.append(
                    {
                        "version": current_version["version"],
                        "date": current_version["date"],
                        "changelog": "\n".join(buffer).strip(),
                    }
                )
            current_version = {
                "version": match.group("version"),
                "date": match.group("date"),
            }
            buffer = []
        else:
            if current_version is not None:
                buffer.append(line)
    # 添加最后一个版本
    if current_version and buffer:
        versions.append(
            {
                "version": current_version["version"],
                "date": current_version["date"],
                "changelog": "\n".join(buffer).strip(),
            }
        )
    return versions


@router.get("/raw")
@auto_log(level="info")
async def get_changelog_raw():
    """返回原始 CHANGELOG.md 内容"""
    if not CHANGELOG_PATH.exists():
        return {"error": "CHANGELOG.md not found"}
    return {"content": CHANGELOG_PATH.read_text(encoding="utf-8")}


@router.get("/parsed")
@auto_log(level="info")
async def get_changelog_parsed():
    """返回结构化解析后的版本信息"""
    if not CHANGELOG_PATH.exists():
        return {"error": "CHANGELOG.md not found"}
    content = CHANGELOG_PATH.read_text(encoding="utf-8")
    parsed = parse_changelog(content)
    return {"versions": parsed}
