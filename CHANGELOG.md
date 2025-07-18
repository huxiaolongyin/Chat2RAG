# Changelog

这个项目的所有值得注意的变化都将记录在这个文件中。

这个格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，还有这个原则遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]
### Added
- 新增 Qwen3 14B 和 Qwen3 32B的模型
- 使用 json 尝试格式化输出 Tool Result
- 为数据库迁移集成Alembic，并在应用启动时初始化迁移
- 重构流处理以提高性能和工具调用支持
- 新增交互对话记录和响应记录
- 新增交互记录、及响应指标查询接口，方便查询和分析用户交互数据。
- 新增 管道的性能监控接口，及性能监控页面

### Changed
- 修改 webUI 默认工具，设置为空
- 修改 chat 接口，移除参数vin、city、time等，由 extra_params 替代
- 重构数据模型和数据库连接，从 chat2rag/core/database 移动到chat2rag/database 下

## Fixed
- 增强BaseModel的to_dict方法，支持datetime类型转换

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

## Fixed

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
