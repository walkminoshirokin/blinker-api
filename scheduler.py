from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import logging
from scraper import run_scraping

JST = ZoneInfo("Asia/Tokyo")
logger = logging.getLogger(__name__)


def create_scheduler():
    scheduler = AsyncIOScheduler(timezone=JST)
    # 毎日6時JSTに前日データ回収率更新＋翌日データ先行生成
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
    yesterday_str = (today - timedelta(days=1)).strftime("%Y%m%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y%m%d")

    # 前日データの回収率更新
    logger.info("定時バッチ開始（前日更新）: %s", yesterday_str)
    try:
        await run_scraping(yesterday_str)
        logger.info("定時バッチ完了（前日更新）: %s", yesterday_str)
    except Exception as e:
        logger.error("定時バッチエラー（前日更新）: %s", e)

    # 翌日データの先行生成
    logger.info("定時バッチ開始（翌日生成）: %s", tomorrow_str)
    try:
        await run_scraping(tomorrow_str)
        logger.info("定時バッチ完了（翌日生成）: %s", tomorrow_str)
    except Exception as e:
        logger.error("定時バッチエラー（翌日生成）: %s", e)
