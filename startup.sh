#!/bin/bash

# 确保数据目录存在
mkdir -p ${PERSISTENT_DATA_DIR}

# 设置文件路径（环境变量）
export USER_DB_PATH=${PERSISTENT_DATA_DIR}/users.json
export CONFIG_FILE=${PERSISTENT_DATA_DIR}/config.ini

# 不再手动创建 INI 配置文件，应用启动时会自动创建 JSON 格式的默认配置
# 用户数据库也会由应用自动初始化（创建 admin 用户）

# 修复文件权限（如果文件已存在）
chmod 666 ${CONFIG_FILE} ${USER_DB_PATH} 2>/dev/null || true

# 启动应用（单 worker，避免多进程竞争）
exec gunicorn -w 1 -b 0.0.0.0:12580 app:app
