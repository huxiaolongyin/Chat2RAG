from typing import Optional

from pydantic import BaseModel, Field


# CommandCategory Schemas
class CommandCategoryBase(BaseModel):
    name: str = Field(..., max_length=50, description="分类名称")
    description: Optional[str] = Field(None, max_length=255, description="描述信息")


class CommandCategoryCreate(CommandCategoryBase):
    pass


class CommandCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="分类名称")
    description: Optional[str] = Field(None, max_length=255, description="描述信息")


# Command Schemas
class CommandBase(BaseModel):
    name: str = Field(..., max_length=50, description="指令名称")
    code: str = Field(..., max_length=50, description="指令代码")
    reply: Optional[str] = Field(None, description="回复内容")
    category_id: Optional[int] = Field(None, description="分类ID", alias="categoryId")
    priority: int = Field(0, description="优先级，数字越大优先级越高")
    description: Optional[str] = Field(None, max_length=255, description="描述信息")
    is_active: bool = Field(True, description="是否启用", alias="isActive")
    commands: Optional[str] = Field(None, max_length=255, description="指令文本")


class CommandCreate(CommandBase):
    pass


class CommandUpdate(CommandBase):
    name: Optional[str] = Field(None, max_length=50, description="指令名称")
    code: Optional[str] = Field(None, max_length=50, description="指令代码")
    priority: Optional[int] = Field(None, description="优先级")
    is_active: Optional[bool] = Field(None, description="是否启用", alias="isActive")
