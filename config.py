import os
import json
import logging

logger = logging.getLogger("ConfigManager")

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.default_config = {
            "pairs": [["sh600519", "sz000858"]],
            "active_pair": "sh600519-sz000858"
        }

    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}
            logger.warning("Config file not found or invalid, using defaults")

        # 兼容旧版 stock1/stock2 格式
        if "stock1" in config and "stock2" in config:
            code1 = config.pop("stock1")
            code2 = config.pop("stock2")
            config["pairs"] = [[code1, code2]]
            config["active_pair"] = f"{code1}-{code2}"
            logger.info("Migrated old config format to new pairs format")

        # 补全缺失字段
        for key, val in self.default_config.items():
            config.setdefault(key, val)

        # 确保 active_pair 存在于 pairs 中
        if config["active_pair"] not in [f"{a}-{b}" for a,b in config["pairs"]]:
            config["active_pair"] = f"{config['pairs'][0][0]}-{config['pairs'][0][1]}" if config["pairs"] else ""

        return config

    def save_config(self, config):
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
