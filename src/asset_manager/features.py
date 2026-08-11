from .config_loader import ConfigLoader

class MarketFeatureEngine:
    """从配置中提取市场指标的简单引擎。"""

    @staticmethod
    def get_indicator_value(config_loader: ConfigLoader, symbol: str, indicator: str) -> float:
        """
        获取指定资产的特定指标值。

        Args:
            config_loader (ConfigLoader): 配置加载器。
            symbol (str): 资产代码。
            indicator (str): 需要获取的指标名称（如 'pe_percentile'）。

        Returns:
            float: 指标的当前数值。如果未找到，返回 50.0 作为基准值。
        """
        metrics = config_loader.get_market_metrics(symbol)
        if not metrics:
            return 50.0
        return metrics.get(indicator, 50.0)
