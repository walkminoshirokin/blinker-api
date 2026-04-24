import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper import run_scraping

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scraping,
        trigger=CronTrigger(hour=8, minute=0, timezone=JST),
        id="daily_scraping",
        name="毎日8:00 JST スクレイピング",
        replace_existing=True,
    )
    return scheduler
