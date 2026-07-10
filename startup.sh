#!/bin/bash

# 确保数据目录存在
mkdir -p ${PERSISTENT_DATA_DIR}

# 设置文件路径
USER_DB_PATH=${PERSISTENT_DATA_DIR}/users.json
CONFIG_FILE=${PERSISTENT_DATA_DIR}/config.ini

# 不再手动创建 config.ini，应用启动时会自动生成 JSON 格式的默认配置
# 用户数据库也会由应用自动初始化（创建 admin 用户）

# 设置环境变量（传递给应用）
export USER_DB_PATH
export CONFIG_FILE

# 启动应用
exec gunicorn -w 4 -b 0.0.0.0:12580 app:app
