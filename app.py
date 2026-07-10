import os
import sys
import threading
import logging
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainApp")

CONFIG_FILE = os.getenv('CONFIG_FILE', '/data/config.ini')
USER_DB_PATH = os.getenv('USER_DB_PATH', '/data/users.json')

logger.info(f"Using config file: {CONFIG_FILE}")
logger.info(f"Using user database: {USER_DB_PATH}")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from config import ConfigManager
    from authentication import AuthManager
    from data import DataService, StockMonitorApp, MultiPairManager
except ImportError as e:
    logger.error(f"Import error: {e}")
    try:
        from .config import ConfigManager
        from .authentication import AuthManager
        from .data import DataService, StockMonitorApp, MultiPairManager
    except ImportError:
        logger.error("Failed to import required modules")
        exit(1)

app = Flask(__name__, template_folder='templates')
CORS(app)

config_manager = ConfigManager(CONFIG_FILE)
auth_manager = AuthManager(USER_DB_PATH)

# 全局多 pair 管理器
pair_manager = None
pair_manager_lock = threading.Lock()

if not os.path.exists(CONFIG_FILE):
    logger.info("Creating default config file")
    config_manager._create_default_config()

try:
    if not os.path.exists(USER_DB_PATH):
        logger.info("Creating default user")
        auth_manager.user_dao.add_user("admin", "password")
except Exception as e:
    logger.error(f"Failed to create default user: {e}")

def init_pair_manager():
    global pair_manager
    config = config_manager.load_config()
    pair_manager = MultiPairManager(config)
    logger.info(f"Initialized with {len(pair_manager.apps)} pairs, active: {pair_manager.active_pair_id}")

init_pair_manager()

