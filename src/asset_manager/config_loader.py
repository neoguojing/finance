import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """加载并生成定投策略配置的工具类。"""

    def __init__(self, config_path: str = "data/config.json"):
        """
        初始化配置加载器。

        Args:
            config_path (str): 配置文件 JSON 的路径。
        """
        self.config_path = Path(config_path)
        self.configs: Dict[str, Any] = self._load_json(self.config_path, self.default_config())

    @staticmethod
    def default_config() -> Dict[str, Any]:
        """
        返回系统的默认配置结构。

        Returns:
            Dict[str, Any]: 包含最大单次投入比例、现金安全策略及决策权重的初始字典。
        """
        return {
            "max_single_invest_percent": 0.1,
            "cash_safety": {"normal": 1.0, "low_cash_or_late_stage": 0.8},
            "assets": {},
        }

    @staticmethod
    def _load_json(path: Path, default: Dict[	str, Any]) -> Dict[str, Any]:
        """从文件路径读取并解析 JSON。"""
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def infer_market(symbol: str, category: str) -> Optional[str]:
        """
        根据资产名称和类别推断市场类型 (US 或 A-share)。

        Args:
            symbol (str): 资产代码或名称。
            category (str): 资产类别（如“股票”、“黄金”）。

        Returns:
            Optional[str]: 如果为美国市场返回 "us"，A股返回 "ashare"，非股票类返回 None。
        """
        if category != "股票":
            return None
        if any(keyword in symbol for keyword in ("标普", "纳斯达克")):
            return "us"
        return "ashare"

    @staticmethod
    def default_metrics(market: str) -> Dict[str, float]:
        """
        针对不同市场返回默认的估值/风险度量指标。

        Args:
            market (str): 市场类型 ("us" 或 "ashare")。

        Returns:
            Dict[str, float]: 包含 PE、PB、VIX 等初始百分位值的字典。
        """
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
        """
        根据权重配置文件 (weights.json) 为所有可定投工具生成完整的资产配置。

        此方法会结合已有的市场度量数据，自动为每个新加入的资产计算其所属市场并初始化指标。

        Args:
            weights (Dict[str, Any]): 包含分类及各资产目标权重的字典。

        Returns:
            Dict[str	str, Any]: 更新后的完整配置对象。
        """
        config = self.default_config()
        config["max_single_invest_percent"] = self.get_setting("max_single_invest_percent", 0.1)
        config["cash_safety"] = self.get_setting("cash_safety", config["cash_safety"])
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
        """将配置持久化到磁盘。"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
        self.configs = config

    def get_assets(self) -> Dict[str, Any]:
        """获取当前配置中所有定投资产的详细信息。"""
        return self.configs.get("assets", {})

    def get_asset_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """查询特定资产的完整配置数据。"""
        return self.get_assets().get(symbol)

    def get_market_metrics(self, symbol: str) -> Dict[str, float]:
        """获取特定资产当前的各类市场度量指标 (如 PE 分位)。"""
        asset = self.get_asset_config(symbol) or {}
        return asset.get("metrics", {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        """从配置字典中安全地提取单项设置参数。"""
        return self.configs.get(key, default)
