# For more information, please refer to https://aka.ms/vscode-docker-python
# 构建阶段
FROM python:3.13-slim as builder

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
&& pip install  uvicorn
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/pip/*
WORKDIR /app
COPY /src /app

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["unicorn", "--host", "0.0.0.0", "-port", "8000", "main:app"]
