from fastapi import FastAPI, Query, HTTPException
from playwright.async_api import async_playwright
from scraper import get_blinker_horses

app = FastAPI()


@app.get("/scrape")
async def scrape(race_id: str = Query(..., description="レースID (例: 202605020101)")):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            horses = await get_blinker_horses(page, race_id)
            await browser.close()
        return {"race_id": race_id, "blinker_horses": horses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
