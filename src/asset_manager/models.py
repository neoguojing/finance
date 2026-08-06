from dataclasses import dataclass
from typing import List

@dataclass
class Asset:
    """
    资产类：代表一个具体的投资工具。

    属性:
        symbol (str): 资产唯一标识符（如股票代码或名称）。
        current_value (float): 该资产当前的市场总价值。
        target_weight (float): 该资产在组合中的目标权重（0.0 到 1.0）。
        category (str): 资产类别（如：股票、债券、现金）。
    """
    symbol: str
    current_value: float
    target_weight: float
    category: str

    def calculate_current_weight(self, total_portfolio_value: float) -> float:
        """
        计算该资产在当前组合中的实际权重。

        输入:
            total_portfolio_value (float): 整个投资组合的总价值。
        输出:
            float: 该资产的实际权重（current_value / total_portfolio_value）。
        """
        if total_portfolio_value == 0:
            return 0.0
        return self.current_value / total_portfolio_value

@dataclass
class Portfolio:
    """
    投资组合类：管理一组资产并计算整体指标。

    属性:
        assets (List[Asset]): 包含所有 Asset 对象的列表。
    """
    assets: List[Asset]

    def get_total_value(self) -> float:
        """
        计算整个投资组合的总价值。

        输出:
            float: 所有资产 current_value 的总和。
        """
        return sum(asset.current_value for asset in self.assets)

    def get_allocation_drift(self) -> List[tuple]:
        """
        计算所有资产的权重偏差（Drift）。

        输出:
            List[tuple]: 一个元组列表，每个元组包含 (资产标识符, 权重偏差)。
                         偏差 = 目标权重 - 实际权重。
        """
        total_value = self.get_total_value()
        drifts = []
        for asset in self.assets:
            current_weight = asset.calculate_current_weight(total_value)
            drifts.append((asset.symbol, asset.target_weight - current_weight))
        return drifts
