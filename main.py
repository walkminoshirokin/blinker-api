from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
from scraper import get_blinker_horses, run_scraping

app = FastAPI()


@app.get("/scrape")
async def scrape(race_id: str = Query(..., description="レースID (例: 202605020101)")):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()
            horses = await get_blinker_horses(page, race_id)
            await browser.close()
        return {"race_id": race_id, "blinker_horses": horses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/all")
async def scrape_all():
    try:
        results = await run_scraping()
        return JSONResponse(
            content={"results": results},
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
