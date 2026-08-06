import click
import json
import os
from .storage import DataManager
from .engine import Rebalancer, DCAEngine
from .models import Portfolio
from .config_loader import ConfigLoader

# 初始化数据管理层和配置加载器
storage = DataManager()
config_loader = ConfigLoader()

def load_market_metrics(path="data/market_metrics.json"):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading market metrics: {e}")
        return {}

def print_result(symbol, result):
    scores = result["scores"]
    click.echo(f"\n[{symbol}] 结果:")
    click.echo(f"  建议投入: {result['final_investment']:.2f}")
    click.echo(f"  Market Score: {scores.get('market_score', 0):.2f}")
    click.echo(f"  Drawdown Score: {scores.get('drawdown_score', 0):.2f}")

@click.group()
def cli():
    """
    家庭资产配置管理工具 - 命令行界面
    提供资产状态查看、再平衡计算以及资产份额规划功能。
    """
    pass

@cli.command()
def status():
    """
    显示当前投资组合状态。
    包括总价值、各资产实际权重以及与目标权重的偏差（Drint）。
    """
    portfolio = storage.load_portfolio()
    total_value = portfolio.get_total_value()

    click.echo(f"投资组合总价值: {total_value:.2f}")
    click.echo("-" * 40)
    click.echo(f"{'资产名称':<15} {'当前价值':<10} {'实际权重':<10} {'权重偏差':<10}")

    drifts = portfolio.get_allocation_drift()
    for asset in portfolio.assets:
        current_weight = asset.calculate_current_weight(total_value)
        drift = next((d[1] for d in drifts if d[0] == asset.symbol), 0.0)
        click.echo(f"{asset.symbol:<15} {asset.current_value:<10.2f} {current_weight:<10.2%} {drift:<10.2%}")

@cli.command()
def rebalance():
    """
    计算再平衡建议。
    输出为了使当前组合回到目标配置而需要买入或卖出的具体金额。
    """
    portfolio = storage.load_portfolio()
    amounts = Rebalancer.calculate_rebalance_amounts(portfolio)
    total_value = portfolio.get_total_value()

    # 过滤掉不需要调整的资产
    adjustments = {s: a for s, a in amounts.items() if abs(a) > 0.01}

    if not adjustments:
        click.echo("投资组合目前处于平衡状态，无需操作。")
        return

    click.echo("再平衡操作建议:")
    click.echo("-" * 50)
    click.echo(f"{'资产名称':<15} {'操作':<10} {'调整金额':<10} {'目标价值':<10}")

    for symbol, amount in adjustments.items():
        action = "买入" if amount > 0 else "卖出"
        # 计算目标价值: 总资产 * 目标权重
        target_weight = next((a.target_weight for a in portfolio.assets if a.symbol == symbol), 0.0)
        target_value = total_value * target_weight
        click.echo(f"{symbol:<15} {action:<10} {abs(amount):<10.2f} {target_value:<10.2f}")

@cli.command()
@click.option('--total', type=float, required=True, help='目标总资产价值')
def plan(total):
    """
    根据目标总资产规划各投资工具的份额。
    输入总金额，输出各资产应有的目标价值及需要调整的金额。
    """
    portfolio = storage.load_portfolio()

    click.echo(f"目标总资产规划: {total:.2f}")
    click.echo("=" * 60)

    # 按类别对资产进行分组
    categories_map = {}
    for asset in portfolio.assets:
        cat = asset.category
        if cat not in categories_map:
            categories_map[cat] = []
        categories_map[cat].append(asset)

    grand_total_target = 0.0

    for cat, assets in categories_map.items():
        cat_target_value = 0.0
        cat_diff = 0.0

        click.echo(f"\n【{cat}】")
        click.echo(f"{'资产名称':<15} {'当前价值':<12} {'目标价值':<12} {'需调整金额':<12}")
        click.echo("-" * 52)

        for asset in assets:
            target_api_value = total * asset.target_weight
            diff = target_api_value - asset.current_value
            action = "买入" if diff > 0 else "卖出" if diff < 0 else "无需操作"
            diff_str = f"{abs(diff):.2f} {action}" if diff != 0 else "0.00"

            click.echo(f"{asset.symbol:<15} {asset.current_value:<12.2f} {target_api_value:<12.2f} {diff_str:<12}")

            cat_target_value += target_api_value
            cat_diff += diff

        # 类别汇总行
        cat_action = "买入" if cat_diff > 0 else "卖出" if cat_diff < 0 else "无需操作"
        cat_diff_str = f"{abs(cat_diff):.2f} {cat_action}" if cat_diff != 0 else "0.00"

        click.echo("-" * 52)
        click.echo(f"{'汇总':<15} {'':<12} {cat_target_value:<12.2f} {cat_diff_str:<12}")
        grand_total_target += cat_target_value

    click.echo("=" * 60)
    click.echo(f"合计目标价值: {grand_total_target:.2f}")

@cli.command()
@click.option('--cash', type=float, required=True, help='剩余现金')
@click.option('--months', type=int, required=True, help='剩余建仓月数')
def ashare_invest(cash, months):
    """
    基于价值+风险模型的 A 股智能定投计算 (简化版)。
    参数从 data/market_metrics.json 中读取。
    """
    metrics = load_market_metrics()
    engine = DCAEngine(config_load_helper()) # Using helper to fix logic
    config_data = config_loader.configs

    found = False
    for symbol, cfg in config_data.items():
        if cfg.get('type') == 'ashare':
            asset_metrics = metrics.get(symbol, {})
            result = engine.calculate_smart_invest(
                symbol=symbol,
                market_metrics=asset_metrics,
                cash_remaining=cash,
                months_left=months
            )
            if "error" in result:
                click.echo(f"{symbol}: {result['error']}")
                continue

            found = True
            print_result(symbol, result)

    if not found:
        click.echo("未在配置中找到 A 股资产。")

@cli.command()
@click.option('--cash', type=float, required=True, help='剩余现金')
@click.option('--months', type=int, required=True, help='剩余建仓月数')
def us_invest(cash, months):
    """
    基于成长+恐慌模型的 美股智能定投计算 (简化版)。
    参数从 data/market_metrics.json 中读取。
    """
    metrics = load_market_metrics()
    engine = DCAEngine(config_loader)
    config_data = config_loader.configs

    found = False
    for symbol, cfg in config_data.items():
        if cfg.get('type') == 'usshare':
            asset_metrics = metrics.get(symbol, {})
            result = engine.calculate_smart_invest(
                symbol=symbol,
                market_metrics=asset_metrics,
                cash_remaining=cash,
                months_left=months
            )
            if "error" in result:
                click.echo(f"{symbol}: {result['error']}")
                continue

            found = True
            print_result(symbol, result)

    if not found:
        click.echo("未在配置中找到美股资产。")

@cli.command()
@click.option('--cash', type=float, required=True)
@click.option('--months', type=int, required=True)
def invest_all(cash, months):
    """
    批量计算所有配置资产的定投建议。
    """
    metrics = load_market_metrics()
    engine = DCAEngine(config_loader)
    config_data = config_loader.configs

    click.echo("开始批量计算...")
    for symbol, cfg in config_data.items():
        asset_metrics = metrics.get(symbol, {})
        result = engine.calculate_smart_invest(
            symbol=symbol,
            market_metrics=asset_metrics,
            cash_remaining=cash,
            months_left=months
        )
        if "error" in result:
            click.echo(f"{symbol}: {result['error']}")
            continue
        print_result(symbol, result)
    click.echo("\n批量计算完成。")

def config_load_helper():
    return config_loader

if __name__ == "__main__":
    cli()
