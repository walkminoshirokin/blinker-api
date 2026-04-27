import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper import run_scraping

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")


async def _run_daily():
    date_str = datetime.now(JST).strftime("%Y%m%d")
    logger.info("定期スクレイピング開始: date=%s", date_str)
    await run_scraping(date_str)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_daily,
        trigger=CronTrigger(hour=8, minute=0, timezone=JST),
        id="daily_scraping",
        name="毎日8:00 JST スクレイピング",
        replace_existing=True,
    )
    return scheduler
