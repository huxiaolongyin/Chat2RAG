# AGENTS.md - Coding Agent Guidelines for Chat2RAG

本文档为 AI 编码代理提供项目指南，包含构建、测试、代码风格等关键信息。

## 项目概述

Chat2RAG 是一个基于 RAG（检索增强生成）的人机交互系统，使用 Haystack 框架构建，支持知识库检索、函数调用、流程管理等功能。

**技术栈：**
- 后端：Python 3.11+ / FastAPI / Tortoise ORM / Haystack
- 前端：Vue 3 / TypeScript / Arco Design / Vite
- 数据库：PostgreSQL + Qdrant（向量数据库）

---

## 构建/测试命令

### 后端 (Python)

```bash
# 安装项目（开发模式）
pip install -e ".[dev]"

# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_api/test_chat.py -v

# 运行单个测试函数
pytest tests/test_api/test_chat.py::TestChatBasic::test_chat_basic_success -v

# 运行带标记的测试
pytest -m "not slow" -v

# 代码格式化 (black, line-length=150)
black .

# 导入排序 (isort, profile=black)
isort .

# 类型检查
mypy chat2rag

# 启动后端服务
python backend/main.py
```

### 前端 (Vue/TypeScript)

```bash
cd web

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build

# 类型检查
npm run typecheck

# ESLint 检查
npm run lint
```

---

## 代码风格指南

### Python 代码风格

#### 导入顺序

```python
# 1. 标准库
import asyncio
from datetime import datetime
from typing import AsyncIterator, List

# 2. 第三-party 库
from fastapi import APIRouter
from pydantic import Field
from tortoise import fields

# 3. 本地模块
from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseSchema
```

#### 类型注解

使用 Python 3.11+ 风格：

```python
# 推荐
def get_item(id: int) -> dict | None:
    ...

name: str | None = None

# 不推荐
from typing import Optional
def get_item(id: int) -> Optional[dict]:
    ...
```

#### 命名约定

- 变量/函数：`snake_case`（如 `prompt_service`, `get_detail`）
- 类名：`PascalCase`（如 `PromptService`, `BaseSchema`）
- 常量：`UPPER_SNAKE_CASE`（如 `CONFIG`, `DATABASE_URL`）
- 私有方法：前缀 `_`（如 `_merge_prompt_version_data`）

#### Schema 定义

所有 API Schema 继承 `BaseSchema`：

```python
from chat2rag.schemas.base import BaseSchema

class PromptCreate(BaseSchema):
    prompt_name: str = Field(..., description="提示词名称")
    prompt_desc: str | None = Field(None, description="描述")
    prompt_text: str = Field(..., description="提示词内容")
```

`BaseSchema` 自动将 `snake_case` 转换为 `camelCase` 输出给前端。

#### Model 定义

数据库 Model 继承 `BaseModel` + `TimestampMixin`：

```python
from chat2rag.models.base import BaseModel, TimestampMixin
from tortoise import fields

class Prompt(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    prompt_name = fields.CharField(max_length=100, unique=True)
    current_version = fields.IntField(default=1)
    
    class Meta:
        table = "prompts"
```

#### 异常处理

使用项目自定义异常：

```python
from chat2rag.core.exceptions import (
    ValueNoExist,       # 资源不存在 → HTTP 404
    ValueAlreadyExist,  # 资源已存在 → HTTP 409
    BusinessException,  # 业务错误 → HTTP 400
    ParameterException, # 参数错误 → HTTP 422
)

# 使用示例
if not prompt:
    raise ValueNoExist(f"提示词ID {id} 不存在")

if await self.model.filter(name=name).exists():
    raise ValueAlreadyExist(msg=f"名称 {name} 已存在")
```

#### 日志记录

```python
from chat2rag.core.logger import get_logger

logger = get_logger(__name__)  # 模块级别 logger

logger.info(f"Prompt created: {prompt_name}")
logger.warning(f"Resource not found: {id}")
logger.exception("Failed to process request")  # 自动包含堆栈
```

#### API 响应格式

统一使用 `BaseResponse`：

