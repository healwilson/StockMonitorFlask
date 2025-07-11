import configparser
import os
import logging

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.logger = logging.getLogger("ConfigManager")
        self.logger.info(f"Initialized with config path: {config_path}")
    
    def load_config(self):
        self.logger.info(f"Loading config from {self.config_path}")
        
        if not os.path.exists(self.config_path):
            self.logger.warning("Config file not found, creating default")
            return self._create_default_config()
        
        try:
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            stock1 = config.get('DEFAULT', 'stock1', fallback='')
            stock2 = config.get('DEFAULT', 'stock2', fallback='')
            
            self.logger.info(f"Loaded config: stock1={stock1}, stock2={stock2}")
            return {
                "stock1": stock1,
                "stock2": stock2
            }
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return {"stock1": "", "stock2": ""}
    
    def save_config(self, config):
        self.logger.info(f"Saving config to {self.config_path}: {config}")
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            parser = configparser.ConfigParser()
            parser['DEFAULT'] = {
                'stock1': config.get('stock1', ''),
                'stock2': config.get('stock2', '')
            }
            
            with open(self.config_path, 'w') as f:
                parser.write(f)
            
            # 设置权限确保可写
            os.chmod(self.config_path, 0o666)
            self.logger.info("Config saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            return False
    
    def _create_default_config(self):
        default_config = {
            "stock1": "",
            "stock2": ""
        }
        self.save_config(default_config)
        return default_config
