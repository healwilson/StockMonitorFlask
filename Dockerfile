FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PERSISTENT_DATA_DIR=/data \
    USER_DB_PATH=/data/users.json \
    CONFIG_FILE=/data/config.ini \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai  

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sudo \
    tzdata && \  
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

RUN useradd -m -s /bin/bash python && \
    usermod -aG sudo python && \
    echo "python ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

RUN mkdir -p /data && \
    chown -R python:python /data && \
    chmod -R 775 /data

COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir pandas==1.5.3 && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件（包含你最新的 index.html、main.js 等）
COPY . .

RUN chmod +x startup.sh

EXPOSE 12580

USER python
CMD ["./startup.sh"]