```python
from chat2rag.schemas.base import BaseResponse, PaginatedResponse

# 成功响应
return BaseResponse.success(data=user, msg="创建成功")

# 错误响应
return BaseResponse.error(msg="参数错误", code="4000", http_status=400)

# 分页响应
return PaginatedResponse.create(items=users, total=100, current=1, size=10)
```

### TypeScript/Vue 代码风格

#### 类型定义

```typescript
// 使用 interface 定义数据结构
export interface ChatRequest {
  model: string
  collections: string[]
  content: QueryContent
  chatId?: string  // 可选字段用 ?
}

// 使用 type 定义联合类型
export type SourceType = 'command' | 'document' | 'tool' | 'llm'
```

#### 命名约定

- 变量/函数：`camelCase`
- 类型/接口：`PascalCase`
- 常量：`UPPER_SNAKE_CASE` 或 `camelCase`

#### 路径别名

使用 `@/` 代替 `src/`：

```typescript
import { useUserStore } from '@/stores/user'
import type { ChatRequest } from '@/types/chat'
```

---

## 项目特定模式

### Service 单例模式

Service 类在模块末尾创建单例：

```python
class PromptService(CRUDBase[Prompt, PromptCreate, PromptUpdate]):
    ...

prompt_service = PromptService()  # 模块级别单例
```

### Strategy 策略模式

响应处理使用策略链：

```python
from chat2rag.strategies.base import ResponseStrategy

class MyStrategy(ResponseStrategy):
    async def can_handle(self, query: str) -> bool:
        return True  # 判断是否能处理
    
    async def execute(self, query: str) -> AsyncIterator[str]:
        yield "response"  # 流式返回结果
```

### CRUD 基类

继承 `CRUDBase` 获得标准 CRUD 方法：

```python
from chat2rag.core.crud import CRUDBase

class MyService(CRUDBase[Model, CreateSchema, UpdateSchema]):
    def __init__(self):
        super().__init__(Model)
    
    # 自动拥有: get(), create(), update(), remove(), get_list()
```

### 事务处理

使用 `in_transaction` 确保数据一致性：

```python
from tortoise.transactions import in_transaction

async with in_transaction():
    await model.create(...)
    await related_model.create(...)
```

---

## 测试约定

### 测试结构

```python
import pytest
from httpx import AsyncClient

class TestChatBasic:
    """基础聊天测试"""
    
    async def test_chat_basic_success(self, client: AsyncClient, test_prompt, test_model):
        """测试基础聊天成功"""
        response = await client.post("/api/v2/chat", json={...})
        assert response.status_code == 200
```

### Fixture 定义

在 `conftest.py` 或测试文件顶部定义：

```python
@pytest.fixture
async def test_prompt(client: AsyncClient):
    """创建测试用提示词"""
    response = await client.post("/api/v1/prompts", json={...})
    assert response.status_code == 200
    return response.json()["data"]
```

---

## 常见注意事项

1. **不要添加代码注释** - 除非用户明确要求
2. **异步函数优先** - 所有数据库操作使用 `async`
3. **流式响应** - Chat API 使用 `StreamingResponse`
4. **驼峰转换** - API 输出自动转 camelCase，无需手动处理
5. **版本管理** - Prompt 等实体有版本控制，更新时创建新版本而非修改
6. **健康检查** - ModelSource 有 `healthy` 状态，连续失败3次标记为不健康

---

## 文件结构参考

```
chat2rag/
├── api/           # FastAPI 路由
│   ├── v1/        # 旧版 API
│   └── v2/        # 新版 API
├── core/          # 核心模块
│   ├── exceptions.py  # 自定义异常
│   ├── logger.py      # 日志配置
│   └── crud.py        # CRUD 基类
├── models/        # Tortoise ORM 模型
├── schemas/       # Pydantic Schema
│   └── base.py    # 基础 Schema + 响应格式
├── services/      # 业务服务层
├── strategies/    # 响应策略
└── utils/         # 工具函数

web/src/
├── api/           # API 调用函数
├── stores/        # Pinia 状态管理
├── types/         # TypeScript 类型定义
├── views/         # Vue 组件
└── router/        # 路由配置
```