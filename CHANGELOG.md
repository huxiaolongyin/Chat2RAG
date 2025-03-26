# Changelog

这个项目的所有值得注意的变化都将记录在这个文件中。

这个格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，还有这个原则遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unrelesed]

### Added

- 新增 ASR 的服务
- 新增 TTS 的服务

### Changed

- 将 frontend、rag_core、backend 整合到chat2rag中

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
