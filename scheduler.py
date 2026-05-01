from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import logging
from scraper import run_scraping

JST = ZoneInfo("Asia/Tokyo")
logger = logging.getLogger(__name__)


def create_scheduler():
    scheduler = AsyncIOScheduler(timezone=JST)
    # 毎日6時JSTに翌日データ生成＋当日データ更新
    scheduler.add_job(
        run_scraping_both,
        "cron",
        hour=6,
        minute=0,
        id="daily_scraping_both",
    )
    return scheduler


async def run_scraping_both():
    today = datetime.now(JST)
    today_str = today.strftime("%Y%m%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y%m%d")

    # 当日データ更新
    logger.info("定時バッチ開始（当日）: %s", today_str)
    try:
        await run_scraping(today_str)
        logger.info("定時バッチ完了（当日）: %s", today_str)
    except Exception as e:
        logger.error("定時バッチエラー（当日）: %s", e)

    # 翌日データ生成
    logger.info("定時バッチ開始（翌日）: %s", tomorrow_str)
    try:
        await run_scraping(tomorrow_str)
        logger.info("定時バッチ完了（翌日）: %s", tomorrow_str)
    except Exception as e:
        logger.error("定時バッチエラー（翌日）: %s", e)
