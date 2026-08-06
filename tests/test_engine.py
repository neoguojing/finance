import pytest
from src.asset_manager.models import Asset, Portfolio
from src.asset_manager.engine import Rebalancer, DCAEngine

def test_rebalancer():
    assets = [
        Asset("Stock", 7000.0, 0.60, "Equity"),
        Asset("Bond", 2000.0, 0.30, "Fixed Income"),
        Asset("Cash", 1000.0, 0.10, "Cash"),
    ]
    portfolio = Portfolio(assets)
    amounts = Rebalancer.calculate_rebalance_amounts(portfolio)

    # Total = 10000.
    # Stock Target = 6000, Current = 7000 => -1000
    # Bond Target = 3000, Current = 2000 => +1000
    # Cash Target = 1000, Current = 1000 => 0
    assert amounts["Stock"] == -1000.0
    assert amounts["Bond"] == 1000.0
    assert amounts["Cash"] == 0.0

def test_dca_target():
    assets = [
        Asset("Stock", 1000.0, 0.60, "Equity"),
        Asset("Bond", 1000.0, 0.30, "Fixed Income"),
        Asset("Cash", 1000.0, 0.10, "Cash"),
    ]
    portfolio = Portfolio(assets)
    allocation = DCAEngine.calculate_contribution_split(portfolio, 1000.0, rule="target")

    assert allocation["Stock"] == 600.0
    assert allocation["Bond"] == 300.0
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
    allocation = DCAEngine.calculate_contribution_split(portfolio, 1000.0, rule="smart")

    assert allocation["Stock"] == 1000.0
    assert allocation["Bond"] == 0.0
    assert allocation["Cash"] == 0.0
