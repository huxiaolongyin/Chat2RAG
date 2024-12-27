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

CMD ["streamlit", "run", "app.py"]