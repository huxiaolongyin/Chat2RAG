from tortoise import fields

from chat2rag.core.enums import FileStatus, FileType

from .base import BaseModel, TimestampMixin


class File(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    collection_name = fields.CharField(max_length=255, description="所属知识库")
    filename = fields.CharField(max_length=500, description="原始文件名")
    file_type = fields.CharEnumField(
        FileType, default=FileType.UNKNOWN, description="文件类型"
    )
    file_size = fields.BigIntField(default=0, description="文件大小(字节)")
    file_path = fields.TextField(null=True, description="存储路径")
    status = fields.CharEnumField(
        FileStatus, default=FileStatus.PENDING, description="状态"
    )
    version = fields.IntField(default=1, description="当前版本号")
    description = fields.TextField(null=True, description="文件描述")
    chunk_count = fields.IntField(default=0, description="知识分块数量")
    parse_config = fields.JSONField(null=True, description="解析配置")
    error_message = fields.TextField(null=True, description="错误信息")

    class Meta:
        table = "files"
        indexes = [("collection_name",), ("status",)]


class FileVersion(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    file = fields.ForeignKeyField(
        "app_system.File",
        related_name="versions",
        on_delete=fields.CASCADE,
        description="关联文件",
    )
    version = fields.IntField(description="版本号")
    file_path = fields.TextField(description="文件存储路径")
    file_size = fields.BigIntField(default=0, description="文件大小(字节)")
    change_note = fields.TextField(null=True, description="变更说明")
    chunk_count = fields.IntField(default=0, description="知识分块数量")
    parse_config = fields.JSONField(null=True, description="解析配置")

    class Meta:
        table = "file_versions"
        unique_together = ("file_id", "version")
