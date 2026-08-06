import json
from pathlib import Path
from typing import Any, Dict

from .models import Asset, Portfolio


class DataManager:
    """从 weights.json 读取目标权重与当前持仓。"""

    def __init__(self, weights_path: str = "data/weights.json"):
        self.weights_path = Path(weights_path)

    def _load(self) -> Dict[str, Any]:
        if not self.weights_path.exists():
            return {"categories": {}}
        with self.weights_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, data: Dict[str, Any]) -> None:
        with self.weights_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    def load_weights(self) -> Dict[str, Any]:
        return self._load()

    def load_portfolio(self) -> Portfolio:
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

    def update_asset_value(self, symbol: str, value: float) -> None:
        data = self._load()
        for category in data.get("categories", {}).values():
            assets = category.get("assets", {})
            if symbol in assets:
                assets[symbol]["current_value"] = value
                self._save(data)
                return
        data.setdefault("categories", {}).setdefault("未分类", {"weight": 0.0, "assets": {}})["assets"][symbol] = {
            "weight": 0.0,
            "current_value": value,
        }
        self._save(data)

    def bulk_update_asset_values(self, value_map: Dict[str, float]) -> None:
        for symbol, value in value_map.items():
            self.update_asset_value(symbol, value)

    def update_asset_weight(self, symbol: str, weight: float) -> None:
        data = self._load()
        for category in data.get("categories", {}).values():
            assets = category.get("assets", {})
            if symbol in assets:
                assets[symbol]["weight"] = weight
                self._save(data)
                return
