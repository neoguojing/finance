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
    """把 PE/PB/VIX 等原始指标转换为统一特征。

    该引擎的核心逻辑是将不同维度的市场指标（如市盈率分位数、VIX 指数等）
    通过加权平均和归一化处理，映射到一个 [0, 100] 的统一分值区间内。
    """

    @staticmethod
    def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        """将数值限制在 [low, high] 范围内。"""
        return max(low, min(value, high))

    @classmethod
    def drawdown_score(cls, drawdown: float) -> float:
        """
        计算回撤得分（Momentum Score 的组成部分）。

        公式: score = (max(drawdown, 0) / 0.30) * 100
        逻辑:
            - 将回撤程度相对于 30% 的基准进行线性缩放。
            - 如果回撤达到 30%，得分为 100。
            - 该得分越高，代表市场处于极端负面状态（回撤严重），
              通常用于衡量趋势的衰减或动能的丧失。
        """
        return cls.clamp(max(drawdown, 0.0) / 0.30 * 100)

    @classmethod
    def build(cls, market: str, metrics: Dict[str, float]) -> MarketFeatures:
        """根据市场类型构建特征集。"""
        if market == "us":
            return cls._build_us(metrics)
        return cls._build_ashare(metrics)

    @classmethod
    def _build_ashare(cls, metrics: Dict[str, float]) -> MarketFeatures:
        """
        计算 A 股市场的特征得分。

        1. Valuation (估值):
           Score = 0.35 * (100 - PE_percentile) + 0.25 * (100 - PB_percentile) + 0.40 * ERP_percentile
           - 使用百分位数的反向值，使得低 PE/PB 分位数（即估值便宜）对应高分。
           - ERP (Equity Risk Premium) 越高，代表风险补偿越大，得分越高。
        2. Momentum (动量): 基于回撤程度计算。
        3. 其他维度目前作为基准值 (50.0) 处理。
        """
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
        """
        计算美股市场的特征得分。

        1. Valuation (估值):
           Score = 0.60 * (100 - Forward_PE_percentile) + 0.40 * (100 - PEG_percentile)
           - 侧重于前向市盈率和 PEG 指标的低分位数（即廉价程度）。
        2. Sentiment (情绪):
           Score = (VIX / 40) * 100
           - 基于 VIX 指数。注意：此处高分代表 VIX 高，即市场恐惧情绪高。
        3. Macro (宏观):
           Score = 100 - Fed_Rate_percentile
           - 美联储利率分位数越高（加息周期），得分越低。
        4. Momentum (动量): 基于回撤程度计算。
        5. Volatility (波动率): 直接映射自 Sentiment 分数（VIX）。
        """
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
