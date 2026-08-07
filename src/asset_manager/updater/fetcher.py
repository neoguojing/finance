from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
import yfinance as yf
import efinance as ef

session = requests.Session()
session.headers.update(
    {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
)
class BaseFetcher(ABC):
    """数据抓取器基类。"""

    @abstractmethod
    def fetch_metrics(self, symbol: str) -> Dict[str, float]:
        """针对给定资产抓取并返回标准化的市场度量指标字典。"""
        pass


class USFetcher(BaseFetcher):
    """使用 yfinance 抓取美股数据的实现类。"""

    def fetch_metrics(self, symbol: str) -> Dict[str, float]:
        try:
            ticker = yf.Ticker(symbol,session=session)
            info = ticker.info
            return {
                "forward_pe_percentile": info.get("forwardPE", 20.0) / 100,
                "peg_percentile": info.get("pegRatio", 1.5) / 100,
                "vix": 20.0,
                "fed_rate_percentile": 50.0,
                "drawdown": 0.0,
            }
        except Exception as e:
            print(f"Error fetching US data for {symbol}: {e}")
            return {}


class ASHareFetcher(BaseFetcher):
    """使用 efinance 抓取 A 股数据的实现类。"""

    def fetch_metrics(self, symbol: str) -> Dict[str, float]:
        try:
            df = ef.stock.get_quote_history(symbol)
            if df is None or df.empty:
                return {}
            return {
                "pe_percentile": 5_0.0,
                "pb_percentile": 50.0,
                "erp_percentile": 50.0,
                "drawdown": 0.0,
            }
        except Exception as e:
            print(f"Error fetching A-share data for {symbol}: {e}")
            return {}
