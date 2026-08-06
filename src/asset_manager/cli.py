import click
from .storage import DataManager
from .engine import Rebalancer
from .models import Portfolio
from .config_loader import ConfigLoader

# 初始化数据管理层和配置加载器
storage = DataManager()
config_loader = ConfigLoader()

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
    包括总价值、各资产实际权重以及与目标权重的偏差（Drift）。
    """
    portfolio = storage.load_portfolio()
    total_value = portfolio.get_total_value()

    click.echo(f"投资组合总价值: {total_value:.2f}")
    click.echo("-" * 40)
    click.echo(f"{'资产名称':<15} {'当前价值':<10} {'实际权重':<10} {'权重偏差':<10}")

    drifts = portfolio.get_allocation_drift()
    for asset in portfolio.assets:
        current_weight = asset.calculate_current_weight(total_value)
        drift = next(d[1] for d in drifts if d[0] == asset.symbol)
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
            target_value = total * asset.target_weight
            diff = target_value - asset.current_value
            action = "买入" if diff > 0 else "卖出" if diff < 0 else "无需操作"
            diff_str = f"{abs(diff):.2f} {action}" if diff != 0 else "0.00"

            click.echo(f"{asset.symbol:<15} {asset.current_value:<12.2f} {target_value:<12.2f} {diff_str:<12}")

            cat_target_value += target_value
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
@click.option('--pe', type=float, help='PE历史百分位(0-100)')
@click.option('--pb', type=float, help='PB历史百分位(0-100)')
@click.option('--erp', type=float, help='ERP历史百分位(0-100)')
@click.option('--dd', type=float, help='距离最高点跌幅(0-1.0, 如 0.1 代表 10%)')
@click.option('--cash', type=float, help='剩余现金')
@click.option('--months', type=int, help='剩余建仓月数')
def ashare_invest(pe, pb, erp, dd, cash, months):
    """
    基于价值+风险模型的 A 股智能定投计算。
    通过估值百分位和回撤幅度，动态调整每月定投金额。
    """
    # 加载默认配置
    cfg = config_loader.get_ashare_params()
    pe = pe if pe is not None else cfg.get('pe_percentile')
    pb = pb if pb is not None else cfg.set('pb_percentile') # Wait, I used set instead of get. I should use .get
    scores = result["scores"]

    click.echo("\n=== A股智能定投计算结果 ===")
    click.echo(f"估值评分 (ValueScore):   {scores['value_score']:.2f}")
    click.echo(f"回撤评分 (DrawdownScore): {scores['drawdown_score']:.2f}")
    click.echo(f"综合评分 (MarketScore):   {scores['market_score']:.2f}")
    click.echo(f"当前倍率 (Multiplier):     {scores['multiplier']:.2f}x")
    click.echo("-" * 30)
    click.echo(f"基础定投金额:             {scores['base_amount']:.2f}")
    click.echo(f"建议本次投入:             {result['final_investment']:.2f}")

    if result['final_investment'] < (scores['base_amount'] * scores['multiplier']):
        click.echo("\n⚠️  注意：投入金额已触发 10% 现金上限限制。")
    click.echo("============================\n")

@cli.command()
@click.option('--fpe', type=float, required=True, help='Forward PE历史百分位(0-100)')
@click.option('--peg', type=float, required=True, help='PEG历史百分位(0-100)')
@click.option('--vix', type=float, required=True, help='VIX指数')
@click.option('--fed', type=float, required=True, help='利率历史百分位(0-100)')
@click.option('--dd', type=float, required=True, help='距离最高点跌幅(0-1.0, 如 0.1 代表 10%)')
@click.option('--cash', type=float, required=True, help='剩余现金')
@click.option('--months', type=int, required=True, help='剩余建仓月数')
def us_invest(fpe, peg, vix, fed, dd, cash, months):
    """
    基于成长+恐慌模型的 美股智能定投计算。
    综合前瞻PE、PEG、VIX指数和利率水平，动态调整每月定投金额。
    """
    from .engine import DCAEngine
    result = DCAEngine.calculate_ushare_smart_invest(fpe, peg, vix, fed, dd, cash, months)
    scores = result["scores"]

    click.echo("\n=== 美股智能定投计算结果 ===")
    click.echo(f"成长评分 (GrowthScore):   {scores['growth_score']:.2f}")
    click.echo(f"VIX评分 (VIXScore):       {scores['vix_score']:.2f}")
    click.echo(f"利率评分 (RateScore):     {scores['rate_score']:.2f}")
    click.echo(f"综合评分 (USScore):       {scores['us_score']:.2f}")
    click.echo(f"当前倍率 (Multiplier):     {scores['multiplier']:.2f}x")
    click.echo("-" * 30)
    click.echo(f"基础定投金额:             {scores['base_amount']:.2f}")
    click.echo(f"建议本次投入:             {result['final_investment']:.2f}")

    if result['final_investment'] < (scores['base_amount'] * scores['multiplier']):
        click.echo("\n⚠️  注意：投入金额已触发 10% 现金上限限制。")
    click.echo("============================\n")

if __name__ == "__main__":
    cli()
