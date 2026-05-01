import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper import run_scraping

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")


async def run_scraping_today():
    date_str = datetime.now(JST).strftime("%Y%m%d")
    logger.info("定時バッチ開始（当日）: %s", date_str)
    await run_scraping(date_str)
    logger.info("定時バッチ完了（当日）: %s", date_str)


async def run_scraping_tomorrow():
    tomorrow = datetime.now(JST) + timedelta(days=1)
    date_str = tomorrow.strftime("%Y%m%d")
    logger.info("定時バッチ開始（翌日）: %s", date_str)
    await run_scraping(date_str)
    logger.info("定時バッチ完了（翌日）: %s", date_str)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=JST)
    scheduler.add_job(
        run_scraping_today,
        trigger=CronTrigger(hour=8, minute=0, timezone=JST),
        id="daily_scraping_today",
        name="毎日8:00 JST スクレイピング（当日）",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scraping_tomorrow,
        trigger=CronTrigger(hour=6, minute=0, timezone=JST),
        id="daily_scraping_tomorrow",
        name="毎日6:00 JST スクレイピング（翌日）",
        replace_existing=True,
    )
    return scheduler
