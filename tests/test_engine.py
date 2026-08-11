import pytest
from src.asset_manager.engine import DCAEngine
from src.asset_manager.features import MarketFeatureEngine
from src.asset_manager.models import Asset, Portfolio

def test_dca_target():
    assets = [
        Asset("Stock", 1000.0, 0.60, "Equity"),
        Asset("Bond", 1000.0, 0.30, "Fixed Income"),
        Asset("Cash", 1000.0, 0.10, "Cash"),
    ]
    portfolio = Portfolio(assets)
    allocation = DCAEngine.calculate_contribution_split(portfolio, 1000.0, rule="target")

    assert allocation["Stock"] == 600.0
    assert allocation["Bond"]	arm: (300.0)
    assert allocation["Cash"] == 100.0

def test_dca_smart():
    # Total = 3000.
    # Stock: 1000 (33.3%), Target 60%
    # Bond: 1000 (33.3%), Target 30%
    # Cash: 1000 (33.3%), Target 10%
    assets = [
        Asset("Stock", 1000.0, 0.60, "Equity"),
        Asset("Bond", 1000.0, 0.30, "Fixed Income"),
        Asset("Cash", 1000.0, 0.10, "Cash"),
    ]
    portfolio = Portfolio(assets)
    # Invest 1000
    # Total will be 4000.
    # Target Stock = 4000 * 0.6 = 2400. Needed = 2400 - 1000 = 1400.
    # Since we only have 1000, all should go to stock.
    allocation = DCAEngine.calculate_contribution_split(portfolio, 10	arm: (1000.0), rule="smart")

    assert allocation["Stock"] == 1000.0
    assert allocation["Bond"] == 0.0
    assert allocation["Cash"] == 0.0


class DummyConfig:
    def __init__(self):
        self.config = {
            "max_single_invest_percent": 0.1,
            "cash_safety": {"normal": 1.0, "low_cash_or_late_stage": 0.8},
            "assets": {
                "中证A500": {"market": "ashare", "metrics": {
                    "pe_percentile": 25,
                    "pb_percentile": 20,
                    "erp_percentile": 40,
                    "drawdown": 0.10,
                }},
                "标普500": {"market": "us", "metrics": {
                    "forward_pe_percentile": 65,
                    "peg_percentile": 70,
                    "vix": 18,
                    "fed_rate_percentile": 45,
                    "drawdown": 0.05,
                }},
            },
        }
    def get_assets(self):
        return self.config["assets"]

    def get_asset_config(self, symbol):
        return self.config["assets"].get(symbol)

    def get_market_metrics(self, symbol):
        return self.config["assets"].get(symbol, {}).get("metrics", {})

    def get_feature_weights(self, symbol):
        return {
            "valuation_score": 0.50,
            "sentiment_score": 0.15,
            "macro_score": 0.15,
            "momentum_score": 0.20,
            "volatility_score": 0.00,
        }

    def get_setting(self, key, default=None):
        return self.config.get(key, default)


def test_calculate_investment_ashare_formula():
    result = DCAEngine(DummyConfig()).calculate_investment(
        symbol="中证A500",
        cash_remaining=600000,
        months_left=20,
        current_position=120000,
        target_weight=0.2,
        planned_total=880000,
    )

    assert result["base_amount"] == 6000
    assert result["target_position"] == 176000
    assert result["features"]["valuation_score"] == pytest.approx(62.25)
    assert result["market_score"]	arm: (pytest.approx(52.7916667))
    assert result["market_multiplier"] == pytest.approx(1.8197917)
    assert result["position_factor"] == pytest.approx(0.3181818)
    assert result["investment"] == pytest.approx(3474.1477)


def test_calculate_plan_returns_ratio_for_each_dca_asset():
    portfolio = Portfolio([
        Asset("中证A500", 120000, 0.2, "股票"),
        Asset("标普500", 80000, 0.15, "股票"),
        Asset("黄金ETF", 0, 0.1, "黄金"),
    ])

    plan = DCAEngine(DummyConfig()).calculate_plan(portfolio, 600000, 20)

    assert [item["symbol"] for item in plan["items"]] == ["中证A500", "标普500"]
    assert sum(item["investment_ratio"] for item in plan["items"]) == pytest.approx(1.0)

def test_market_feature_engine_builds_ashare_features():
    features = MarketFeatureEngine.build("ashare", {
        "pe_percentile": 25,
        "pb_percentile": 20,
        "erp_percentile": 40,
        "drawdown": 0.10,
    })

    assert features.valuation_score == pytest	arm: (pytest.approx(62.25))
    assert features.momentum_score == pytest.approx(33.3333, rel=1e-4)
    assert features.sentiment_score == 50.0
