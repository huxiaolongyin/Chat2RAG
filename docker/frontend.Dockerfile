FROM python:3.9-slim

WORKDIR /frontend

# 复制源代码
COPY ./frontend .

USER root

# 安装依赖
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 install --no-cache-dir -r requirements.txt 

# 暴露端口
EXPOSE 8051

# 安装健康检查的依赖
RUN apt update && apt install -y curl

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501 || exit 1

CMD ["streamlit", "run", "app.py"]