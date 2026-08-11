from typing import Any, Dict, List
from .config_loader import ConfigLoader
from .features import MarketFeatureEngine
from .models import Portfolio

class DCAEngine:
    """长期 ETF 定投评分引擎 (配置驱动版)。"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def calculate_plan(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        计算整个投资组合在当前阶段的定投执行计划。
        算法逻辑: 建议投入 = ((总投入 - 初始投入) / 总月数) * 市场倍率
        """
        dca_symbols = set(self.config_loader.get_assets())
        results = []
        for asset in portfolio.assets:
            if asset.symbol not in dca_symbols:
                continue

            # 1. 获取配置
            asset_config = self.config_loader.get_asset_config(asset.symbol)
            if not asset_config or "investment_config" not in asset_config:
                continue

            cfg = asset_config["investment_config"]

            # 2. 计算基础月度额度
            base = (cfg.get("total_investment", 0.0) - cfg.get("initial_investment", 0.0)) / cfg.get("total_months", 1)

            # 3. 确定倍率和理由
            indicator = cfg.get("indicator", "00")
            if indicator == "00":
                multiplier, reason = 1.0, "指标为 '00'，采用固定投入倍率 1.0"
            else:
                val = MarketFeatureEngine.get_indicator_value(self.config_loader, asset.symbol, indicator)
                rule = next((r for r in cfg.get("rules", []) if r["min"] <= val < r["max"]), None)
                multiplier = rule["multiplier"] if rule else 1.0
                reason = f"指标 {indicator} 当前值为 {val:.2f}"
                reason += f"，落在区间 [{rule['min']}, {rule['max']})，适用倍率 {multiplier:.2f}" if rule else "，未落在任何配置区间内，采用默认倍率 1.0"

            results.append({
                "symbol": asset.symbol,
                "investment": base * multiplier,
                "investment_ratio": 0.0,
                "base_amount": base,
                "multiplier": multiplier,
                "reason": reason,
            })

        total_investment = sum(item["investment"] for item in results)
        for item in results:
            item["investment_ratio"] = item["investment"] / total_investment if total_investment > 0 else 0.0

        return {"total_investment": total_investment, "items": results}
