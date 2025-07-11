#!/bin/bash

# 确保数据目录存在
mkdir -p ${PERSISTENT_DATA_DIR}

# 设置文件路径
USER_DB_PATH=${PERSISTENT_DATA_DIR}/users.json
CONFIG_FILE=${PERSISTENT_DATA_DIR}/config.ini

# 确保配置文件存在
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Creating default config file at ${CONFIG_FILE}"
    echo '[DEFAULT]' > ${CONFIG_FILE}
    echo 'stock1 =' >> ${CONFIG_FILE}
    echo 'stock2 =' >> ${CONFIG_FILE}
fi

# 确保用户数据库存在
if [ ! -f "${USER_DB_PATH}" ]; then
    echo "Creating default users database at ${USER_DB_PATH}"
    echo '{}' > ${USER_DB_PATH}
    
    # 添加默认用户
    python -c 'from authentication import AuthManager; auth_mgr = AuthManager("'${USER_DB_PATH}'"); auth_mgr.user_dao.add_user("admin", "password")'
fi

# 修复文件权限
chmod 666 ${CONFIG_FILE} ${USER_DB_PATH} 2>/dev/null || true

# 设置环境变量（关键：传递给应用）
export USER_DB_PATH
export CONFIG_FILE

# 启动应用
exec gunicorn -w 4 -b 0.0.0.0:12580 app:app
