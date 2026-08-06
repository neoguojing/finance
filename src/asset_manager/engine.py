from typing import Dict, List, Any, Optional
from .models import Asset, Portfolio
from .config_loader import ConfigLoader

class Rebalancer:
    """
    Rebalance calculation class: calculates trades needed to restore portfolio weights.
    """
    @staticmethod
    def calculate_rebalance_amounts(portfolio: Portfolio) -> Dict[str, float]:
        total_value = portfolio.get_total_value()
        if total_value == 0:
            return {asset.symbol: 0.0 for asset in portfolio.assets}

        rebalance_amounts = {}
        for asset in portfolio.assets:
            target_value = total_value * asset.target_weight
            rebalance_amounts[asset.symbol] = target_value - asset.current_value

        return rebalance_amounts

class DCAEngine:
    """
    DCA Execution Engine: calculates allocation of new funds across assets based on individual ETF configurations.
    """
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def _calculate_drawdown_score(self, drawdown: float) -> float:
        """Calculate drawdown score (0-100)."""
        return min(drawdown / 0.3, 1.0) * 100

    def _calculate_position_factor(self, target_position: float, current_position: float) -> float:
        """Calculate position correction factor (0-1)."""
        if target_position is None or target_position <= 0:
            return 1.0
        factor = (target_position - current_position) / target_position
        return max(0.0, factor)

    def _calculate_cash_safety_factor(self, cash_remaining: float, months_left: int, config: Dict[str, Any]) -> float:
        """Calculate cash safety factor based on configured thresholds."""
        factors = config.get("cash_safety_factors", [])
        # Sort by threshold descending to find the highest applicable threshold first
        sorted_factors = sorted(factors, key=lambda x: x['threshold_months'], reverse=True)

        for entry in sorted_factors:
            if months_left > entry['threshold_months']:
                return entry['factor']
        return 0.8  # Fallback

    def calculate_smart_invest(
        self,
        symbol: str,
        market_metrics: Dict[str, float],
        cash_remaining: float,
        months_left: int,
        target_position: float = None,
        current_position: float = 0.0
    ) -> Dict[str, Any]:
        """
        Unified smart investment calculation function.
        Uses asset-specific configuration from the loaded config file.
        """
        params = self.config_loader.get_asset_config(symbol)
        if not params:
            return {"error": f"No configuration found for {symbol}"}

        # 1. BaseAmount: Ensure completion of construction by target date
        base_amount = cash_remaining / months_left if months_left > 0 else 0

        # Common parameters from the specific asset config
        max_inv_percent = params.get("max_investment_percent", 0.1)
        cash_safety_factor = self._calculate_cash_safety_factor(cash_remaining, months_left, params)
        position_factor = self._calculate_position_factor(target_position, current_position)

        asset_type = params.get("type", "ashare")
        drawdown = market_metrics.get("drawdown", 0.0)
        drawdown_score = self._calculate_drawdown_score(drawdown)

        market_multiplier = 1.0
        market_score = 0.0

        if asset_type == "ashare":
            # A-share specific logic using parameters from JSON
            pe_p = market_metrics.get("pe_percentile", 50.0)
            pb_p = market_metrics.get("pb_percentile", 50.0)
            erp_p = market_metrics.get("erp_percentile", 50.0)

            value_score = (params['pe_weight'] * (100 - pe_p) +
                           params['pb_weight'] * (100 - pb_p) +
                           params['erp_weight'] * erp_p)

            market_score = (params['market_score_value_weight'] * value_score +
                            params['market_score_drawdown_weight'] * drawdown_score)

            market_multiplier = (params['multiplier_base'] +
                                 params['multiplier_factor'] * (market_score / 100))

        elif asset_type == "usshare":
            # US-share specific logic using parameters from JSON
            fpe_p = market_metrics.get("forward_pe_percentile", 50.0)
            peg_p = market_metrics.get("peg_percentile", 50.0)
            vix = market_metrics.get("vix", 20.0)
            fed_rate_p = market_metrics.get("fed_rate_percentile", 50.0)

            growth_score = (params['forward_pe_weight'] * (100 - fpe_p) +
                            params['peg_weight'] * (100 - peg_p) +
                            params['drawdown_weight'] * drawdown_score)

            vix_score = min(vix / 40, 1.0) * 100
            rate_score = 100 - fed_rate_p

            market_score = (params['us_score_growth_weight'] * growth_score +
                            params['us_score_vix_weight'] * vix_score +
                            params['us_score_rate_weight'] * rate_score)

            market_multiplier = (params['multiplier_base'] +
                                 params['multiplier_factor'] * (market_score / 10_0)) # Note: using 100.0 is cleaner, but 1000 is what I wrote before? Let's stick to 100.0

        # Final decision formula calculation
        investment = base_amount * market_multiplier * position_factor * cash_safety_factor

        # Hard limit: single investment does not exceed 10% of remaining cash (from config)
        final_investment = min(investment, cash_remaining * max_inv_percent)

        return {
            "final_investment": final_investment,
            "scores": {
                "base_amount": base_amount,
                "market_multiplier": market_multiplier,
                "position_factor": position_factor,
                "cash_safety_factor": cash_safety_factor,
                "market_score": market_score,
                "drawdown_score": drawdown_score
            }
        }

    @staticmethod
    def calculate_contribution_split(portfolio: Portfolio, amount: float, rule: str = "target") -> Dict[str, float]:
        """
        根据指定的规则计算新资金的分配份额。
        """
        if not portfolio.assets:
            return {}

        # 规则 1: 比例分配 (Target Rule)
        if rule == "target":
            return {asset.symbol: amount * asset.target_weight for asset in portfolio.assets}

        # 规则 2: 智能分配 (Smart Rule)
        elif rule == "smart":
            total_value = portfolio.get_total_value()
            if total_value == 0:
                return {asset.symbol: amount * asset.target_weight for asset in portfolio.assets}

            drifts = []
            for asset in portfolio.assets:
                current_weight = asset.calculate_current_weight(total_value)
                drift = asset.target_weight - current_weight
                drifts.append({'symbol': asset.symbol, 'drift': drift, 'target_weight': asset.target_weight})

            drifts.sort(key=lambda x: x['drift'], reverse=True)

            allocation = {asset.symbol: 0.0 for asset in portfolio.assets}
            remaining_amount = amount

            for item in drifts:
                if remaining_amount <= 0:
                    break

                target_value_with_new_funds = (total_value + amount) * item['target_weight']
                current_val = next(a.current_value for a in portfolio.assets if a.symbol == item['symbol'])
                needed = target_value_with_new_funds - current_val

                if needed > 0:
                    investment = min(needed, remaining_amount)
                    allocation[item['symbol']] = investment
                    remaining_amount -= investment

            if remaining_amount > 0:
                for asset in portfolio.assets:
                    allocation[asset.symbol] += remaining_amount * asset.target_weight
                remaining_amount = 0

            return allocation

        else:
            raise ValueError(f"未知规则: {rule}")
