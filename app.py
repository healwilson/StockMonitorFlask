import os
import sys
import threading
import logging
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainApp")

# 确保从环境变量获取路径
CONFIG_FILE = os.getenv('CONFIG_FILE', '/data/config.ini')
USER_DB_PATH = os.getenv('USER_DB_PATH', '/data/users.json')

logger.info(f"Using config file: {CONFIG_FILE}")
logger.info(f"Using user database: {USER_DB_PATH}")

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from config import ConfigManager
    from authentication import AuthManager
    from data import DataService, StockMonitorApp
except ImportError as e:
    logger.error(f"Import error: {e}")
    # 尝试相对导入
    try:
        from .config import ConfigManager
        from .authentication import AuthManager
        from .data import DataService, StockMonitorApp
    except ImportError:
        logger.error("Failed to import required modules")
        exit(1)

app = Flask(__name__, template_folder='templates')
CORS(app)  # 允许跨域请求

# 初始化配置管理器和认证管理器
config_manager = ConfigManager(CONFIG_FILE)
auth_manager = AuthManager(USER_DB_PATH)

# 全局监控实例和锁
monitor = None
monitor_lock = threading.Lock()

# 确保配置文件存在
if not os.path.exists(CONFIG_FILE):
    logger.info("Creating default config file")
    config_manager._create_default_config()

# 创建默认用户（仅用于演示）
try:
    if not os.path.exists(USER_DB_PATH):
        logger.info("Creating default user")
        auth_manager.user_dao.add_user("admin", "password")
except Exception as e:
    logger.error(f"Failed to create default user: {e}")

# 认证路由
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    token = auth_manager.login(username, password)
    if token:
        return jsonify({'token': token}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

# 修改账户信息路由
@app.route('/auth/update-account', methods=['POST'])
def update_account():
    data = request.json
    current_username = data.get('current_username')
    new_username = data.get('new_username')
    new_password = data.get('new_password')
    current_password = data.get('current_password')

    if not current_username or not current_password:
        return jsonify({'error': 'Current username and password are required'}), 400

    # 验证并更新账户信息
    success, message = auth_manager.update_account(
        current_username,
        new_username,
        new_password,
        current_password
    )

    if success:
        return jsonify({'status': 'success', 'message': message})
    else:
        return jsonify({'error': message}), 400

# 登录页面
@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

# 根路径重定向到登录
@app.route('/')
def root():
    return redirect('/login')

# 主应用页面
@app.route('/app')
def main_app():
    return send_from_directory('.', 'index.html')

# API路由 - 配置管理
@app.route('/api/config')
@auth_manager.protected_route
def get_config():
    config = config_manager.load_config()
    logger.info(f"Returning config: {config}")
    return jsonify(config)

@app.route('/api/update-stocks', methods=['POST'])
@auth_manager.protected_route
def update_stocks():
    data = request.json
    stock1 = data.get('stock1')
    stock2 = data.get('stock2')
    
    logger.info(f"Updating stocks: {stock1}, {stock2}")

    if not (stock1 and stock2):
        return jsonify({"error": "股票代码不能为空"}), 400

    # 保存新配置前先清除旧缓存
    with monitor_lock:
        global monitor
        
        # 获取旧股票代码
        old_stock1 = config_manager.load_config().get("stock1", "")
        old_stock2 = config_manager.load_config().get("stock2", "")
        
        logger.info(f"Clearing cache for old stocks: {old_stock1}, {old_stock2}")
        
        # 清除旧股票代码的缓存
        DataService.clear_stock_cache(old_stock1)
        DataService.clear_stock_cache(old_stock2)
        
        # 保存新配置
        new_config = {"stock1": stock1, "stock2": stock2}
        success = config_manager.save_config(new_config)
        if not success:
            logger.error("Failed to save config")
            return jsonify({"error": "保存配置失败"}), 500
        
        # 更新监控实例
        monitor = StockMonitorApp(new_config)
        logger.info("Monitor instance updated with new config")
    
    return jsonify({"status": "success"})

# API路由 - 获取数据
@app.route('/api/get-data')
@auth_manager.protected_route
def get_data():
    with monitor_lock:
        global monitor
        if monitor is None:
            # 从配置文件加载
            config = config_manager.load_config()
            monitor = StockMonitorApp(config)
        
        config_data = config_manager.load_config()
        stock1 = config_data.get("stock1", "")
        stock2 = config_data.get("stock2", "")
        
        # 确保监控实例使用最新配置
        if (monitor.stocks[0]['code'] != stock1 or 
            monitor.stocks[1]['code'] != stock2):
            logger.warning("Monitor config mismatch, resetting")
            monitor = StockMonitorApp(config_data)
        
        if not stock1 or not stock2:
            logger.warning("Stock codes not configured, returning empty data")
            return jsonify({
                "stock1": {"code": "", "name": "Not Configured", "price": 0.0, "changePercent": 0.0},
                "stock2": {"code": "", "name": "Not Configured", "price": 0.0, "changePercent": 0.0},
                "diff": {"current": 0.0},
                "intraday": {"data": [], "stats": {}},
                "fiveDay": {"data": [], "stats": {}},
                "stock1ChartData": {"prices": [], "times": [], "change_percent": []},
                "stock2ChartData": {"prices": [], "times": [], "change_percent": []},
                "index1": {"name": "上证指数", "price": 0.0, "changePercent": 0.0},
                "index2": {"name": "深证成指", "price": 0.0, "changePercent": 0.0},
                "index3": {"name": "创业板指", "price": 0.0, "changePercent": 0.0},
                "index4": {"name": "科创50", "price": 0.0, "changePercent": 0.0},
                "index5": {"name": "上证50", "price": 0.0, "changePercent": 0.0},
                "index6": {"name": "沪深300", "price": 0.0, "changePercent": 0.0},
                "index7": {"name": "中证500", "price": 0.0, "changePercent": 0.0},
                "index8": {"name": "中证1000", "price": 0.0, "changePercent": 0.0}
            })

        data = monitor.get_frontend_data()
        return jsonify(data)

# 添加缓存清除接口
@app.route('/auth/clear-cache', methods=['POST'])
def clear_auth_cache():
    # 强制重新加载用户数据
    auth_manager.user_dao.users = auth_manager.user_dao._load_users()
    logger.info("Auth cache cleared")
    return jsonify({"status": "success"})

# 静态文件服务
@app.route('/<path:path>')
def serve_static(path):
    # 允许访问的文件类型
    allowed_extensions = ('.js', '.css', '.png', '.jpg', '.ico', '.html')
    
    # 检查是否是API请求
    if path.startswith('api/') or path == 'api':
        return None  # Flask将自动调用对应的API路由
    
    # 检查是否是登录页或主应用页
    if path == 'login.html' or path == 'index.html' or path == '':
        return send_from_directory('.', path if path else 'index.html')
    
    # 检查文件扩展名是否允许
    if path.endswith(allowed_extensions):
        return send_from_directory('.', path)
    
    # 其他情况重定向到登录页
    return redirect('/login')

if __name__ == "__main__":
    # 创建监控实例
    config = config_manager.load_config()
    logger.info(f"Starting with config: {config}")
    
    # 只有在配置了股票代码时才创建监控实例
    if config.get("stock1") and config.get("stock2"):
        with monitor_lock:
            monitor = StockMonitorApp(config)
    
    # 启动后端
    app.run(host='0.0.0.0', port=12580, debug=False)
