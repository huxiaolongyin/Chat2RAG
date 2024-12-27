FROM bitnami/pytorch:2.1.2

WORKDIR /code

# 只复制依赖相关文件,利用缓存
COPY ./pyproject.toml  .
COPY ./README.md .

# 复制源代码
COPY ./backend ./backend
COPY ./rag_core ./rag_core

USER root

# 配置pip并安装依赖
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir .

EXPOSE 8000

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000",\
    "--limit-concurrency","500",\
    "--timeout-keep-alive","65",\
    "--loop", "uvloop"]
# CMD ["gunicorn", "src.main:app", "-w" ,"4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--max-requests", "1000"]