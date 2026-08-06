from typing import Any, Dict

from .config_loader import ConfigLoader
from .features import MarketFeatureEngine, MarketFeatures
from .models import Portfolio


class Rebalancer:
    """计算组合回到目标权重所需的买卖金额。"""

    @staticmethod
    def calculate_rebalance_amounts(portfolio: Portfolio) -> Dict[str, float]:
        """
        计算每个资产为了达到目标权重需要买入或卖出的金额。

        算法逻辑:
            对于每个资产，计算 (目标权重 * 组合总价值) - 当前持仓价值。
            结果为正表示需要买入，结果为负表示需要卖出。

        Args:
            portfolio (Portfolio): 当前的投资组合对象，包含所有资产的当前价值和目标权重。

        Returns:
            Dict[str, float]: 键为资产代码(symbol)，值为对应的交易金额。
        """
        total_value = portfolio.get_total_value()
        if total_value == 0:
            return {asset.symbol: 0.0 for asset in portfolio.assets}
        return {
            asset.symbol: total_value * asset.target_weight - asset.current_value
            for asset in portfolio.assets
        }


class DCAEngine:
    """长期 ETF 定投评分引擎。"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    @staticmethod
    def market_score(features: MarketFeatures, weights: Dict[str, float] = None) -> float:
        """
        计算市场综合得分。

        算法逻辑:
            采用加权平均法。将不同维度的特征分数（估值、情绪、宏观、趋势、波动）
            乘以预设的权重，得到一个 0-100 之间的总分。

        Args:
            features (MarketFeatures): 从市场数据中提取出的标准化特征对象。
            weights (Dict[str, float], optional): 各个维度的权重分配。如果未提供，则使用默认权重。

        Returns:
            float: 最终的市场评分 (0.0 - 100.0)。
        """
        weights = weights or {
            "valuation_score": 0.50,
            "sentiment_score": 0.15,
            "macro_score": 0.15,
            "momentum_score": 0.20,
            "volatility_score": 0.00,
        }
        values = features.to_dict()
        return sum(values[key] * weight for key, weight in weights.items())

    @staticmethod
    def market_multiplier(score: float) -> float:
        """
        根据市场得分计算定投倍率。

        算法 逻辑:
            使用连续线性映射函数，将 0-100 的评分区间映射到 0.5-3.0 的倍率区间。
            分值越高（代表越安全/越便宜），定投金额的倍数越大。

        Args:
            score (float): 市场综合得分 (0.0 - 100.0)。

        Returns:
            float: 计算出的定投放大/缩小倍率 (0.5 - 3.0)。
        """
        return 0.5 + 2.5 * max(0.0, min(score, 100.0)) / 100

    @staticmethod
    def position_factor(target_position: float, current_position: float) -> float:
        """
        计算仓位修正因子。

        算法逻辑:
            采用“向目标靠拢”策略。
            当当前持仓距离目标仓位较远时，因子趋近于 1.0 (全额投入)；
            当当前持仓已接近或超过目标仓位时，因子趋近于 0.0 (停止投入)。

        Args:
            target_position (float): 计划达到的目标总金额。
            current_position (float): 当前已持有的资产价值。

        Returns:
            float: 仓位调节系数 (0.0 - 1.0)。
        """
        if target_position <= 0:
            return 1.0
        return max(0.0, min((target_position - current_position) / target_position, 1.0))

    def cash_safety_factor(self, cash_remaining: float, months_left: int) -> float:
        """
        计算现金安全系数。

        算法逻辑:
            考虑资金链风险和建仓阶段。
            如果剩余现金过低或者处于建仓周期的最后阶段，则主动降低投入力度以防断供。

        Args:
            cash_remaining (float): 当前可用的总现金金额。
            months_left (int): 计划定投剩余的月数。

        Returns:
            float: 安全系数 (通常为 0.8 或 1.0)。
        """
        settings = self.config_loader.get_setting("cash_safety", {})
        if cash_remaining <= 0 or months_left <= 1:
            return settings.get("low_cash_or_late_stage", 0.8)
        return settings.get("normal", 1.0)

    def calculate_investment(
        self,
        symbol: str,
        cash_remaining: float,
        months_left: int,
        current_position: float,
        target_weight: float,
        planned_total: float,
    ) -> Dict[str, Any]:
        """
        计算特定资产在本期的建议定投金额。

        算法核心公式:
            建议投入 = 基础月度额度 * 市场倍率 * 仓位因子 * 现金安全系数
            其中：
                1. 基础月度额度 (Base) = (剩余总现金 / 剩余月数) * 目标权重
                2. 市场倍率 (Multiplier): 基于估值、情绪等特征计算，分值高则放大投入。
                3. 仓位因子 (Position Factor): 当前持仓越接近目标，投入越少。
                4. 现金安全系数 (Safety Factor): 资金紧缺或末期时减少投入。

        Args:
            symbol (str): 资产代码（如 "510300"）。
            cash_remaining (float): 当前可用的总现金金额。
            months_left (int): 计划定投剩余的月数。
            current_position (float): 该资产当前的持仓市值。
            target_weight (float): 该资产在组合中的目标权重 (0.0 - 1.0)。
            planned_total (float): 整个投资计划的总规模（当前价值 + 剩余现金）。

        Returns:
            Dict[str, Any]: 包含本次定投建议金额、各因子计算结果及市场特征的字典。
        """
        asset = self.config_loader.get_asset_config(symbol)
        if not asset:
            return {"error": f"未找到定投资产配置: {symbol}"}

        base = cash_remaining / months_left * target_weight if months_left > 0 else 0.0
        target_position = planned_total * target_weight
        metrics = self.config_loader.get_market_metrics(symbol)
        market = asset.get("market")
        features = MarketFeatureEngine.build(market, metrics)
        score = self.market_score(features, self.config_loader.get_feature_weights(symbol))
        multiplier = self.market_multiplier(score)
        position = self.position_factor(target_position, current_position)
        safety = self.cash_safety_factor(cash_remaining, months_left)
        raw = base * multiplier * position * safety
        max_percent = self.config_loader.get_setting("max_single_invest_percent", 0.10)
        final = min(raw, cash_remaining * max_percent)

        return {
            "symbol": symbol,
            "investment": final,
            "investment_ratio": 0.0,
            "base_amount": base,
            "target_position": target_position,
            "market_multiplier": multiplier,
            "position_factor": position,
            "cash_safety_factor": safety,
            "market_score": score,
            "features": features.to_dict(),
        }

    def calculate_plan(self, portfolio: Portfolio, cash_remaining: float, months_left: int) -> Dict[str, Any]:
        """
        计算整个投资组合在当前阶段的定投执行计划。

        算法逻辑:
            遍历所有配置在可定投名单中的资产，利用 `calculate_investment` 逐个计算本期建议金额，
            并统计总投入额度和各资产在本期投入中所占的比例。

        Args:
            portfolio (Portfolio): 当前持仓组合对象。
            cash_remaining (float): 当前可用的总现金金额。
            months_left (int): 计划定投剩余的月数。

        Returns:
            Dict[int, Any]: 包含本期建议总投入金额 (`total_investment`) 和各个资产详细计算结果的列表 (`items`)。
        """
        planned_total = portfolio.get_total_value() + cash_remaining
        dca_symbols = set(self.config_loader.get_assets())
        results = []
        for asset in portfolio.assets:
            if asset.symbol not in dca_symbols:
                continue
            result = self.calculate_investment(
                symbol=asset.symbol,
                cash_remaining=cash_remaining,
                months_left=months_left,
                current_position=asset.current_value,
                target_weight=asset.target_weight,
                planned_total=planned_total,
            )
            if "error" not in result:
                results.append(result)

        total_investment = sum(item["investment"] for item in results)
        for item in results:
            item["investment_ratio"] = item["investment"] / total_investment if total_investment > 0 else 0.0
        return {"total_investment": total_investment, "items": results}
