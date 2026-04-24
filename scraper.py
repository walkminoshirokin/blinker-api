import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

RESULT_PATH = Path("/app/data/result.json")
JST = ZoneInfo("Asia/Tokyo")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

KAISHO = {
    "東京": "2026050201",
    "京都": "2026080301",
    "福島": "2026030105",
}


async def get_blinker_horses(page, race_id: str):
    url = f"https://race.netkeiba.com/race/newspaper.html?race_id={race_id}&rf=shutuba_submenu"
    logger.info("ページ取得開始: %s", url)
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("load")
    await page.wait_for_timeout(1000)
    logger.debug("ページロード完了: race_id=%s", race_id)
    horses = await page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('span.Mark.First').forEach(span => {
            if (span.textContent.trim() !== 'B') return;
            const dt = span.closest('dt.Horse02');
            const nameEl = dt ? dt.querySelector('a') : null;
            const horseName = nameEl ? nameEl.textContent.trim() : '?';

            const dl = span.closest('dl.HorseList');
            const dataIndex = dl ? dl.getAttribute('data-index') : null;
            const umaNum = dataIndex !== null ? parseInt(dataIndex) + 1 : '?';

            results.push({ 馬番: umaNum, 馬名: horseName });
        });

        return results;
    }""")

    logger.info("race_id=%s: ブリンカー装着馬 %d 頭取得", race_id, len(horses))
    return horses


async def run_scraping():
    kaisho = {
        "東京": "2026050201",
        "京都": "2026080301",
        "福島": "2026030105",
    }
    all_results = {}
    logger.info("スクレイピング開始: %d 会場", len(kaisho))
    for basho, base in kaisho.items():
        all_results[basho] = {}
        logger.info("会場処理中: %s (base=%s)", basho, base)
        for i in range(1, 13):
            race_id = f"{base}{str(i).zfill(2)}"
            logger.info("  %sR 処理開始 (race_id=%s)", i, race_id)
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = await browser.new_page()
                try:
                    horses = await get_blinker_horses(page, race_id)
                    all_results[basho][f"{i}R"] = horses
                    logger.info("  %sR 完了: %d 頭", i, len(horses))
                except Exception as e:
                    logger.error("  %sR エラー (race_id=%s): %s", i, race_id, e)
                    all_results[basho][f"{i}R"] = {"error": str(e)}
                finally:
                    await browser.close()
    logger.info("スクレイピング完了")

    saved_at = datetime.now(JST).isoformat()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump({"saved_at": saved_at, "results": all_results}, f, ensure_ascii=False, indent=2)
    logger.info("result.json 保存完了: %s", saved_at)

    return all_results


async def main():
    results = await run_scraping()
    for basho, races in results.items():
        print(f"\n{'='*30}")
        print(f"  {basho}")
        print(f"{'='*30}")
        for race_key, horses in races.items():
            if isinstance(horses, dict) and "error" in horses:
                print(f"  {race_key}: エラー → {horses['error']}")
            elif horses:
                print(f"  {race_key} ブリンカー装着馬:")
                for h in horses:
                    print(f"    馬番{h['馬番']} {h['馬名']}")
            else:
                print(f"  {race_key}: Bマークなし")

