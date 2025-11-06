# Changelog

这个项目的所有值得注意的变化都将记录在这个文件中。

这个格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，还有这个原则遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [V0.3.0rc2] - 2025-11-06
### Added
- 新增模型渠道管理和模型列表管理Model、Service、Schema及API
- 新增chat2rag各个组件使用模型渠道及管理，取消或降低对CONFIG配置的依赖
- 新增定时1小时刷新模型延迟

### Removed
- 移除重复无用`doc_pipeline.py`文件
- 移除无用 `shot_name.py` 文件

## [V0.3.0rc1] - 2025-11-03
### Added
- 项目重构
    - 升级依赖包版本
    - 将 ORM 从 `SQLAlchemy` 改为支持异步的 `Tortoise-ORM` 
    - 重构 `Agent` 和 `RAG` 管道为异步管道
    - 重构缓存方法为异步
    - 将工具管理改为 `tool_service` 管理
    - 整体模块目录重构，如 `chat2rag.api.schema` 调整为 `chat2rag.schemas`，`chat2rag.api.model` 调整为 `chat2rag.models` 等
    - 配置、枚举及响应目录简化为单一文件，减少复杂性 
- 【重要更新】策略模块及策略链：
    - 实现模块化策略能力，灵活控制大模型 chat 接口返回策略组合，如 V1 接口使用「精准模式策略+RAG策略」，V2 接口使用「命令策略+流程策略+精准模式策略+Agent策略」
- 【重要更新】优化 `flow` 流程管理，改进入点、转移点和退出点判断逻辑
- 【重要更新】新增 command、flow、metric、prompt、sensitive、tool 的 service 层实现数据库 ORM 操作 
- 【重要更新】加入 MCP 连接管理器，管理连接生命周期
- 【重要更新】新增自动化测试，包含接口测试(`tests.test_api`)及数据库模拟(`conftest`)，保证测试安全无侵入
- 【重要更新】为便于部署，移入内部`MCP`独立服务(导航等)，并进行单独`config`配置及初始化sql服务等
- 新增敏感词接口和命令词接口
- 新增 `logger.py` 中接口入参自动记录装饰器
- 新增 makefile 快速启动 mcp服务的命令

### Changed
- 优化 `TODO.md` 

### Fixed
- 修复对话轮数获取异常，能够正常获取`user->assistant`的正常对话轮，配置 `chat_rounds` 为当前对话+历史对话的轮数，`chat_rounds=1` 则只有当前对话

### Removed
- 移除无用 mysql 容器配置（docker-compose.yml）  
- 移除无用的 `chat2rag.component`  
- 移除多线程 executor，改为异步实现  
- 移除 `SQLAlchemy` 连接及管理相关代码 `chat2rag.database`


## [V0.2.4] - 2025-10-10
### Added
- 增加对 csv 文件的解析
- 新增指标搜索中，对知识库(场景下)的过滤
- 简化工具管理代码逻辑
- 新增交互记录返回场景内容
- 新增场景(知识库)下的分布饼图
- 优化指标查询布局
- 新增交互记录指标更多字段，包含提示词、对话ID，轮数，工具调用等
- 模型常量集中到 CONFIG 进行配置，新增 QWEN3 其他模型
- Chat V1接口的 prompt 增加当前时间，增加场景信息(知识库)
- 优化 旧UI 的 render 代码逻辑，新增阈值、topK的控制，新增清除会话的功能
- 优化Chat V1接口的输出逻辑，对符号在任意位置都可分段
- 新增 Deepseek V3.1 模型
- Chat V1接口新增对模型、精准模式的记录

### Fixed
- 处理当 collection 为空时的异常
- 修复精准模式参数错乱
- 添加SSE响应头，修复精准模式下SSE流异常
- 部分模型不支持 enable_thinking 参数，去除固定的写法，关联到模型表中

### Removed
- 删除 ChatUI 上，不使用的功能组件

## [V0.2.3] - 2025-09-24
### Added
- 新增 makefile 构建和运行命令，自动读取 VERSION.txt 作为变量
- 新增通用缓存管道创建器，支持将可变参数转换为可哈希格式
- 恢复 v1 版本的 chat 接口，并对其进行优化
- 对 prompt 在获取分页数据时按创建时间降序排序记录
- 新增状态机流程FlowData 模型及相关 API，支持流程数据的创建、获取、更新和删除
- 加强交互表现力，支持动作、表情、图片和链接标记的解析与处理
- 新增音频配置模型，重命名流程字段，优化请求参数描述
- 将 ChatUI 的按钮、选择器组件和状态包装成函数
- 版本更新内容，直接通过接口提供
- 交互记录加入对v1 接口的监控

### Changed
- 调整项目依赖，更新 arize-phoenix 到 11.35.0，旧版会报错
- 修改 dockerfile 构建文件
- 调整异步执行器到全局，支持在独立线程中运行异步协程
- ChatUI 调整为 V1 的 chat 接口，地址接口调整为本地8000
- 将 ChatUI 中的 st.button 旧参数 `use_container_width=True` 替换为 `width='stretch'`

