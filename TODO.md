# 待办事项

优先级说明：

- 🔴P1: 紧急且重要，立即处理
- 🟠P2: 重要但不紧急，本迭代完成
- 🟡P3: 常规任务，按计划进行
- 🟢P4: 待定/低优先级，有空闲资源时处理

## 性能监控

- [ ] 🟡P3 新增 管道的性能、查询历史数据写入到数据库
- [ ] 🟡P3 新增 管道的性能监控接口，及性能监控页面

## 异常处理

- [ ] 🟢P4 使用 `__name__`命名的日志记录器使您可以立即识别日志消息的来源模块：2023-11-15 10:32:15,678 - myapp.core - INFO - 主函数开始执行
- [ ] 🟢P4 加入 try except 异常处理

## 界面优化

<!-- - [ ] 🟡P3 将 streamlit 的UI框架改为 gradio -->
- [ ] 🟡P3 添加用户登录界面

## 性能优化

- [ ] 🟠P2 首次提问出现卡顿
- [ ] 🟡P3 在init中加入lazy import，参考：[haystack](https://github.com/deepset-ai/haystack/blob/main/haystack/__init__.py)

## 交互提升

- [ ] 🟡P3 新增 大模型长期记忆、历史消息动态摘要处理
- [ ] 🟡P3 RRF检索排行
- [ ] 🟡P3 用户问题自动识别扩展
- [ ] 🟠P2 引入语音识别ASR、语音合成TTS

## 文档处理

- [ ] 🟡P3 添加对doc、pdf、excel、csv等添加文档处理

## 测试

- [ ] 🟡P3 新增 对RAG的单元测试和集成测试

## 其他

- [ ] 🟢P4 添加requirements.txt，并在 pyproject.toml 添加为动态参数
- [ ] 🟢P4 docker 镜像启动顺序影响 后端程序运行
- [ ] 🟡P3 修复前端网页的警告：`The widget with key "model_select" was created with a default value but also had its value set via the Session State API.`
- [ ] 🟢P4 将 opentelemetry 监控切换成另一个通用的监控

## 功能
- [x] 🟡P3 在数据库中进行 MCP 和 API Tool 的配置