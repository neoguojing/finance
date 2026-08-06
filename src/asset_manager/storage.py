import json
import os
from typing import List, Dict, Any
from .models import Asset, Portfolio

class DataManager:
    """
    数据管理类：负责资产配置数据和持仓数据的读取与保存。
    现在所有数据统一存储在 weights.json 中。
    """
    def __init__(self, weights_path: str = "data/weights.json"):
        """
        初始化数据管理器。

        输入:
            weights_path (str): 资产配置与持仓统一 JSON 文件的路径。
        """
        self.weights_path = weights_path
        self.holdings_path = "data/holdings.json"  # 保留用于迁移

    def load_portfolio(self) -> Portfolio:
        """
        从 JSON 文件中加载资产权重和持仓，并构建 Portfolio 对象。

        输出:
            Portfolio: 包含所有资产及其当前权重和价值的投资组合对象。
        """
        if not os.path.exists(self.weights_path):
            return Portfolio(assets=[])

        # 1. 加载主配置文件
        with open(self.weights_path, 'r', encoding='utf-8') as f:
            weights_data = json.load(f)

        # 2. 迁移逻辑：如果存在旧的 holdings.json，将其合并到 weights.json
        if os.path.exists(self.holdings_path):
            with open(self.holdings_path, 'r', encoding='utf-8') as f:
                old_holdings = json.load(f)

            migrated = False
            categories = weights_data.get("categories", {})
            for symbol, data in old_holdings.items():
                val = data["actual"] if isinstance(data, dict) and "actual" in data else data

                # 在现有类别中寻找该资产
                found = False
                for cat_name, cat_info in categories.items():
                    assets = cat_info.get("assets", {})
                    if symbol in assets:
                        # 转换为新格式: weight -> {weight, current_value}
                        rel_weight = assets[symbol]
                        if not isinstance(rel_weight, dict):
                            assets[symbol] = {"weight": rel_weight, "current_value": float(val)}
                        else:
                            assets[symbol]["current_value"] = float(val)
                        found = True
                        migrated = True
                        break

                if not found:
                    # 添加到 General 类别
                    if "General" not in categories:
                        categories["General"] = {"weight": 0.0, "assets": {}}
                    gen_assets = categories["General"]["assets"]
                    if symbol in gen_assets:
                        rel_weight = gen_assets[symbol]
                        if not isinstance(rel_weight, dict):
                            gen_assets[symbol] = {"weight": rel_weight, "current_value": float(val)}
                        else:
                            gen_assets[symbol]["current_value"] = float(val)
                    else:
                        gen_assets[symbol] = {"weight": 0.0, "current_value": float(val)}
                    migrated = True

                if migrated:
                    self.save_weights(weights_data)
                    try:
                        os.remove(self.holdings_path)
                    except OSError:
                        pass

        # 3. 解析嵌套结构并计算绝对权重
        assets = []
        categories = weights_data.get("categories", {})
        for cat_name, cat_info in categories.items():
            cat_weight = cat_info.get("weight", 0.0)
            assets_in_cat = cat_info.get("assets", {})
            for symbol, asset_data in assets_in_cat.items():
                # 处理两种格式：旧的简单 float 权重 或 新的 dict 格式
                if isinstance(asset_data, dict):
                    rel_weight = asset_data.get("weight", 0.0)
                    current_value = asset_data.get("current_value", 0.0)
                else:
                    rel_weight = asset_data
                    current_value = 0.0

                abs_weight = rel_weight
                assets.append(Asset(
                    symbol=symbol,
                    current_value=float(current_value),
                    target_weight=float(abs_weight),
                    category=cat_name
                ))

        return Portfolio(assets=assets)

    def save_weights(self, weights: Dict[str, Any]):
        """
        保存目标权重及持仓配置到 JSON 文件。
        """
        with open(self.weights_path, 'w', encoding='utf-8') as f:
            json.dump(weights, f, indent=4, ensure_ascii=False)

    def _update_and_save(self, update_fn):
        """辅助方法：加载 -> 更新 -> 保存"""
        with open(self.weights_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        update_fn(data)
        self.save_weights(data)

    def update_asset_value(self, symbol: str, value: float):
        """
        更新特定资产的当前市场价值并持久化。
        """
        def update(data):
            categories = data.get("categories", {})
            for cat_name, cat_info in categories.items():
                assets = cat_info.get("assets", {})
                if symbol in assets:
                    # 确保是字典格式
                    if not isinstance(assets[symbol], dict):
                        assets[symbol] = {"weight": assets[symbol], "current_value": 0.0}
                    assets[symbol]["current_value"] = value
                    return

            # 如果没找到，添加到 General
            if "General" not in categories:
                categories["General"] = {"weight": 0.0, "assets": {}}
            gen_assets = categories["General"]["assets"]
            if symbol in gen_assets:
                if not isinstance(gen_assets[symbol], dict):
                    gen_assets[symbol] = {"weight": gen_assets[symbol], "current_value": 0.0}
                gen_assets[symbol]["current_value"] = value
            else:
                gen_assets[symbol] = {"weight": 0.0, "current_value": value}

        self._update_and_save(update)

    def bulk_update_asset_values(self, value_map: Dict[str, float]):
        """
        批量更新多个资产的当前市场价值并一次性持久化。
        """
        def update(data):
            categories = data.get("categories", {})
            for symbol, value in value_map.items():
                found = False
                for cat_name, cat_info in categories.items():
                    assets = cat_info.get("assets", {})
                    if symbol in assets:
                        if not isinstance(assets[symbol], dict):
                            assets[symbol] = {"weight": assets[symbol], "current_value": 0.0}
                        assets[symbol]["current_value"] = value
                        found = True
                        break
                if not found:
                    if "General" not in categories:
                        categories["General"] = {"weight": 0.0, "assets": {}}
                    gen_assets = categories["General"]["assets"]
                    if symbol in gen_assets:
                        if not isinstance(gen_assets[symbol], dict):
                            gen_assets[symbol] = {"weight": gen_assets[symbol], "current_value": 0.0}
                        gen_assets[symbol]["current_value"] = value
                    else:
                        gen_assets[symbol] = {"weight": 0.0, "current_value": value}

        self._update_and_save(update)

    def update_asset_weight(self, symbol: str, weight: float):
        """
        更新目标权重并持久化。
        如果 symbol 是类别名，则更新类别总权重。
        如果 symbol 是资产名，则更新其在类别内的相对权重。
        """
        def update(data):
            categories = data.setdefault("categories", {})
            # 1. 检查是否为类别名
            if symbol in categories:
                categories[symbol]["weight"] = weight
                return

            # 2. 检查是否为已有资产
            for cat_name, cat_info in categories.items():
                assets = cat_info.get("assets", {})
                if symbol in assets:
                    # 保持字典格式
                    if not isinstance(assets[symbol], dict):
                        assets[symbol] = {"weight": weight, "current_value": 0.0}
                    else:
                        assets[symbol]["weight"] = weight
                    return

            # 3. 新资产：添加到 "General" 类别
            if "General" not in categories:
                categories["General"] = {"weight": 1.0, "assets": {}}
            gen_assets = categories["General"]["assets"]
            if symbol in gen_assets:
                if not isinstance(gen_assets[symbol], dict):
                    gen_assets[symbol] = {"weight": weight, "current_value": 0.0}
                else:
                    gen_assets[symbol]["weight"] = weight
            else:
                gen_assets[symbol] = {"weight": weight, "current_value": 0.0}

        self._update_and_save(update)
