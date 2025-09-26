FROM python:3.11-slim

WORKDIR /code

# 复制源代码
COPY ./chat2rag ./chat2rag
COPY ./pyproject.toml  .
COPY ./README.md .
COPY ./VERSION.txt .
COPY ./static ./static
COPY ./CHANGELOG.md .

USER root

# Install UV
RUN pip3 install uv 

# 配置pip并安装依赖
RUN uv pip install --system --no-cache-dir . && rm -rf ~/.cache/pip ~/.cache/uv

# 暴露端口
EXPOSE 8051 8000

# 添加启动脚本
COPY ./scripts/start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]