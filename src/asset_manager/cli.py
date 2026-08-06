import click

from .config_loader import ConfigLoader
from .engine import DCAEngine, Rebalancer
from .storage import DataManager

storage = DataManager()
config_loader = ConfigLoader()


def print_investment(result):
    features = result["features"]
    click.echo(f"\n{result['symbol']}")
    click.echo(f"  建议投入: {result['investment']:.2f}")
    click.echo(f"  定投比例: {result['investment_ratio']:.2%}")
    click.echo(f"  市场评分: {result['market_score']:.2f}")
    click.echo(
        "  市场特征: "
        f"估值={features['valuation_score']:.2f}, "
        f"情绪={features['sentiment_score']:.2f}, "
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


@cli.command("generate-config")
def generate_config():
    """根据 weights.json 生成或刷新可定投工具配置。"""
    config = config_loader.generate_from_weights(storage.load_weights())
    config_loader.save(config)
    click.echo(f"已生成 {len(config['assets'])} 个定投工具配置。")


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
