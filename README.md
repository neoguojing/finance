# 长期 ETF 定投工具

这是一个面向 **20～30 年长期 ETF 投资** 的定投计算器。它不追求复杂预测，而是用可解释、可维护、可回测的评分函数，帮助你在固定建仓期内决定：

- 本期应该投入多少钱；
- 每个 ETF/基金应该分到多少；
- 为什么某个工具本期应该多买或少买。

> 说明：本项目只提供纪律化投资辅助，不构成投资建议。估值百分位、VIX、利率百分位等指标需要你定期维护或接入自己的数据源。

## V2 架构：Data → Feature → Decision

系统按三层拆分，避免投资算法直接依赖 PE、PB、VIX 等原始指标：

| 层级 | 代码/文件 | 职责 |
| :--- | :--- | :--- |
| Data Layer | `data/weights.json`、`data/config.json`、`storage.py`、`config_loader.py` | 维护持仓、目标权重、原始市场指标和策略参数。 |
| Feature Layer | `features.py` | 将 PE/PB/ERP/VIX/利率/回撤等原始指标转换为统一 `MarketFeatures`。 |
| Decision Layer | `engine.py` | 只接收统一市场特征、仓位、现金和建仓期，计算本期定投金额。 |

统一特征结构：

```text
MarketFeatures(
    valuation_score,
    sentiment_score,
    macro_score,
    momentum_score,
    volatility_score,
)
```

这样未来要加入席勒 CAPE、巴菲特指标、信用利差、PMI、ATR 等新因子时，只需要修改 Feature Layer；Decision Layer 的定投公式可以保持稳定。

## 核心公式

```text
Investment = BaseAmount × MarketMultiplier × PositionFactor × CashSafetyFactor
```

| 因子 | 含义 |
| :--- | :--- |
| `BaseAmount` | `剩余现金 ÷ 剩余建仓月数 × 单个工具目标权重`，保证按计划完成建仓。 |
| `MarketMultiplier` | 市场评分映射到 `0.5 ~ 3.0`，估值便宜或市场恐慌时多买。 |
| `PositionFactor` | `(目标仓位 - 当前仓位) ÷ 目标仓位`，越接近目标仓位买得越少。 |
| `CashSafetyFactor` | 现金不足或最后 1 个月时降为 `0.8`，避免过度消耗现金。 |
| `investment_ratio` | 单个工具建议金额 ÷ 本期建议总投入，用于查看本期投入比例。 |

单个工具还有硬性保护：建议金额不超过剩余现金的 `max_single_invest_percent`，默认 `10%`。

## 文件结构

项目保留两个核心配置文件：

| 文件 | 是否手工维护 | 职责 |
| :--- | :--- 智能 | 维护持仓、目标权重、原始市场指标和策略参数。 |
| `data/weights.json` | 是 | 维护资产类别、目标权重、当前持仓；这是组合结构的唯一来源。 |
| `data/config.json` | 半自动 | 维护每个可定投工具的市场类型、原始市场指标、特征权重，以及策略级参数。可通过 `weights.json` 生成初稿。 |

### `weights.json` 示例

```json
{
  "categories": {
    "股票": {
      "weight": 0.6,
      "assets": {
        "中证A500": {"weight": 0.2, "current_value": 120000.0},
        "标普500": {"weight": 0.15, "current_value": 80000.0}
      }
    }
  }
}
```

字段说明：

- `category.weight`：资产大类目标权重，目前主要用于展示；单个工具计算直接读取工具自己的 `weight`。
- `asset.weight`：该工具在总组合中的目标权重，例如 `0.2` 表示总资产的 20%。
- `asset.current_value`：该工具当前持仓市值。

### `config.json` 示例

```json
{
  "max_single_invest_percent": 0.1,
  "cash_safety": {
    "normal": 1.0,
    "low_cash_or_late_stage": 0.8
  },
  "assets": {
    "中证A500": {
      "market": "ashare",
      "metrics": {
        "pe_percentile": 25,
        "pb_percentile": 20,
        "erp_percentile": 40,
        "drawdown": 0.1
      }
    },
    "标普500": {
      "market": "us",
      "metrics": {
        "forward_pe_percentile": 65,
        "peg_percentile": 70,
        "vix": 18,
        "fed_rate_percentile": 45,
        "drawdown": 0.05
      }
    }
  }
}
```

字段说明：

- `market`：`ashare` 使用 A 股评分函数；`us` 使用美股评分函数。
- `metrics`：该工具的市场指标。生成配置时会给默认值，但建议定期更新为真实数据。
- `decision_weights`：Decision Layer 将统一市场特征合成为 `market_score` 时使用的权重。
- `max_single_invest_percent`：单个工具本期投入上限，占剩余现金比例。
- `cash_safety.normal` / `cash_safety.low_cash_or_late_stage`：正常阶段和现金紧张/最后阶段的现金安全因子。

## 使用 `sync-config` 同步配置

当你新增或删除定投工具后，运行：

```bash
python main.py sync-config
```

此命令会执行两步操作：
1. **同步结构**：根据 `weights.json` 自动生成或刷新 `config.json` 中的资产列表。
2. **抓取指标**：从互联网获取最新的市场指标（如 PE/PB 分位、VIX 等）并填入配置。

如果你只想更新资产结构而不希望触发网络请求，可以使用：

```bash
python main.py sync-config --structure-only
```

