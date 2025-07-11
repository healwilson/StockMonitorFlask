FROM python:3.9-slim

WORKDIR /app

# 使用环境变量定义存储路径
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PERSISTENT_DATA_DIR=/data \
    USER_DB_PATH=/data/users.json \
    CONFIG_FILE=/data/config.ini \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai  

# 安装必要的系统包
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sudo \
    tzdata && \  
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 配置时区为上海
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# 创建应用用户
RUN useradd -m -s /bin/bash python && \
    usermod -aG sudo python && \
    echo "python ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# 创建数据目录并设置权限
RUN mkdir -p /data && \
    chown -R python:python /data && \
    chmod -R 775 /data

# 复制项目文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir pandas==1.5.3 && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 确保启动脚本有执行权限
RUN chmod +x startup.sh

# 暴露端口
EXPOSE 12580

# 启动应用
USER python
CMD ["./startup.sh"]
