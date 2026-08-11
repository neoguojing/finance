from typing import Any, Dict, List
from .config_loader import ConfigLoader
from .features import MarketFeatureEngine
from .models import Portfolio

class DCAEngine:
    """长期 ETF 定投评分引擎 (配置驱动版)。"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def calculate_investment(
        self,
        symbol: str,
        current_position: float,
    ) -> Dict[str, Any]:
        """
        计算特定资产在本期的建议定投金额。

        算法逻辑:
            1. 从 config.json 中读取 investment_config (总投入, 总月数, 指标, 规则)。
            2. 基础月度额度 (Base) = 总投入 / 总月数。
            3. 根据当前指标值在 rules 中匹配倍率 (Multiplier)。
            4. 建议投入 = Base * Multiplier。

        Args:
            symbol (str): 资产代码。
            current_position (float): 该资产当前的持仓市值。

        Returns:
            Dict[str, Any]: 包含本次定投建议金额和计算理由的字典。
        """
        asset_config = self.config_loader.get_asset_config(symbol)
        if not asset_config:
            return {"error": f"未找到定投资产配置: {symbol}"}

        invest_cfg = asset_config.get("investment_config")
        if not invest_cfg:
            return {"error": f"资产 {symbol} 缺少 investment_config 配置"}

        total_invest = invest_cfg.get("total_investment", 0.0)
        total_months = invest_cfg.get("total_months", 1)
        indicator_name = invest_cfg.get("indicator", "00")
        rules = invest_cfg.get("rules", [])

        # 1. 计算基础月度额度
        base = total_invest / total_months if total_months > 0 else 0.0

        # 2. 确定倍率和理由
        if indicator_name == "00":
            multiplier = 1.0
            reason = "指标为 '00'，采用固定投入倍率 1.0"
        else:
            val = MarketFeatureEngine.get_indicator_value(self.config_loader, symbol, indicator_name)
            multiplier = 1.0  # 默认倍率
            reason = f"指标 {indicator_name} 当前值为 {val:.2f}"

            # 匹配区间
            matched = False
            for rule in rules:
                if rule["min"] <= val < rule["max"]:
                    multiplier = rule["multiplier"]
                    reason += f"，落在区间 [{rule['min']}, {rule['max']})，适用倍率 {multiplier:.2f}"
                    matched = True
                    break

            if not matched:
                reason += "，未落在任何配置区间内，采用默认倍率 1.0"

        # 3. 计算最终金额
        final = base * multiplier

        return {
            "symbol": symbol,
            "investment": final,
            "investment_ratio": 0.0, # 在 calculate_plan 中填充
            "base_amount": base,
            "multiplier": multiplier,
            "reason": reason,
            "indicator_value": val if indicator_name != "00" else None
        }

    def calculate_plan(self, portfolio: Portfolio, cash_remaining: float = None, months_left: int = None) -> Dict[str, Any]:
        """
        计算整个投资组合在当前阶段的定投执行计划。

        注意: cash_remaining 和 months_left 现在仅作为兼容性参数，
        实际计算依据每个资产在 config.json 中的 investment_config。
        """
        dca_symbols = set(self.config_loader.get_assets())
        results = []
        for asset in portfolio.assets:
            if asset.symbol not in dca_symbols:
                continue
            result = self.calculate_investment(
                symbol=asset.symbol,
                current_position=asset.current_value,
            )
            if "error" not in result:
                results.append(result)

        total_investment = sum(item["investment"] for item in results)
        for item in results:
            item["investment_ratio"] = item["investment"] / total_investment if total_investment > 0 else 0.0

        return {"total_investment": total_investment, "items": results}
