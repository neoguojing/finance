from typing import Any, Dict

from .config_loader import ConfigLoader
from .features import MarketFeatureEngine, MarketFeatures
from .models import Portfolio


class Rebalancer:
    """计算组合回到目标权重所需的买卖金额。"""

    @staticmethod
    def calculate_rebalance_amounts(portfolio: Portfolio) -> Dict[str, float]:
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
        """Decision Layer 只依赖统一特征，不直接依赖 PE/PB/VIX 等原始指标。"""
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
        """连续倍率函数：评分 0~100 映射为 0.5~3.0。"""
        return 0.5 + 2.5 * max(0.0, min(score, 100.0)) / 100

    @staticmethod
    def position_factor(target_position: float, current_position: float) -> float:
        """仓位修正：越接近目标仓位，买入越少。"""
        if target_position <= 0:
            return 1.0
        return max(0.0, min((target_position - current_position) / target_position, 1.0))

    def cash_safety_factor(self, cash_remaining: float, months_left: int) -> float:
        """现金安全：现金不足或接近建仓结束时降低投入。"""
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

    @staticmethod
    def calculate_contribution_split(portfolio: Portfolio, amount: float, rule: str = "target") -> Dict[str, float]:
        if not portfolio.assets:
            return {}
        if rule == "target":
            return {asset.symbol: amount * asset.target_weight for asset in portfolio.assets}
        if rule != "smart":
            raise ValueError(f"未知规则: {rule}")

        total_value = portfolio.get_total_value()
        if total_value == 0:
            return {asset.symbol: amount * asset.target_weight for asset in portfolio.assets}

        allocation = {asset.symbol: 0.0 for asset in portfolio.assets}
        remaining = amount
        for asset in sorted(
            portfolio.assets,
            key=lambda item: item.target_weight - item.calculate_current_weight(total_value),
            reverse=True,
        ):
            if remaining <= 0:
                break
            needed = (total_value + amount) * asset.target_weight - asset.current_value
            if needed > 0:
                buy = min(needed, remaining)
                allocation[asset.symbol] = buy
                remaining -= buy

        if remaining > 0:
            for asset in portfolio.assets:
                allocation[asset.symbol] += remaining * asset.target_weight
        return allocation
