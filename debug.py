import asyncio
from playwright.async_api import async_playwright

BASHO_CODE = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉"
}

async def debug_kaisai(date_str: str):
    url = f"https://race.netkeiba.com/top/?kaisai_date={date_str}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(5000)  # JS描画を長めに待つ

        # race_idを含む全リンクを取得
        all_race_ids = await page.evaluate("""() => {
            const anchors = document.querySelectorAll('a[href*="race_id"]');
            return Array.from(anchors).map(a => {
                const match = a.href.match(/race_id=(\d{12})/);
                return match ? match[1] : null;
            }).filter(Boolean);
        }""")

        print("=== 全race_id ===")
        for r in set(all_race_ids):
            print(r)

        # race_idの構造: YYYY + 場コード2桁 + 開催回2桁 + 日次2桁 + レース番号2桁
        # 場コードでグルーピングし、1Rに最も近いベースを取得
        kaisho = {}
        for race_id in set(all_race_ids):
            code = race_id[4:6]
            base = race_id[:10]
            name = BASHO_CODE.get(code, f"不明({code})")
            # 既存より小さいレース番号のベースを優先（1Rに近いもの）
            if name not in kaisho or base < kaisho[name]:
                kaisho[name] = base

        print("\n=== 取得した競馬場 ===")
        for name, base in kaisho.items():
            print(f"  {name}: {base}")

        await browser.close()

asyncio.run(debug_kaisai("20260426"))
