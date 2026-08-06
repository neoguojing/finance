import logging
from typing import Dict, Any
from ..config_loader import ConfigLoader
from .fetcher import USFetcher, ASHareFetcher, BaseFetcher

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigUpdater:
    """配置更新器：负责从外部数据源抓取指标并写回 config.json。"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.fetchers: Dict[str, BaseFetcher] = {
            "us": USFetcher(),
            "ashare": ASHareFetcher()
        }

    def update_all_assets(self) -> None:
        """
        遍历配置中的资产，针对开启了 'auto_update' 的资产执行数据抓取与更新。
        """
        logger.info("开始执行配置自动更新任务...")
        config = self.config_loader.configs
        assets_config = config.get("assets", {})

        if not assets_config:
            logger.warning("未在配置中找到任何资产信息，跳过更新。")
            return

        updated_count = 0
        errors_count = 0

        for symbol, asset_info in assets_config.items():
            # 检查是否开启了自动更新标志 (假设我们在 config 中注入了这个字段)
            if not asset_info.get("auto_update", False):
                continue

            market = asset_info.get("market")
            fetcher = self.fetch_provider(market)

            if not fetcher:
                logger.error(f"无法为资产 {symbol} ({market}) 找到匹配的数据抓取器。")
                errors_count += 1
                continue

            logger.info(f"正在更新资产 [{symbol}] 的市场数据 (Market: {market})...")
            try:
                new_metrics = fetcher.fetch_metrics(symbol)
                if new_metrics:
                    # 将抓取到的新指标合并到原有的 metrics 中
                    current_metrics = asset_info.get("metrics", {})
                    asset_info["metrics"] = {**current_metrics, **new_metrics}
                    updated_count += 1
                    logger.info(f"资产 [{symbol}] 更新成功。")
                else:
                    logger.warning(f"资产 [{symbol}] 未能抓取到有效指标数据。")
                    errors_count += 1
            except Exception as e:
                logger.error(f"更新资产 [{symbol}] 时发生异常: {e}")
                errors_count += 1

        if updated_count > 0:
            # 执行写回磁盘操作
            self.config_loader.save(config)
            logger.info(f"配置更新完成！成功更新 {updated_count} 个资产，失败/跳过 {errors_count} 个。")
        else:
            logger.info("本次运行未发现需要更新的资产。")

    def fetch_provider(self, market: str) -> Any:
        """根据市场类型返回对应的抓取器实例。"""
        return self.fetchers.get(market)

if __name__ == "__main__":
    # 简单的命令行测试入口
    loader = ConfigLoader("data/config.json")
    updater = ConfigUpdater(loader)
    updater.update_all_assets()
