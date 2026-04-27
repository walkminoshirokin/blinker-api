import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from playwright.async_api import async_playwright

from scraper import get_blinker_horses, run_scraping
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")

app = FastAPI()
scheduler = create_scheduler()


def today_jst() -> str:
    return datetime.now(JST).strftime("%Y%m%d")


@app.on_event("startup")
async def startup():
    scheduler.start()
    logger.info("スケジューラー起動完了")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    logger.info("スケジューラー停止")


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.get("/scrape")
async def scrape(race_id: str = Query(..., description="レースID (例: 202605020101)")):
    logger.info("GET /scrape リクエスト: race_id=%s", race_id)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()
            horses = await get_blinker_horses(page, race_id)
            await browser.close()
        logger.info("GET /scrape 完了: race_id=%s, 結果 %d 頭", race_id, len(horses))
        return {"race_id": race_id, "blinker_horses": horses}
    except Exception as e:
        logger.error("GET /scrape エラー: race_id=%s, %s", race_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/all")
async def scrape_all(date: str = Query(None, description="日付 (例: 20260427)")):
    date_str = date or today_jst()
    result_path = Path(f"/app/data/result_{date_str}.json")
    logger.info("GET /scrape/all リクエスト受信: date=%s", date_str)
    if not result_path.exists():
        return JSONResponse(
            content={"error": "データ未生成。しばらくお待ちください"},
            media_type="application/json; charset=utf-8",
        )
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info("GET /scrape/all 返却: saved_at=%s", data.get("saved_at"))
    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.post("/scrape/run")
async def scrape_run(date: str = Query(None, description="日付 (例: 20260427)")):
    date_str = date or today_jst()
    logger.info("POST /scrape/run リクエスト受信: date=%s", date_str)
    try:
        results = await run_scraping(date_str)
        total = sum(len(races) for races in results.values())
        logger.info("POST /scrape/run 完了: %d 会場, 合計 %d レース処理", len(results), total)
        return JSONResponse(
            content={"message": "スクレイピング完了", "venues": len(results), "total_races": total},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("POST /scrape/run エラー: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
