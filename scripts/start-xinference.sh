#!/bin/bash
xinference-local -H 0.0.0.0 --log-level debug &

# 使用 curl 循环检测服务是否就绪
until curl -s http://localhost:9997/status > /dev/null; do
    echo "Waiting for xinference service to be ready..."
    sleep 2
    
done

echo "Xinference service is ready!"

# 检查服务是否启动，如果启动则加载模型
xinference launch --model-name 360Zhinao-search --model-type embedding

exec tail -f /dev/nul
# xinference launch --model-name 360Zhinao-search --model-type embedding