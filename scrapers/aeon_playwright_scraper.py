"""
イオン - Playwright版スクレイパー
Bot対策を回避するためヘッドレスブラウザを使用
"""
from bs4 import BeautifulSoup
from datetime import datetime
from .playwright_base import PlaywrightBaseScraper, PLAYWRIGHT_AVAILABLE


class AeonPlaywrightScraper(PlaywrightBaseScraper):
    def __init__(self):
        super().__init__()
        self.search_url = "https://www.aeonretail.jp/campaign/"
        self.source_name = 'イオン (aeonretail.jp)'

    def scrape(self):
        """Playwrightでキャンペーン情報をスクレイピング"""
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'source': self.source_name,
                'source_url': self.search_url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': 'playwright not installed'
            }

        lotteries = []

        try:
            content = self.run_async(self.fetch_page_content(
                self.search_url,
                wait_selector='.campaign'
            ))

            if content:
                lotteries = self._parse_content(content)
        except Exception as e:
            print(f"Error scraping aeon: {e}")

        unique_lotteries = self.remove_duplicates(lotteries)

        return {
            'source': self.source_name,
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

    def _parse_content(self, content):
        """HTMLコンテンツをパース"""
        lotteries = []
        soup = BeautifulSoup(content, 'html.parser')

        # キャンペーン・商品アイテムを探す
        items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
            kw in str(x).lower() for kw in ['item', 'product', 'campaign', 'card', 'banner']
        ))

        for item in items:
            lottery = self._parse_item(item)
            if lottery:
                lotteries.append(lottery)

        # リンクからも探す
        links = soup.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            href = link.get('href', '')

            if self.is_pokemon_card(text):
                lottery = self._parse_link(link, href, text)
                if lottery:
                    lotteries.append(lottery)

        return lotteries

    def _parse_item(self, item):
        """商品アイテムから情報を抽出"""
        try:
            text = item.get_text(strip=True)

            if not self.is_pokemon_card(text):
                return None

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href and not href.startswith('http'):
                href = 'https://www.aeonretail.jp' + href

            # 商品名・キャンペーン名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'ttl']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name or len(product_name) < 5:
                product_name = text[:150]

            price = self.extract_price(text)
            status = self.determine_status(text)
            period = self.extract_period(text)

            if product_name and href:
                return {
                    'store': 'イオン',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else 'キャンペーン',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None

    def _parse_link(self, link, href, text):
        """リンクから情報を抽出"""
        try:
            if not href.startswith('http'):
                href = 'https://www.aeonretail.jp' + href

            parent = link.find_parent(['div', 'li', 'article'])
            parent_text = parent.get_text() if parent else text

            price = self.extract_price(parent_text)
            status = self.determine_status(parent_text)
            period = self.extract_period(parent_text)

            if len(text) > 5:
                return {
                    'store': 'イオン',
                    'product': text,
                    'lottery_type': '抽選販売' if '抽選' in parent_text else 'キャンペーン',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None


if __name__ == '__main__':
    scraper = AeonPlaywrightScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product'][:50]}...")