### Fixed
- 修正 example/RAGPipeline 导入路径，确保正确引用

### Removed
- 移除冗余日志和冗余导入

## [V0.2.2] - 2025-09-12
### Added
- 新增 Qwen3 14B 和 Qwen3 32B的模型
- 使用 json 尝试格式化输出 Tool Result
- 为数据库迁移集成 Alembic，并在应用启动时初始化迁移
- 重构流处理以提高性能和工具调用支持
- 新增交互对话记录和响应记录
- 新增交互记录、及响应指标查询接口，方便查询和分析用户交互数据。
- 新增 管道的性能监控接口，及性能监控页面
- 新增表情、动作、工具类型、链接的字段
- 新增 chat v2 接口，移除参数 vin、city、time 等，由 extra_params 替代
- 新增状态机控制大模型交互输出内容
- 新增本地挂载 Swagger UI 所需静态内容

### Changed
- 修改 webUI 默认工具，设置为空
- 重构数据模型和数据库连接，从 chat2rag/core/database 移动到 chat2rag/database 下

### Fixed
- 增强BaseModel的to_dict方法，支持 datetime 类型转换
- 将 PostgreSQL 容器的时区设置为中国时区，解决时区问题
- 修复精准模式下，新增聊天历史记录，使用 ChatRole 枚举替代字符串标识用户和助手角色

## [V0.2.1] - 2025-07-04
### Added
- 新增 Agent管道，融合MCP、RAG、ToolInvoke
- 新增 Agent管道示例
- 新增 MCP中streamable模式的支持
- 新增 使用 SerperDevWebSearch进行网页搜索的功能
- 优化 Agent Pipeline，支持 ToolCall 和 ToolResult 流式输出
- 新增 MCP工具名的映射，使用AI对工具描述进行取名
- 新增 streamlit ui 上增加工具选择、网络搜索、优化模型选择

### Fixed
- 移除 get_bazi_info 工具，直接`+`似乎有问题

### Changed
- 修改 Base Pipeline，加入泛型变量，支持更多类型的 Pipeline
- 增强工具管理， 并修改 tool 接口
- 修改 Function Pipeline(将弃用)，添加 Funciton 示例
- 修改 RAG Pipeline(将弃用)，添加 RAG 示例
- 修改 api/v1/chat 接口，使用Agent 管道进行输出内容
- 优化 短记忆 chat_history 内容，将 ChatMessage 集成到一个函数内

### Removed
- 移除 内置的天气服务，使用高德 MCP 代替
- 移除 内置的微博检索工具
- 移除 yml管理工具集

## [V0.2.0] - 2025-06-25

### Added

- 新增 ASR 的服务(暂未全部接入)
- 新增 TTS 的服务(暂未全部接入)
- 在 prompt 中添加基础信息：时间、vin、地点
- 新增 汉特云内部mcp服务
- 新增 tool v2 接口，进行 MCP 和 api tool 的增删改查.
- 新增 对多个 MCP 服务的处理，增加单例模式进行MCP的连接
- 支持 多个知识库的检索
- 新增 makefile 文件启动 后端和前端

### Fixed

- 修复 qdrant-haystack 升级到 9.2.0，导致 qdrant.py 无法使用的问题
- 修复 chat 接口修改导致的 collection 参数问题

### Changed

- 将 frontend、rag_core、backend 整合到chat2rag中
- 将天气查询改为高德 MCP
- 更新 document 从 str -> DocumentType 类型
- 将管道的 warmup() 改到 base 中
- 更新 haystack 和相关依赖
- 优化冗余的配置文件，统一到 config.py 中

### Removed

- 移除 语音交互的 html

## [V0.1.2] - 2025-02-20

### Added

- 新增 数据库postgresql的使用
- 新增 Prompt 查询、修改接口，并支持大模型切换 Prompt
- 新增 web端的模型切换、提示词切换

### Fixed

- WEB 重新刷新取消弹出欢迎页
- 精准模式回答的日志
- embedding 服务存活检测及服务切换（暂时取消服务切换）
- WEB 端，弹出的参考文档和大模型使用的不一致，由非精准检索，检索到问题导致
- batch的分段根据chunk结尾的符号进行分割，某些情况下，大模型返回的chunk的符号在中间，导致分段有问题

## [V0.1.1] - 2025-01-16

### Added

- 新增精准模式匹配，在精准模式下，将优先进行问题的匹配，然后再进行文档的匹配，从而提高匹配的准- 确性。
- 新增知识内容的搜索功能
- 新增知识数据导出的功能
- 在知识写入时，拆分为问题，问题-答案，进行向量的存储
- 在消息中新增 uuid
- 在环境变量中进行 function 的启用

### Fixed

- 修复若干 bug
- 修复管道时间计算的问题
- 修复不能删除没有meta的知识的问题

## [V0.1.0] - 2025-01-10

### Added

- 新增 RAG 流式、批式 交流
- 新增 函数调用功能
- 新增 知识库的增删改查、导入导出
- 新增 docker / docker compose 部署
