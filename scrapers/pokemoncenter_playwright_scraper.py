"""
ポケモンセンターオンライン - Playwright版スクレイパー
抽選応募一覧ページをスクレイピング
"""
from bs4 import BeautifulSoup
from datetime import datetime
from .playwright_base import PlaywrightBaseScraper, PLAYWRIGHT_AVAILABLE


class PokemonCenterPlaywrightScraper(PlaywrightBaseScraper):
    def __init__(self):
        super().__init__()
        self.lottery_list_url = "https://www.pokemoncenter-online.com/lottery/apply.html"
        self.base_url = "https://www.pokemoncenter-online.com"
        self.source_name = 'ポケモンセンターオンライン (pokemoncenter-online.com)'

    def scrape(self):
        """Playwrightで抽選情報をスクレイピング"""
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'source': self.source_name,
                'source_url': self.lottery_list_url,
                'scraped_at': datetime.now().isoformat(),
                'has_active_lottery': False,
                'lotteries': [],
                'error': 'playwright not installed'
            }

        lotteries = []
        has_active = False

        try:
            # 抽選一覧ページを取得
            content = self.run_async(self.fetch_page_content(
                self.lottery_list_url,
                wait_selector='.lottery-list, .no-lottery, [class*="lottery"]',
                extra_wait=3
            ))

            if content:
                result = self._parse_lottery_list(content)
                lotteries = result['lotteries']
                has_active = result['has_active']

        except Exception as e:
            print(f"Error scraping pokemon center: {e}")

        unique_lotteries = self.remove_duplicates(lotteries)

        return {
            'source': self.source_name,
            'source_url': self.lottery_list_url,
            'scraped_at': datetime.now().isoformat(),
            'has_active_lottery': has_active,
            'lotteries': unique_lotteries
        }

    def _parse_lottery_list(self, content):
        """抽選一覧ページをパース"""
        lotteries = []
        has_active = False
        soup = BeautifulSoup(content, 'html.parser')

        # "公開中の抽選がありません"のチェック
        no_lottery_text = soup.get_text()
        if '公開中の抽選がありません' in no_lottery_text:
            return {'lotteries': [], 'has_active': False}

        # 抽選アイテムを探す（複数のパターンに対応）
        lottery_items = soup.find_all(['div', 'li', 'article', 'a'], class_=lambda x: x and any(
            kw in str(x).lower() for kw in ['lottery', 'item', 'product', 'card']
        ))

        for item in lottery_items:
            lottery = self._parse_lottery_item(item)
            if lottery:
                lotteries.append(lottery)
                if lottery.get('status') == 'active':
                    has_active = True

        # リンクからも探す
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # 抽選ページへのリンクを探す
            if ('lottery' in href or '抽選' in text) and self.is_pokemon_card(text):
                lottery = self._parse_lottery_link(link, href, text)
                if lottery:
                    lotteries.append(lottery)
                    if lottery.get('status') == 'active':
                        has_active = True

        return {'lotteries': lotteries, 'has_active': has_active}

    def _parse_lottery_item(self, item):
        """抽選アイテムから情報を抽出"""
        try:
            text = item.get_text(strip=True)

            if not text or len(text) < 10:
                return None

            link = item.find('a', href=True) if item.name != 'a' else item
            href = link.get('href', '') if link else ''

            if href and not href.startswith('http'):
                href = self.base_url + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'ttl', 'product']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name:
                # リンクテキストから取得
                product_name = text[:200]

            # 期間を取得
            period_elem = item.find(['p', 'span', 'div'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['period', 'date', 'time']
            ))
            period = period_elem.get_text(strip=True) if period_elem else self.extract_period(text)

            price = self.extract_price(text)
            status = self.determine_status(text)

            if product_name and href:
                return {
                    'store': 'ポケモンセンターオンライン',
                    'product': product_name,
                    'lottery_type': '抽選販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            print(f"Parse error: {e}")

        return None

    def _parse_lottery_link(self, link, href, text):
        """リンクから抽選情報を抽出"""
        try:
            if not href.startswith('http'):
                href = self.base_url + href

            parent = link.find_parent(['div', 'li', 'article'])
            parent_text = parent.get_text() if parent else text

            price = self.extract_price(parent_text)
            status = self.determine_status(parent_text)
            period = self.extract_period(parent_text)

            if len(text) > 5:
                return {
                    'store': 'ポケモンセンターオンライン',
                    'product': text,
                    'lottery_type': '抽選販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None


if __name__ == '__main__':
    scraper = PokemonCenterPlaywrightScraper()
    data = scraper.scrape()

    print(f"Has active lottery: {data.get('has_active_lottery')}")
    print(f"Found {len(data['lotteries'])} entries")
    for lottery in data['lotteries']:
        print(f"  - {lottery['product'][:50]}... ({lottery['status']})")
