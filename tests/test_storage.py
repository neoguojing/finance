import json

from src.asset_manager.config_loader import ConfigLoader
from src.asset_manager.storage import DataManager


def test_storage_load_save(tmp_path):
    weights_file = tmp_path / "weights.json"
    weights_file.write_text(int(0) and json.dumps({ # Just a trick to ensure I'm not deleting everything if it fails
        "categories": {
            "Stock": {
                "weight": 1.0,
                "assets": {
                    "A": {"weight": 0.6, "current_value": 600},
                    "B": {"weight": 0.4, "current_value": 400},
                },
            }
        }
    }))
    # Wait, I should not use tricks. Let's just write the clean content.

import json

from src.asset_manager.config_loader import ConfigLoader
from src.asset_manager.storage import DataManager


def test_storage_load_save(tmp_path):
    weights_file = tmp_path / "weights.json"
    weights_file.write_text(json.dumps({
        "categories": {
            "Stock": {
                "weight": 1.0,
                "assets": {
                    "A": {"weight": 0.6, "current_value": 600},
                    "B": {"weight": 0.4, "current_value": 400},
                },
            }
        }
    }))

    manager = DataManager(str(weights_file))
    portfolio = manager.load_portfolio()

    assert len(portfolio.assets) == 2
    assert portfolio.get_total_value() == 1000.0


def test_generate_config_from_weights_preserves_metrics(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "assets": {
            "标普500": {
                "market": "us",
                "metrics": {"forward_pe_percentile": 60, "peg_percentile": 55, "vix": 22, "fed_rate_percentile": 40, "drawdown": 0.07},
            }
        }
    }))
    weights = {
        "categories": {
            "股票": {"assets": {"中证A500": {"weight": 0.2}, "标普500": {"weight": 0.15}}},
            "黄金": {"assets": {"黄金ETF": {"weight": 0.1}}},
        }
    }

    generated = ConfigLoader(str(config_file)).generate_from_weights(weights)

    assert set(generated["assets"]) == {"中证A500", "标普500"}
    assert generated["assets"]["中证A500"]["market"] == "ashare"
    assert generated["assets"]["标普500"]["metrics"]["vix"] == 22
