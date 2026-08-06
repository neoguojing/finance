import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """加载并生成定投策略配置。"""

    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = Path(config_path)
        self.configs: Dict[str, Any] = self._load_json(self.config_path, self.default_config())

    @staticmethod
    def default_config() -> Dict[str, Any]:
        return {
            "max_single_invest_percent": 0.1,
            "cash_safety": {"normal": 1.0, "low_cash_or_late_stage": 0.8},
            "decision_weights": {
                "valuation_score": 0.50,
                "sentiment_score": 0.15,
                "macro_score": 0.15,
                "momentum_score": 0.20,
                "volatility_score": 0.00,
            },
            "assets": {},
        }

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def infer_market(symbol: str, category: str) -> Optional[str]:
        if category != "股票":
            return None
        if any(keyword in symbol for keyword in ("标普", "纳斯达克")):
            return "us"
        return "ashare"

    @staticmethod
    def default_metrics(market: str) -> Dict[str, float]:
        if market == "us":
            return {
                "forward_pe_percentile": 50.0,
                "peg_percentile": 50.0,
                "vix": 20.0,
                "fed_rate_percentile": 50.0,
                "drawdown": 0.0,
            }
        return {
            "pe_percentile": 50.0,
            "pb_percentile": 50.0,
            "erp_percentile": 50.0,
            "drawdown": 0.0,
        }

    def generate_from_weights(self, weights: Dict[str, Any]) -> Dict[str, Any]:
        """基于 weights.json 为可定投工具生成配置，保留已有指标。"""
        config = self.default_config()
        config["max_single_invest_percent"] = self.get_setting("max_single_invest_percent", 0.1)
        config["cash_safety"] = self.get_setting("cash_safety", config["cash_safety"])
        config["decision_weights"] = self.get_setting("decision_weights", config["decision_weights"])
        old_assets = self.get_assets()

        for category, category_data in weights.get("categories", {}).items():
            for symbol in category_data.get("assets", {}):
                market = self.infer_market(symbol, category)
                if not market:
                    continue
                old_asset = old_assets.get(symbol, {})
                config["assets"][symbol] = {
                    "market": old_asset.get("market", market),
                    "metrics": old_asset.get("metrics", self.default_metrics(market)),
                }
        return config

    def save(self, config: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
        self.configs = config

    def get_assets(self) -> Dict[str, Any]:
        return self.configs.get("assets", {})

    def get_asset_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.get_assets().get(symbol)

    def get_market_metrics(self, symbol: str) -> Dict[str, float]:
        asset = self.get_asset_config(symbol) or {}
        return asset.get("metrics", {})

    def get_feature_weights(self, symbol: str) -> Dict[str, float]:
        asset = self.get_asset_config(symbol) or {}
        return asset.get("decision_weights", self.get_setting("decision_weights", {}))

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.configs.get(key, default)
