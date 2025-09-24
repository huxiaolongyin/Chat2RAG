# 待办事项

优先级说明：

- 🔴P1: 紧急且重要，立即处理
- 🟠P2: 重要但不紧急，本迭代完成
- 🟡P3: 常规任务，按计划进行
- 🟢P4: 待定/低优先级，有空闲资源时处理

## 功能新增

- [x] 🟡P3 在数据库中进行 MCP 和 API Tool 的配置
- [x] 🟡P3 新增 管道的性能、查询历史数据写入到数据库
- [x] 🟡P3 新增 管道的性能监控接口，及性能监控页面
- [ ] 🟡P3 添加用户登录界面
- [ ] 🟡P3 新增 大模型长期记忆、历史消息动态摘要处理
- [ ] 🟡P3 RRF检索排行
- [ ] 🟡P3 用户问题自动识别扩展
- [ ] 🟠P2 引入语音识别ASR、语音合成TTS
- [ ] 🟡P3 添加对 doc、pdf、excel、csv 等添加文档处理
- [ ] 🟡P3 新增 对RAG的单元测试和集成测试
- [ ] 🟡P3 新增命令行启动方式
- [ ] 🟡P3 新增一个ORM Service 基类，实现基础增删改查；
- [ ] 🟡P3 新增各个对象的Service服务，将ORM操作集成到Service上
- [ ] 🟡P3 新增 Prompt 的版本管理，记录历史Prompt
- [ ] 🟡P3 流式`stream.py`解析响应内容时，处理TAG内容
- [ ] 🟡P3 widget with key `model_select` 有问题，暂时无法处理

## 性能优化

- [ ] 🟠P2 进行缓存优化，解决首次提问出现卡顿
- [ ] 🟡P3 在init中加入lazy import，参考：[haystack](https://github.com/deepset-ai/haystack/blob/main/haystack/__init__.py)

## BUG 修复

- [ ] 🟢P4 docker 镜像启动顺序影响 后端程序运行
