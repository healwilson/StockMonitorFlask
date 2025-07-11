import jwt
import datetime
import functools
import logging
from flask import request, make_response

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AuthManager")

# 安全密钥
SECRET_KEY = "healwilson"

class AuthManager:
    def __init__(self, user_db_path):
        self.user_db_path = user_db_path
        logger.info(f"Initialized with user DB path: {user_db_path}")
        
        # 初始化 UserDAO
        from user_dao import UserDAO
        self.user_dao = UserDAO(user_db_path)
        logger.info("UserDAO initialized")
    
    def login(self, username, password):
        """验证用户凭据并生成JWT令牌"""
        logger.info(f"Login attempt for user: {username}")
        
        if not self.user_dao.validate_user(username, password):
            logger.warning(f"Invalid credentials for user: {username}")
            return None

        # 生成JWT令牌
        token = jwt.encode({
            'sub': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }, SECRET_KEY, algorithm='HS256')
        
        logger.info(f"Login successful for user: {username}")
        return token

    def update_account(self, current_username, new_username, new_password, current_password):
        """更新用户账户信息（用户名和/或密码）"""
        logger.info(f"Account update request: {current_username} -> {new_username}")
        
        # 验证并更新账户信息
        success, message = self.user_dao.update_account(
            current_username,
            new_username,
            new_password,
            current_password
        )
        
        if success:
            logger.info(f"Account updated successfully: {message}")
        else:
            logger.error(f"Account update failed: {message}")
            
        return success, message

    def authenticate_request(self):
        """验证请求是否包含有效的JWT令牌"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            return False, "Missing authentication token"

        token = auth_header.split(" ")[1]
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            username = payload['sub']
            logger.info(f"Authenticated user: {username}")
            return True, username
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return False, "Invalid token"

    def protected_route(self, func):
        """用于保护路由的装饰器"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            valid, response = self.authenticate_request()
            if not valid:
                logger.warning("Unauthorized access attempt")
                return make_response({'error': response}, 401)
            return func(*args, **kwargs)

        return wrapper
    
    def is_authenticated(self):
        """检查用户是否已认证"""
        valid, _ = self.authenticate_request()
        return valid
