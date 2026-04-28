import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

JST = ZoneInfo("Asia/Tokyo")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASHO_CODE = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉"
}


async def get_kaisai_info(date_str: str):
    url = f"https://race.netkeiba.com/top/?kaisai_date={date_str}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(5000)
        all_race_ids = await page.evaluate("""() => {
            const anchors = document.querySelectorAll('a[href*="race_id"]');
            return Array.from(anchors).map(a => {
                const match = a.href.match(/race_id=(\\d{12})/);
                return match ? match[1] : null;
            }).filter(Boolean);
        }""")
        await browser.close()

    # 競馬場ごとに最小レース番号のベースIDを採用
    kaisho_tmp = {}
    for race_id in set(all_race_ids):
        code = race_id[4:6]
        base = race_id[:10]
        race_num = int(race_id[10:12])
        name = BASHO_CODE.get(code, f"不明({code})")
        if name not in kaisho_tmp or race_num < kaisho_tmp[name]["race_num"]:
            kaisho_tmp[name] = {"base": base, "race_num": race_num}

    kaisho = {name: info["base"] for name, info in kaisho_tmp.items()}
    return kaisho


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


async def get_race_result(page, race_id: str):
    """結果ページから着順と複勝払戻を取得"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}&rf=race_submenu"
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(1000)
        return await page.evaluate("""() => {
            const top3 = [];
            const rows = document.querySelectorAll('table tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length < 4) continue;
                const rank = cells[0].textContent.trim();
                if (['1', '2', '3'].includes(rank)) {
                    top3.push({
                        着順: rank,
                        馬番: cells[1].textContent.trim(),
                        馬名: cells[3].textContent.trim()
                    });
                }
                if (top3.length >= 3) break;
            }

            const fukusho = [];
            const fukushoRow = document.querySelector('tr.Fukusho');
            if (fukushoRow) {
                // td.Resultの全spanテキストを取得（空白除去後に空でないもの）
                const allSpans = fukushoRow.querySelectorAll('td.Result span');
                const numList = Array.from(allSpans)
                    .map(s => s.textContent.trim())
                    .filter(s => s !== '');
                // td.PayoutのinnerHTMLをbrで分割
                const payoutEl = fukushoRow.querySelector('td.Payout span');
                const payouts = payoutEl
                    ? payoutEl.innerHTML.split(/<br\s*\/?>/i)
                        .map(s => s.replace(/<[^>]+>/g, '').trim())
                        .filter(Boolean)
                    : [];
                numList.forEach((num, i) => {
                    fukusho.push({ 馬番: num, 払戻: payouts[i] || '' });
                });
            }

            return { top3, fukusho, has_result: top3.length > 0 };
        }""")
    except Exception:
        return {"top3": [], "fukusho": [], "has_result": False}


async def run_scraping(date_str: str = None):
    if date_str is None:
        date_str = datetime.now(JST).strftime("%Y%m%d")

    kaisho = await get_kaisai_info(date_str)
    result_path = Path(f"/app/data/result_{date_str}.json")

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
                    race_result = await get_race_result(page, race_id)
                    race_entries = []
                    for horse in horses:
                        uma_num = str(horse["馬番"])  # 数値→文字列に統一
                        chakujun = "-"
                        for t in race_result["top3"]:
                            # 両方strip()して比較
                            if t["馬番"].strip() == uma_num.strip():
                                chakujun = t["着順"]
                                break
                        race_entries.append({
                            "馬番": horse["馬番"],
                            "馬名": horse["馬名"],
                            "has_result": race_result["has_result"],
                            "top3": race_result["top3"],
                            "fukusho": race_result["fukusho"],
                            "着順": chakujun,
                        })
                    all_results[basho][f"{i}R"] = race_entries
                    logger.info("  %sR 完了: %d 頭", i, len(horses))
                except Exception as e:
                    logger.error("  %sR エラー (race_id=%s): %s", i, race_id, e)
                    all_results[basho][f"{i}R"] = {"error": str(e)}
                finally:
                    await browser.close()
    logger.info("スクレイピング完了")

    saved_at = datetime.now(JST).isoformat()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({"saved_at": saved_at, "results": all_results}, f, ensure_ascii=False, indent=2)
    logger.info("result_%s.json 保存完了: %s", date_str, saved_at)

    return all_results


async def main():
    results = await run_scraping()
    for basho, races in results.items():
        print(f"\n{'='*30}")
        print(f"  {basho}")
        print(f"{'='*30}")
        for race_key, entries in races.items():
            if isinstance(entries, dict) and "error" in entries:
                print(f"  {race_key}: エラー → {entries['error']}")
            elif entries:
                print(f"  {race_key} ブリンカー装着馬:")
                for h in entries:
                    print(f"    馬番{h['馬番']} {h['馬名']} 着順:{h['着順']}")
            else:
                print(f"  {race_key}: Bマークなし")
