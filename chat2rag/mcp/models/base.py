from tortoise import fields, models


class BaseModel(models.Model):
    """
    基础模型类
    """

    class Meta:
        abstract = True
        app = "app_system"


class TimestampMixin:
    """
    时间戳混入类

    为模型添加创建时间和更新时间字段
    """

    create_time = fields.DatetimeField(
        auto_now_add=True, use_tz=True, description="创建时间"
    )
    update_time = fields.DatetimeField(
        auto_now=True, use_tz=True, description="更新时间"
    )
