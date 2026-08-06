# 家庭资产配置管理工具 (Family Asset Allocation Manager)

这是一个基于 Python 的家庭资产配置管理工具，旨在帮助用户通过量化的方式管理资产组合，实现资产的科学配置与定期再平衡。

## 🚀 核心特性

### 1. 资产份额自动计算
- **目标权重管理**：用户可定义各资产类别的目标占比（如：股票 60%, 债券 30%, 现金 10%）。
- **实时偏差分析**：自动计算当前资产价值与目标权重的偏差（Drift），清晰展示哪些资产过重或不足。

### 2. 资产自动再平衡 (Rebalancing)
- **目标价值法**：基于当前总资产，计算每个资产应有的目标价值。
- **交易建议**：自动计算需要“买入”或“卖出”的具体金额，以使组合重新回到目标配置。

---

## 🛠️ 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置数据
程序将所有配置和持仓数据统一存储在 `data/weights.json` 中。

**示例 `weights.json`**:
```json
{
    "categories": {
        "Stock": {
            "weight": 0.6,
            "assets": {
                "US_Stock": { "weight": 0.5, "current_value": 3000.0 },
                "CN_Stock": { "weight": 0.5, "current_value": 2000.0 }
            }
        },
        "Bond": {
            "weight": 0.4,
            "assets": {
                "US_Bond": { "weight": 1.0, "current_value": 4000.0 }
            }
        }
    }
}
```

### 运行命令
由于项目结构原因，运行命令时建议将当前目录添加到 `PYTHONPATH`。

#### 1. 查看当前资产状态
```bash
export PYTHONPATH=$PYTHONPATH:. && python main.py status
```

#### 2. 规划资产份额
```bash
# 如果你想将总资产规划为 10000 元，查看各资产应有的份额及调整建议
export PYTHONPATH=$PYTHONPATH:. && python main.py plan --total 10000
```

#### 3. 计算再平衡建议
```bash
export PYTHONPATH=$PYTHONPATH:. && python main.py rebalance
```

#### 4. A股智能定投规划 (新)
```bash
# 示例：PE=20, PB=30, ERP=70, 跌幅=15%(0.15), 现金=600000, 剩余20个月
export PYTHONPATH=$PYTHONPATH:. && python main.py ashare-invest --pe 20 --pb 30 --erp 70 --dd 0.15 --cash 600000 --months 20
```

#### 5. 美股智能定投规划 (新)
```bash
# 示例：FPE=30, PEG=40, VIX=25, 利率百分位=50, 跌幅=10%(0.1), 现金=600000, 剩余20个月
export PYTHONPATH=$PYTHONPATH:. && python main.py us-invest --fpe 30 --peg 40 --vix 25 --fed 50 --dd 0.1 --cash 600000 --months 20
```

---

## 📖 命令行详解

| 命令 | 参数 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `status` | 无 | 显示总价值、各资产实际权重及偏差 | `python main.py status` |
| `plan` | `--total` (必填) | 根据目标总额规划各资产份额 | `python main.py plan --total 10000` |
| `rebalance` | 无 | 计算使组合回到目标配置的买卖金额 | `python main.py rebalance` |

---

## 📂 模块说明

- `src/asset_manager/models.py`: 定义核心数据结构（资产 `Asset` 和 投资组合 `Portfolio`）。
- `src/asset_manager/engine.py`: 实现再平衡算法和定投分配逻辑。
- `src/asset_manager/storage.py`: 处理数据的持久化，管理 JSON 文件读写。
- `src/asset_manager/cli.py`: 基于 `click` 提供的命令行交互界面。
- `main.py`: 程序入口点。

## 🧪 测试
可以使用 `pytest` 运行现有测试：
```bash
pytest tests/
```