def ensure_default_user():
    try:
        if not os.path.exists(USER_DB_PATH):
            logger.info("User database not found, creating default user")
            auth_manager.user_dao.add_user("admin", "password")
            logger.info("Default user admin/password created")
        else:
            users = auth_manager.user_dao.users
            if 'admin' not in users:
                logger.info("Admin user missing, recreating")
                auth_manager.user_dao.add_user("admin", "password")
    except Exception as e:
        logger.error(f"Failed to ensure default user: {e}")
        try:
            import json
            from werkzeug.security import generate_password_hash
            from datetime import datetime
            default_users = {
                'admin': {
                    'password': generate_password_hash('password'),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            }
            os.makedirs(os.path.dirname(USER_DB_PATH), exist_ok=True)
            with open(USER_DB_PATH, 'w') as f:
                json.dump(default_users, f, indent=2)
            logger.info("Default user created via fallback")
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")

ensure_default_user()

# ---------- 认证路由 ----------
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

@app.route('/auth/update-account', methods=['POST'])
def update_account():
    data = request.json
    current_username = data.get('current_username')
    new_username = data.get('new_username')
    new_password = data.get('new_password')
    current_password = data.get('current_password')
    if not current_username or not current_password:
        return jsonify({'error': 'Current username and password are required'}), 400
    success, message = auth_manager.update_account(current_username, new_username, new_password, current_password)
    if success:
        return jsonify({'status': 'success', 'message': message})
    else:
        return jsonify({'error': message}), 400

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/')
def root():
    return redirect('/login')

@app.route('/app')
def main_app():
    return send_from_directory('.', 'index.html')

# ---------- 多 pair API ----------
@app.route('/api/pairs')
@auth_manager.protected_route
def get_pairs():
    with pair_manager_lock:
        pair_ids = pair_manager.get_pair_ids()
        active = pair_manager.active_pair_id
        # 不再自动修复，让前端处理无效 active
    return jsonify({"pairs": pair_ids, "active": active})

@app.route('/api/add-pair', methods=['POST'])
@auth_manager.protected_route
def add_pair():
    data = request.json
    code1 = data.get('stock1', '').strip()
    code2 = data.get('stock2', '').strip()
    if not code1 or not code2:
        return jsonify({"error": "两个股票代码都不能为空"}), 400
    with pair_manager_lock:
        pid = pair_manager.add_pair(code1, code2)
        config = config_manager.load_config()
        pair_list = [[app_obj.stocks[0]['code'], app_obj.stocks[1]['code']] for app_obj in pair_manager.apps.values()]
        config["pairs"] = pair_list
        config["active_pair"] = pair_manager.active_pair_id
        config_manager.save_config(config)
    return jsonify({"pair_id": pid, "status": "added"})

@app.route('/api/remove-pair', methods=['POST'])
@auth_manager.protected_route
def remove_pair():
    data = request.json
    pid = data.get('pair_id')
    if not pid:
        return jsonify({"error": "pair_id is required"}), 400
    with pair_manager_lock:
        if pid not in pair_manager.apps:
            return jsonify({"error": "Pair not found"}), 404
        pair_manager.remove_pair(pid)
        config = config_manager.load_config()
        pair_list = [[app_obj.stocks[0]['code'], app_obj.stocks[1]['code']] for app_obj in pair_manager.apps.values()]
        config["pairs"] = pair_list
        config["active_pair"] = pair_manager.active_pair_id
        config_manager.save_config(config)
    return jsonify({"status": "removed"})

@app.route('/api/switch-pair', methods=['POST'])
@auth_manager.protected_route
def switch_pair():
    data = request.json
    pid = data.get('pair_id')
    if not pid:
        return jsonify({"error": "pair_id is required"}), 400
    with pair_manager_lock:
        if pid not in pair_manager.apps:
            return jsonify({"error": "Pair not found"}), 404
        pair_manager.switch_to(pid)
        config = config_manager.load_config()
        config["active_pair"] = pid
        config_manager.save_config(config)
    return jsonify({"status": "switched", "active": pid})

# ---------- 获取数据（支持指定 pair） ----------
@app.route('/api/get-data')
@auth_manager.protected_route
def get_data():
    pair_id = request.args.get('pair', None)
    with pair_manager_lock:
        if pair_id and pair_id in pair_manager.apps:
            target_app = pair_manager.apps[pair_id]
        else:
            target_app = pair_manager.get_active_app()
        if target_app is None:
            return jsonify({"error": "No pair configured"}), 400

        data = target_app.get_frontend_data()
        index_codes = [
            "sh000001", "sz399001", "sz399006", "sh000688",
            "sh000016", "sh000300", "sh000905", "sh000852"
        ]
        index_data = DataService.get_realtime_data(index_codes)
        for i, code in enumerate(index_codes, 1):
            data[f"index{i}"] = index_data.get(code, {"name": f"指数{i}", "price": 0.0, "changePercent": 0.0})
    return jsonify(data)

# ---------- 兼容旧版配置接口 ----------
@app.route('/api/config')
@auth_manager.protected_route
def get_config():
    with pair_manager_lock:
        app_obj = pair_manager.get_active_app()
        if app_obj:
            return jsonify({"stock1": app_obj.stocks[0]['code'], "stock2": app_obj.stocks[1]['code']})
        return jsonify({"stock1": "", "stock2": ""})

@app.route('/api/update-stocks', methods=['POST'])
@auth_manager.protected_route
def update_stocks():
    data = request.json
    stock1 = data.get('stock1', '').strip()
    stock2 = data.get('stock2', '').strip()
    if not stock1 or not stock2:
        return jsonify({"error": "股票代码不能为空"}), 400
    with pair_manager_lock:
        pid = f"{stock1}-{stock2}"
        if pid not in pair_manager.apps:
            pair_manager.add_pair(stock1, stock2)
        pair_manager.switch_to(pid)
        config = config_manager.load_config()
        pair_list = [[app_obj.stocks[0]['code'], app_obj.stocks[1]['code']] for app_obj in pair_manager.apps.values()]
        config["pairs"] = pair_list
        config["active_pair"] = pid
        config_manager.save_config(config)
    return jsonify({"status": "success"})

# ---------- 其他路由 ----------
@app.route('/auth/clear-cache', methods=['POST'])
def clear_auth_cache():
    auth_manager.user_dao.users = auth_manager.user_dao._load_users()
    logger.info("Auth cache cleared")
    return jsonify({"status": "success"})

@app.route('/<path:path>')
def serve_static(path):
    allowed_extensions = ('.js', '.css', '.png', '.jpg', '.ico', '.html')
    if path.startswith('api/') or path == 'api':
        return None
    if path == 'login.html' or path == 'index.html' or path == '':
        return send_from_directory('.', path if path else 'index.html')
    if path.endswith(allowed_extensions):
        return send_from_directory('.', path)
    return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=12580, debug=False)
