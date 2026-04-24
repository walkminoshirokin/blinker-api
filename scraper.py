import asyncio
from playwright.async_api import async_playwright


async def get_blinker_horses(page, race_id: str):
    url = f"https://race.netkeiba.com/race/newspaper.html?race_id={race_id}&rf=shutuba_submenu"
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("load")
    await page.wait_for_timeout(2000)
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


async def main():
    kaisho = {
        "東京": "2026050201",
        "京都": "2026080301",
        "福島": "2026030105",
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for basho, base in kaisho.items():
            print(f"\n{'='*30}")
            print(f"  {basho}")
            print(f"{'='*30}")

            for i in range(1, 13):
                race_id = f"{base}{str(i).zfill(2)}"
                try:
                    horses = await get_blinker_horses(page, race_id)
                    if horses:
                        print(f"  {i}R ブリンカー装着馬:")
                        for h in horses:
                            print(f"    馬番{h['馬番']} {h['馬名']}")
                    else:
                        print(f"  {i}R: Bマークなし")
                except Exception as e:
                    print(f"  {i}R: エラー → {e}")

        await browser.close()


asyncio.run(main())
