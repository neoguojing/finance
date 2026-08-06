import json
import os
from typing import Dict, Any, Optional

class ConfigLoader:
    """
    配置加载器：负责从 data/config.json 中按资产符号加载参数。
    """
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = config_path
        self.configs: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            print(f"Warning: Config file {self.config_path} not found.")
            return {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file {self.config_path}: {e}")
            return {}

    def get_asset_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取特定资产的配置参数"""
        return self.configs.get(symbol)
