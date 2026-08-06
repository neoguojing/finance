import os
import json
import pytest
from src.asset_manager.storage import DataManager
from src.asset_manager.models import Portfolio

def test_storage_load_save(tmp_path):
    weights_file = tmp_path / "weights.json"
    holdings_file = tmp_path / "holdings.json"

    weights = {"Stock": 0.6, "Bond": 0.4}
    holdings = {"Stock": 600, "Bond": 400}

    weights_file.write_text(json.dumps(weights))
    holdings_file.write_text(json.dumps(holdings))

    manager = DataManager(str(weights_file), str(holdings_file))
    portfolio = manager.load_portfolio()

    assert len(portfolio.assets) == 2
    assert portfolio.get_total_value() == 1000.0

    # Update value
    manager.update_asset_value("Stock", 700)
    new_portfolio = manager.load_portfolio()
    assert new_portfolio.get_total_value() == 1100.0
