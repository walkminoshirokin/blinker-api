import asyncio
from playwright.async_api import async_playwright

KAISHO = {
    "東京": "2026050201",
    "京都": "2026080301",
    "福島": "2026030105",
}


async def get_blinker_horses(page, race_id: str):
    url = f"https://race.netkeiba.com/race/newspaper.html?race_id={race_id}&rf=shutuba_submenu"
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("load")
    await page.wait_for_timeout(1000)
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

    return horses


async def run_scraping():
    kaisho = {
        "東京": "2026050201",
        "京都": "2026080301",
        "福島": "2026030105",
    }
    all_results = {}
    for basho, base in kaisho.items():
        all_results[basho] = {}
        for i in range(1, 13):
            race_id = f"{base}{str(i).zfill(2)}"
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = await browser.new_page()
                try:
                    horses = await get_blinker_horses(page, race_id)
                    all_results[basho][f"{i}R"] = horses
                except Exception as e:
                    all_results[basho][f"{i}R"] = {"error": str(e)}
                finally:
                    await browser.close()
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

