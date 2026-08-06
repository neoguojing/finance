from dataclasses import dataclass
from typing import List

@dataclass
class Asset:
    """
    资产类：代表一个具体的投资工具（如 ETF）。

    属性:
        symbol (str): 资产唯一标识符（如 "510300" 或 "SPY"）。
        current_value (float): 该资产在组合中的当前市值。
        target_weight (float): 预设的目标权重 (0.0 - 1.0)。
        category (str): 资产类别（如 "股票"、"债券"、"黄金"）。
    """
    symbol: str
    current_value: float
    target_weight: float
    category: str

    def calculate_current_weight(self, total_portfolio_value: float) -> float:
        """
        计算该资产在当前整体投资组合中所占的实际权重。

        Args:
            total_portfolio_value (float): 整个投资组合的总价值。

        Returns:
            float: 当前实际权重（current_value / total_portfolio_value）。若总值为0则返回0.0。
        """
        if total_portfolio_value == 0:
            return 0.0
        return self.current_value / total_portfolio_value

@dataclass
class Portfolio:
    """
    投资组合类：管理一组 Asset 对象，并提供整体统计功能。

    属性:
        assets (List[Asset]): 包含所有资产实例的列表。
    """
    assets: List[Asset]

    def get_total_value(self) -> float:
        """
        计算整个投资组合中所有资产价值的总和。

        Returns:
            float: 组合总市值。
        """
        return sum(asset.current_value for asset in self.assets)
