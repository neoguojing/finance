import json
from pathlib import Path
from typing import Any, Dict

from .models import Asset, Portfolio


class DataManager:
    """负责从 weights.json 配置文件中持久化读取目标权重与当前持仓数据。"""

    def __init__(self, weights_path: str = "data/weights.json"):
        """
        初始化数据管理器。

        Args:
            weights_path (str): 存储资产权重、类别及当前价值的 JSON 文件路径。
        """
        self.weights_path = Path(weights_path)

    def _load(self) -> Dict[str, Any]:
        """从磁盘加载原始 JSON 配置数据。"""
        if not self.weights_path.exists():
            return {"categories": {}}
        with self.weights_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, data: Dict[str, Any]) -> None:
        """将更新后的数据结构写回磁盘。"""
        with self.weights_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    def load_weights(self) -> Dict[str, Any]:
        """获取所有资产的配置权重数据。"""
        return self._load()

    def load_portfolio(self) -> Portfolio:
        """
        从配置文件中重建当前的投资组合对象 (Portfolio)。

        该方法会遍历 JSON 中的 categories 结构，将每个资产条目转换为 Asset 实例，
        并关联其当前市值与目标权重。

        Returns:
            Portfolio: 构建完成的投资组合对象。
        """
        assets = []
        for category, category_data in self._load().get("categories", {}).items():
            for symbol, asset_data in category_data.get("assets", {}).items():
                assets.append(
                    Asset(
                        symbol=symbol,
                        current_value=float(asset_data.get("current_value", 0.0)),
                        target_weight=float(asset_data.get("weight", 0.0)),
                        category=category,
                    )
                )
        return Portfolio(assets=assets)