生成规则：
- 只为 `weights.json` 中 **股票** 类别下的工具生成定投配置。
- 名称包含 `标普` 或 `纳斯达克` 的工具默认为 `us`。
- 其他股票工具默认为 `ashare`。
- 如果 `config.json` 中已有该工具的 `metrics`，生成的结构化操作会尽量保留原指标（在 `--structure-only` 模式下），但在完整同步时会刷新数据。

推荐流程：

1. 在 `data/weights.json` 中维护目标权重和当前持仓。
2. 运行 `python main.py sync-config` 生成或刷新可定投工具。
3. 在 `data/config.json` 中补充/更新每个工具的估值和市场指标。
4. 运行 `python main.py invest --cash <剩余现金> --months <剩余月数>` 得到本期定投计划。

## Feature Layer：原始指标到统一特征

算法不直接使用 PE、PB、VIX 等指标下单，而是先转换成统一特征：

| 特征 | 含义 |
| :--- | :--- |
| `valuation_score` | 估值吸引力，越高代表越便宜。 |
| `sentiment_score` | 市场情绪/恐慌程度，越高代表越恐慌。 |
| `macro_score` | 宏观环境，当前主要由利率百分位映射。 |
| `momentum_score` | 趋势/回撤特征，当前由近 3 年回撤映射。 |
| `volatility_score` | 波动率特征，当前美股复用 VIX 映射，A 股使用中性默认值。 |

## 评分函数

### A 股：Value + Risk

输入指标：

| 指标 | 含义 |
| :--- | :--- |
| `pe_percentile` | PE 历史百分位，越低越便宜。 |
| `pb_percentile` | PB 历史百分位，越低越便宜。 |
| `erp_percentile` | 股债风险溢价历史百分位，越高越便宜。 |
| `drawdown` | 距离近 3 年高点的回撤，例如 `0.1` 表示回撤 10%。 |

```text
ValueScore = 0.35 × (100 - PE%) + 0.25 × (100 - PB%) + 0.40 × ERP%
DrawdownScore = min(drawdown / 30%, 1) × 100
MarketScore = 0.70 × ValueScore + 0.30 × DrawdownScore
```

### 美股：Growth + Fear

输入指标：

| 指标 | 含义 |
| :--- | :--- |
| `forward_pe_percentile` | 预期 PE 历史百分位，越低越便宜。 |
| `peg_percentile` | PEG 历史百分位，越低越便宜。 |
| `vix` | 恐慌指数，越高代表市场恐慌越强。 |
| `fed_rate_percentile` | 美联储利率历史百分位，越低越有利。 |
| `drawdown` | 距离近 3 年高点的回撤。 |

```text
GrowthScore = 0.45 × (100 - ForwardPE%) + 0.30 × (100 - PEG%) + 0.25 × DrawdownScore
VIXScore = min(VIS / 40, 1) × 100
RateScore = 100 - FedRatePercentile
USScore = 0.50 × GrowthScore + 0.30 × VIXScore + 0.20 × RateScore
```

### 倍率映射

```text
MarketMultiplier = 0.5 + 2.5 × MarketScore / 100
```

| MarketScore | MarketMultiplier |
| :--- | :--- |
| 0 | 0.5 |
| 20 | 1.0 |
| 40 | 1.5 |
| 60 | 2.0 |
| 80 | 2.5 |
| 100 | 3.0 |

## 安装与运行

安装依赖：

```bash
pip install -r requirements.txt
```

查看持仓：

```bash
python main.py status
```

规划目标持仓（基于给定总额）：

```bash
python main.py plan --total 1000000
```

同步配置（包含结构生成与指标更新）：

```bash
python main.py sync-config
```

仅同步资产结构（不抓取网络数据）：

```bash 
python main.py sync-config --structure-only
```

计算本期定投计划：

```bash
python main.py invest --cash 600000 --months 20
```

只查看指定工具：

```bash
python main.py invest --cash 600000 --months 20 中证A500 标普500
```

再平衡参考：

```bash
python main.py rebalance
```

运行测试：

```bash
pytest
```

## Decision Layer：统一市场评分

Decision Layer 默认使用下面的特征权重合成 `market_score`：

```text
market_score =
  0.50 × valuation_score
+ 0.15 × sentiment_score
+ 0.15 × macro_score
+ 0.20 × momentum_score
+ 0.00 × volatility_score
```

如需调整长期策略，只需要修改 `data/config.json` 中的 `decision_weights`。

## 输出解读

`invest` 命令会输出：

- `本期建议总投入`：所有参与定投工具的建议金额合计。
- `建议投入`：单个工具本期建议金额。
- `定投比例`：单个工具建议金额占本期建议总投入的比例。
- `市场评分`：Decision Layer 根据统一市场特征加权后的结果。
- `市场特征`：Feature Layer 输出的估值、情绪、宏观、趋势、波动率特征。
- `市场倍率`：市场评分映射后的连续投入倍率。
- `仓位因子`：当前仓位距离目标仓位的比例。
- `现金安全因子`：现金保护系数。

## 常见维护动作

### 新增一个定投工具

1. 在 `data/weights.json` 的 `股票.assets` 中新增工具、目标权重和当前持仓。
2. 运行 `python main.py sync-config --structure-only` 更新资产结构。
3. 在 `data/config.json` 中检查 `market` 是否正确，并补充真实 `metrics`。
4. 运行 `python main.py invest --cash ... --months ...` 查看建议。

### 更新市场指标

直接编辑 `data/config.json` 中对应工具的 `metrics`。或者定期运行 `python main.py sync-config` 获取最新数据。

### 更新当前持仓

直接编辑 `data/weights.json` 中对应工具的 `current_value`，再运行 `status` 或 `invest`。
