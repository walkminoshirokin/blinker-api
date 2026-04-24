import json
import logging
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright

from scraper import get_blinker_horses, run_scraping
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

RESULT_PATH = Path("/app/data/result.json")

app = FastAPI()
scheduler = create_scheduler()


@app.on_event("startup")
async def startup():
    scheduler.start()
    logger.info("スケジューラー起動完了")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    logger.info("スケジューラー停止")


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
async def scrape_all():
    logger.info("GET /scrape/all リクエスト受信")
    if not RESULT_PATH.exists():
        return JSONResponse(
            content={"error": "データ未生成。しばらくお待ちください"},
            media_type="application/json; charset=utf-8",
        )
    with open(RESULT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    logger.info("GET /scrape/all 返却: saved_at=%s", data.get("saved_at"))
    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.post("/scrape/run")
async def scrape_run():
    logger.info("POST /scrape/run リクエスト受信")
    try:
        results = await run_scraping()
        total = sum(len(races) for races in results.values())
        logger.info("POST /scrape/run 完了: %d 会場, 合計 %d レース処理", len(results), total)
        return JSONResponse(
            content={"message": "スクレイピング完了", "venues": len(results), "total_races": total},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("POST /scrape/run エラー: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
