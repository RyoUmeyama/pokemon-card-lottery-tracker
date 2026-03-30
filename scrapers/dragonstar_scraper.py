"""
ドラゴンスター - Playwright版スクレイパー
Bot対策を回避するためヘッドレスブラウザを使用
"""
from bs4 import BeautifulSoup
from datetime import datetime
from .playwright_base import PlaywrightBaseScraper, PLAYWRIGHT_AVAILABLE
import logging

logger = logging.getLogger(__name__)


class DragonstarScraper(PlaywrightBaseScraper):
    def __init__(self):
        super().__init__()
        self.search_url = "https://dorasuta.membercard.jp/lottery"
        self.source_name = 'ドラゴンスター (dorasuta.membercard.jp)'

    def scrape(self):
        """Playwrightで抽選情報をスクレイピング"""
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
                wait_selector='div[class*="lottery"], [class*="event"], [class*="promotion"]',
                scroll=True,
                extra_wait=3
            ))

            if content:
                lotteries = self._parse_content(content)
        except Exception as e:
            logger.error(f"Error scraping dragonstar: {e}")

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

        # 抽選コンテナを探す（複数の可能性のあるセレクタ）
        lottery_containers = soup.find_all(['div', 'article', 'section'], class_=lambda x: x and any(
            kw in str(x).lower() for kw in ['lottery', 'event', 'promotion', 'campaign', 'raffle', 'entry']
        ))

        for container in lottery_containers:
            lottery = self._parse_lottery_item(container)
            if lottery:
                lotteries.append(lottery)

        # コンテナで見つからない場合はリンクから探す
        if not lotteries:
            links = soup.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')

                if self.is_pokemon_card(text) and href:
                    lottery = self._parse_link(link, href, text)
                    if lottery:
                        lotteries.append(lottery)

        return lotteries

    def _parse_lottery_item(self, item):
        """抽選アイテムから情報を抽出"""
        try:
            text = item.get_text(strip=True)

            if not self.is_pokemon_card(text):
                return None

            # リンクを取得
            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href and not href.startswith('http'):
                if href.startswith('/'):
                    href = 'https://dorasuta.membercard.jp' + href
                else:
                    href = 'https://dorasuta.membercard.jp/' + href

            # 商品名を取得
            title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'product', 'ttl', 'heading']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name or len(product_name) < 5:
                # テキストから商品名を推定
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    if self.is_pokemon_card(line) and len(line) >= 5:
                        product_name = line[:150]
                        break

            price = self.extract_price(text)
            period = self.extract_period(text)
            status = self.determine_status(text)

            if product_name and href:
                return {
                    'store': 'ドラゴンスター',
                    'product': product_name,
                    'lottery_type': '抽選',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.error(f"Error parsing lottery item: {e}")

        return None

    def _parse_link(self, link, href, text):
        """リンクから情報を抽出"""
        try:
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = 'https://dorasuta.membercard.jp' + href
                else:
                    href = 'https://dorasuta.membercard.jp/' + href

            parent = link.find_parent(['div', 'li', 'article', 'section'])
            parent_text = parent.get_text() if parent else text

            price = self.extract_price(parent_text)
            period = self.extract_period(parent_text)
            status = self.determine_status(parent_text)

            if len(text) >= 5:
                return {
                    'store': 'ドラゴンスター',
                    'product': text[:150],
                    'lottery_type': '抽選',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.error(f"Error parsing link: {e}")

        return None


if __name__ == '__main__':
    scraper = DragonstarScraper()
    data = scraper.scrape()

    if data:
        logger.info(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            logger.info(f"  - {lottery['product'][:50]}...")
