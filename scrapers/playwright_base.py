"""
Playwrightを使用したベーススクレイパー
Bot対策のあるサイトに対応するためのヘッドレスブラウザ実装
"""
import asyncio
from datetime import datetime
import re

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightBaseScraper:
    """Playwrightを使用するスクレイパーの基底クラス"""

    def __init__(self):
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG',
            'ナイトワンダラー', 'クリムゾンヘイズ', 'レイジングサーフ'
        ]
        self.timeout = 30000  # 30秒

    def is_pokemon_card(self, text):
        """ポケモンカード関連かチェック"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.pokemon_keywords)

    def extract_price(self, text):
        """価格を抽出"""
        if not text:
            return ''
        price_match = re.search(r'[\d,]+円', text)
        return price_match.group() if price_match else ''

    def extract_period(self, text):
        """期間を抽出"""
        if not text:
            return ''
        patterns = [
            r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}/\d{1,2}/\d{1,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ''

    def determine_status(self, text):
        """ステータスを判定"""
        if not text:
            return 'unknown'
        if any(kw in text for kw in ['受付中', '予約可', '在庫あり', 'カートに入れる', '販売中']):
            return 'active'
        elif any(kw in text for kw in ['終了', '売切', '品切', '完売', '予約終了']):
            return 'closed'
        elif any(kw in text for kw in ['近日', '予定', 'まもなく']):
            return 'upcoming'
        return 'unknown'

    async def fetch_page_content(self, url, wait_selector=None):
        """Playwrightでページコンテンツを取得"""
        if not PLAYWRIGHT_AVAILABLE:
            print("Warning: playwright is not installed")
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='ja-JP'
                )
                page = await context.new_page()

                # ページにアクセス
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')

                # 特定のセレクタを待つ場合
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=10000)
                    except:
                        pass  # セレクタが見つからなくても続行

                # ページ全体をスクロールして遅延読み込みコンテンツを取得
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)

                content = await page.content()
                await browser.close()
                return content

        except Exception as e:
            print(f"Playwright error for {url}: {e}")
            return None

    def run_async(self, coro):
        """非同期処理を同期的に実行"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def remove_duplicates(self, lotteries):
        """重複を除去"""
        seen = set()
        unique = []

        for lottery in lotteries:
            key = (lottery.get('product', ''), lottery.get('detail_url', ''))
            if key not in seen and lottery.get('product'):
                seen.add(key)
                unique.append(lottery)

        return unique
