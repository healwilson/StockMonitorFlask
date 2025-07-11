import json
import os
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UserDAO")

class UserDAO:
    def __init__(self, db_path):
        self.db_path = db_path
        logger.info(f"Initialized with DB path: {db_path}")
        self.users = self._load_users()
        logger.info(f"Loaded {len(self.users)} users")
    
    def _load_users(self):
        """从JSON文件加载用户数据"""
        try:
            # 确保文件存在
            if not os.path.exists(self.db_path):
                logger.warning(f"User database file not found: {self.db_path}")
                logger.info("Creating new user database")
                return self._save_users({})
            
            # 检查文件可读性
            if not os.access(self.db_path, os.R_OK):
                logger.warning(f"User database not readable: {self.db_path}")
                logger.info("Attempting to fix permissions")
                try:
                    os.chmod(self.db_path, 0o666)
                    logger.info("Permissions fixed")
                except Exception as e:
                    logger.error(f"Failed to fix permissions: {str(e)}")
            
            # 加载用户数据
            with open(self.db_path, 'r') as f:
                users = json.load(f)
                logger.info(f"Loaded {len(users)} users from {self.db_path}")
                return users
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in user database")
            return {}
        except Exception as e:
            logger.error(f"Error loading user database: {str(e)}")
            return {}

    def _save_users(self, data=None):
        """将用户数据保存到JSON文件"""
        try:
            data = data or self.users
            logger.info(f"Saving {len(data)} users to {self.db_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # 写入文件
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # 设置可写权限
            try:
                os.chmod(self.db_path, 0o666)
                logger.info(f"Set permissions to 666 for {self.db_path}")
            except Exception as e:
                logger.warning(f"Could not set permissions: {str(e)}")
            
            return data
        except Exception as e:
            logger.error(f"Error saving user database: {str(e)}")
            return {}

    def add_user(self, username, password):
        """添加新用户"""
        if username in self.users:
            logger.warning(f"User creation failed: username '{username}' already exists")
            return False

        self.users[username] = {
            "password": generate_password_hash(password),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if self._save_users():
            logger.info(f"User '{username}' created successfully")
            return True
        return False

    def get_user(self, username):
        """获取用户信息"""
        return self.users.get(username)

    def validate_user(self, username, password):
        """验证用户凭据"""
        user = self.get_user(username)
        if not user:
            logger.warning(f"Login attempt for non-existent user: {username}")
            return False
            
        if check_password_hash(user["password"], password):
            logger.info(f"Successful login for user: {username}")
            return True
            
        logger.warning(f"Failed login attempt for user: {username}")
        return False

    def update_account(self, current_username, new_username, new_password, current_password):
        """更新用户账户信息"""
        logger.info(f"Updating account: {current_username} -> {new_username}")
        
        # 验证当前用户凭据
        if not self.validate_user(current_username, current_password):
            logger.warning(f"Account update failed: invalid credentials for {current_username}")
            return False, "当前密码错误"
        
        # 检查新用户名是否可用
        if new_username and new_username != current_username:
            if new_username in self.users:
                logger.warning(f"Account update failed: username '{new_username}' already exists")
                return False, "新用户名已被使用"
        
        # 处理用户名变更
        if new_username and new_username != current_username:
            # 迁移用户数据
            self.users[new_username] = self.users.pop(current_username)
            current_username = new_username
            logger.info(f"Username changed to: {new_username}")
        
        # 处理密码变更
        if new_password:
            self.users[current_username]["password"] = generate_password_hash(new_password)
            logger.info("Password updated")
        
        # 更新更新时间
        self.users[current_username]["updated_at"] = datetime.now().isoformat()
        
        # 保存更改
        if self._save_users():
            logger.info("Account changes saved successfully")
            return True, "账户信息更新成功"
        
        logger.error("Failed to save account changes")
        return False, "保存失败"
