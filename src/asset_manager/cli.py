import click

from .config_loader import ConfigLoader
from .engine import DCAEngine, Rebalancer
from .storage import DataManager
from .updater.updater import ConfigUpdater


storage = DataManager()
config_loader = ConfigLoader()


def print_investment(result):
    features = result["features"]
    click.echo(f"\n{result['symbol']}")
    click.echo(f"  建议投入: {result['investment']:.2f}")
    click.echo(f"  定投比例: {result['investment_ratio']:.2%}")
    click.echo(
        "  市场评分: "
        f"{result['market_score']:.2f}"
    )
    click.echo(
        "  市场特征: "
        f"估值={features['valuation_score']:.2f}, "
        f"情绪={round(features['sentiment_score'], 2):.2f}, " # Added rounding to be safe
        f"宏观={features['macro_score']:.2f}, "
        f"趋势={features['momentum_score']:.2f}, "
        f"波动={features['volatility_score']:.2f}"
    )
    click.echo(f"  市场倍率: {result['market_multiplier']:.2f}")
    click.echo(f"  仓位因子: {result['position_factor']:.2f}")
    click.echo(f"  现金安全因子: {result['cash_safety_factor']:.2f}")


@click.group()
def cli():
    """长期 ETF 投资工具。"""


@cli.command()
def status():
    """查看当前持仓与目标仓位。"""
    portfolio = storage.load_portfolio()
    total = portfolio.get_total_value()
    click.echo(f"{'资产':<12} {'当前仓位':>12} {'目标权重':>10} {'当前权重':>10}")
    click.echo("-" * 52)
    for asset in portfolio.assets:
        current_weight = asset.calculate_current_weight(total)
        click.echo(f"{asset.symbol:<12} {asset.current_value:>12.2f} {asset.target_weight:>10.2%} {current_weight:>10.2%}")


@cli.command()
def rebalance():
    """按目标权重计算再平衡金额。"""
    amounts = Rebalancer.calculate_rebalance_amounts(storage.load_portfolio())
    for symbol, amount in amounts.items():
        action = "买入" if amount > 0 else "卖出" if amount < 0 else "无需操作"
        click.echo(f"{symbol}: {action} {abs(amount):.2f}")


@cli.command("sync-config")
@click.option("--structure-only", is_flag=True, help="仅更新资产结构，不抓取市场指标")
def sync_config(structure_only):
    """同步配置：从 weights.json 生成配置并（可选）抓取最新市场指标。"""
    # 1. 生成基础结构
    click.echo("正在从 weights.json 同步资产结构...")
    config = config_loader.generate_from_weights(storage.load_weights())
    config_loader.save(config)
    click.echo(f"基础配置生成成功（包含 {len(config['assets'])} 个资产）。")

    # 2. 如果没有指定 --structure-only，则启动更新器抓取实时指标
    if not structure_only:
        click.echo("正在从互联网抓取最新市场指标...")
        updater = ConfigUpdater(config_loader)
        updater.update_all_assets()
        click.echo("所有可用资产的高度同步完毕。")
    else:
        click.echo("已跳过网络数据更新。")


@cli.command()
@click.option("--total", type=float, required=True, help="假设的投资组合总金额 (当前持仓 + 待投入现金)")
def plan(total: float):
    """规划：输入总金额，查看各资产达到目标权重后的分布情况。"""
    portfolio = storage.load_portfolio()
    click.echo(f"\n基于总额 {total:.2f} 的目标持仓规划：")
    click.echo("-" * 75)
    click.echo(f"{'资产':<12} {'目标权重':>10} {'目标价值':>15} {'当前价值':>15} {'差额/需买入':>15}")
    click.echo("-" * 75)

    category_investments = {}
    total_investment = 0.0

    for asset in portfolio.assets:
        target_value = total * asset.target_weight
        current_weight = asset.current_value / total if total > 0 else 0

        # 考虑份额超过或减少预定份额 5% 才显示调仓金额
        if abs(current_weight - asset.target_weight) > 0.05 * asset.target_weight:
            diff = target_value - asset.current_value
            action = "买入" if diff > 0 else "卖出"
        else:
            diff = 0.0
            action = "无需操作"

        if diff > 0:
            category_investments[asset.category] = category_investments.get(asset.category, 0.0) + diff
            total_investment += diff

        click.echo(
            f"{asset.symbol:<12} {asset.target_weight:>10.2%} {target_value:>15.2f} "
            f"{asset.current_value:>15.2f} {diff:>15.2f} ({action})"
        )
    click.echo("-" * 75)

    click.echo("\n投资统计:")
    click.echo("一级分类投入:")
    for category, amount in category_investments.items():
        click.echo(f"  - {category}: {amount:.2f}")
    click.echo(f"二级资产总投入: {total_investment:.2f}")


@cli.command()
@click.option("--cash", type=float, required=True, help="剩余现金")
@click.option("--months", type=int, required=True, help="剩余建仓月数")
@click.argument("symbols", nargs=-1)
def invest(cash, months, symbols):
    """计算定投金额和每个工具的定投比例。不传 SYMBOL 时计算全部定投资产。"""
    engine = DCAEngine(config_loader)
    portfolio = storage.load_portfolio()
    plan = engine.calculate_plan(portfolio, cash, months)
    items = plan["items"]
    if symbols:
        items = [item for item in items if item["symbol"] in symbols]
    click.echo(f"本期建议总投入: {sum(item['investment'] for item in items):.2f}")
    for result in items:
        print_investment(result)

if __name__ == "__main__":
    cli()
