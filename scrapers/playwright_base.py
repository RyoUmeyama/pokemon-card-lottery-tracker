"""
Playwrightを使用したベーススクレイパー
Bot対策のあるサイトに対応するためのヘッドレスブラウザ実装
"""
import asyncio
from datetime import datetime
import re
import random

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightBaseScraper:
    """Playwrightを使用するスクレイパーの基底クラス"""

    # 複数のUser-Agentをローテーション
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    ]

    def __init__(self):
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG',
            'ナイトワンダラー', 'クリムゾンヘイズ', 'レイジングサーフ',
            'ムニキスゼロ', 'MEGAドリーム', 'メガエルレイド', 'ロケット団',
            '抽選', '予約'
        ]
        self.timeout = 60000  # 60秒に延長
        self.navigation_timeout = 45000  # ナビゲーションタイムアウト

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
        if any(kw in text for kw in ['受付中', '予約可', '在庫あり', 'カートに入れる', '販売中', '応募する', '抽選受付']):
            return 'active'
        elif any(kw in text for kw in ['終了', '売切', '品切', '完売', '予約終了', '受付終了']):
            return 'closed'
        elif any(kw in text for kw in ['近日', '予定', 'まもなく']):
            return 'upcoming'
        return 'unknown'

    async def fetch_page_content(self, url, wait_selector=None, wait_for_js=True, scroll=True, extra_wait=2):
        """
        Playwrightでページコンテンツを取得

        Args:
            url: 取得するURL
            wait_selector: 待機するCSSセレクタ
            wait_for_js: JSの実行完了を待つか
            scroll: ページをスクロールするか
            extra_wait: 追加の待機時間（秒）
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("Warning: playwright is not installed")
            return None

        try:
            async with async_playwright() as p:
                # より本物のブラウザに近い設定でlaunch
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                        '--start-maximized',
                    ]
                )

                # ランダムなUser-Agentを選択
                user_agent = random.choice(self.USER_AGENTS)

                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    locale='ja-JP',
                    timezone_id='Asia/Tokyo',
                    # Webdriver検出を回避
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                    }
                )

                page = await context.new_page()

                # Webdriver検出を回避するスクリプト (強化版)
                await page.add_init_script("""
                    // webdriver プロパティを隠す
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // plugins を偽装
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            const plugins = [
                                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                                { name: 'Native Client', filename: 'internal-nacl-plugin' }
                            ];
                            plugins.length = 3;
                            return plugins;
                        }
                    });

                    // languages を偽装
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ja-JP', 'ja', 'en-US', 'en']
                    });

                    // Chrome オブジェクトを偽装
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };

                    // permissions を偽装
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );

                    // Headless検出を回避
                    Object.defineProperty(navigator, 'maxTouchPoints', {
                        get: () => 1
                    });

                    // WebGL vendor/renderer を偽装
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter.call(this, parameter);
                    };
                """)

                # ページにアクセス
                response = await page.goto(
                    url,
                    timeout=self.navigation_timeout,
                    wait_until='domcontentloaded'
                )

                if response and response.status >= 400:
                    print(f"HTTP Error {response.status} for {url}")
                    await browser.close()
                    return None

                # networkidleを待つ（タイムアウトしても続行）
                if wait_for_js:
                    try:
                        await page.wait_for_load_state('networkidle', timeout=15000)
                    except:
                        pass

                # 特定のセレクタを待つ場合
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=15000)
                    except:
                        pass  # セレクタが見つからなくても続行

                # ページ全体をスクロールして遅延読み込みコンテンツを取得
                if scroll:
                    await self._smooth_scroll(page)

                # 追加の待機時間（動的コンテンツのロード用）
                if extra_wait > 0:
                    await asyncio.sleep(extra_wait)

                content = await page.content()
                await browser.close()
                return content

        except Exception as e:
            print(f"Playwright error for {url}: {e}")
            return None

    async def _smooth_scroll(self, page):
        """人間らしいスムーズスクロール"""
        try:
            # 現在のスクロール高さを取得
            scroll_height = await page.evaluate('document.body.scrollHeight')
            viewport_height = await page.evaluate('window.innerHeight')

            current_position = 0
            while current_position < scroll_height:
                # ランダムなスクロール量
                scroll_amount = random.randint(300, 500)
                current_position += scroll_amount

                await page.evaluate(f'window.scrollTo(0, {current_position})')
                # ランダムな待機時間
                await asyncio.sleep(random.uniform(0.1, 0.3))

            # 最後にトップに戻る
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(0.5)

            # もう一度下までスクロール
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

        except Exception as e:
            print(f"Scroll error: {e}")

    async def fetch_with_retry(self, url, wait_selector=None, max_retries=3, **kwargs):
        """リトライ付きでページを取得"""
        for attempt in range(max_retries):
            content = await self.fetch_page_content(url, wait_selector, **kwargs)
            if content and len(content) > 1000:  # 最低限のコンテンツがあるか確認
                return content
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2, 4, 6秒と増加
                print(f"Retry {attempt + 1}/{max_retries} for {url}, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
        return None

    def run_async(self, coro):
        """非同期処理を同期的に実行"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 既にイベントループが実行中の場合は新しいループを作成
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(coro)
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
