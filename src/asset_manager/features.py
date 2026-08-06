from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class MarketFeatures:
    """算法层使用的统一市场特征。"""

    valuation_score: float
    sentiment_score: float
    macro_score: float
    momentum_score: float
    volatility_score: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class MarketFeatureEngine:
    """把 PE/PB/VIX 等原始指标转换为统一特征。"""

    @staticmethod
    def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(value, high))

    @classmethod
    def drawdown_score(cls, drawdown: float) -> float:
        return cls.clamp(max(drawdown, 0.0) / 0.30 * 100)

    @classmethod
    def build(cls, market: str, metrics: Dict[str, float]) -> MarketFeatures:
        if market == "us":
            return cls._build_us(metrics)
        return cls._build_ashare(metrics)

    @classmethod
    def _build_ashare(cls, metrics: Dict[str, float]) -> MarketFeatures:
        valuation = (
            0.35 * (100 - metrics.get("pe_percentile", 50.0))
            + 0.25 * (100 - metrics.get("pb_percentile", 50.0))
            + 0.40 * metrics.get("erp_percentile", 50.0)
        )
        momentum = cls.drawdown_score(metrics.get("drawdown", 0.0))
        return MarketFeatures(
            valuation_score=cls.clamp(valuation),
            sentiment_score=50.0,
            macro_score=50.0,
            momentum_score=momentum,
            volatility_score=50.0,
        )

    @classmethod
    def _build_us(cls, metrics: Dict[str, float]) -> MarketFeatures:
        valuation = (
            0.60 * (100 - metrics.get("forward_pe_percentile", 50.0))
            + 0.40 * (100 - metrics.get("peg_percentile", 50.0))
        )
        sentiment = cls.clamp(metrics.get("vix", 20.0) / 40 * 100)
        macro = cls.clamp(100 - metrics.get("fed_rate_percentile", 50.0))
        momentum = cls.drawdown_score(metrics.get("drawdown", 0.0))
        return MarketFeatures(
            valuation_score=cls.clamp(valuation),
            sentiment_score=sentiment,
            macro_score=macro,
            momentum_score=momentum,
            volatility_score=sentiment,
        )
