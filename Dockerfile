# 1. 使用官方 Python 镜像
FROM python:3.13-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制 src 目录的所有内容到容器 /app 路径下
COPY src/ /app/

# 如果有需要安装的依赖，确保在 src 目录里包含 requirements.txt
# 如果没有就注释掉下面这行
RUN pip install --no-cache-dir -r requirements.txt\
&& pip install  uvicorn
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/pip/*
# 4. 使用 uvicorn 启动应用
# 如果你想使用 reload 方便开发，可以加上 --reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]