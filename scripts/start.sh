#!/bin/bash
cd /code

uvicorn chat2rag.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --limit-concurrency 500 \
    --timeout-keep-alive 65 \
    --loop uvloop &

# 确保使用正确的 Streamlit 应用路径
# 如果不确定路径，您可以用以下命令查找：
# find . -name "*.py" | grep -i ui
streamlit run chat2rag/ui/app.py

# 防止容器退出
wait
