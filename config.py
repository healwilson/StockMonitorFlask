import json
import threading
import logging

logger = logging.getLogger("ConfigManager")

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self._lock = threading.Lock()  # 新增线程锁
        self.default_config = {
            "pairs": [["sh600519", "sz000858"]],
            "active_pair": "sh600519-sz000858"
        }

    def load_config(self):
        with self._lock:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config = {}
                logger.warning("Config file not found or invalid, using defaults")

            # 兼容旧格式
            if "stock1" in config and "stock2" in config:
                code1 = config.pop("stock1")
                code2 = config.pop("stock2")
                config["pairs"] = [[code1, code2]]
                config["active_pair"] = f"{code1}-{code2}"
                logger.info("Migrated old config format")

            # 补全缺失字段
            for key, val in self.default_config.items():
                config.setdefault(key, val)

            # 确保 active_pair 有效
            valid_ids = [f"{a}-{b}" for a, b in config.get("pairs", [])]
            if config["active_pair"] not in valid_ids:
                config["active_pair"] = valid_ids[0] if valid_ids else ""
                logger.warning(f"Reset active_pair to {config['active_pair']}")

            return config

    def save_config(self, config):
        with self._lock:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info("Config saved successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                return False

    def _create_default_config(self):
        self.save_config(self.default_config)
