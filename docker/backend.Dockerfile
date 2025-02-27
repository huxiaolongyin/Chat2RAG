FROM python:3.9-slim

# 使用清华源加速apt
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list 

# 只更新curl相关的包索引
RUN apt-get update -o Dir::Etc::sourcelist="sources.list" \
    -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# 只复制依赖相关文件,利用缓存
COPY ./pyproject.toml  .
COPY ./README.md .
COPY ./VERSION.txt .

# 复制源代码
COPY ./backend ./backend
COPY ./rag_core ./rag_core

USER root

# Install UV
RUN pip3 install uv -i https://mirrors.aliyun.com/pypi/simple/

# 配置pip并安装依赖
RUN uv pip install --system --no-cache-dir . -i https://mirrors.aliyun.com/pypi/simple/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000",\
    "--limit-concurrency","500",\
    "--timeout-keep-alive","65",\
    "--loop", "uvloop"]

# 多核服务器可使用这个
# CMD ["gunicorn", \
#     "--bind", "0.0.0.0:8000", \
#     "--preload", \
#     "--worker-connections", "200", \ 
#     "-k", "uvicorn.workers.UvicornWorker", \
#     "--timeout", "120", \
#     "--max-requests", "1000", \
#     "backend.main:app"]
