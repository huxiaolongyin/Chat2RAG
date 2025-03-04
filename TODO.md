# Project Roadmap

这是一个长期更新的Road Map，用于记录项目的发展方向和计划。

## v0.1.3

### 🚀 New Features
- [ ] 新增 语音识别STT、语音合成TTS
- [ ] 新增 大模型长期记忆、历史消息动态摘要处理
- [ ] RRF检索排行
- [ ] 用户问题自动识别扩展

### 🐛 Bug Fixe
- [ ] 首次提问出现卡顿

### 🔧 Technical improve
- [ ] 将 streamlit 的UI框架改为 gradio

### 📚 Docs Complete
- [ ] xxx

## v0.1.2

### 🚀 New Features

- [X] 新增 数据库postgresql的使用
- [X] 新增 Prompt 查询、修改接口，并支持大模型切换 Prompt
- [ ] 新增 管道的性能、查询历史数据写入到数据库
- [ ] 新增 管道的性能监控接口，及性能监控页面
- [X] 新增 web端的模型切换、提示词切换

### 🐛 Bug Fixe

- [X] WEB 重新刷新取消弹出欢迎页
- [X] 精准模式回答的日志
- [X] embedding 服务存活检测及服务切换（暂时取消服务切换）
- [X] WEB 端，弹出的参考文档和大模型使用的不一致，由非精准检索，检索到问题导致
- [ ] batch的分段有问题
