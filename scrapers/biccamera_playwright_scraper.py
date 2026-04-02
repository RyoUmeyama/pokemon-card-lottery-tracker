"""
ビックカメラ - Playwright版スクレイパー
Bot対策を回避するためヘッドレスブラウザを使用
"""
from datetime import datetime
import logging

from bs4 import BeautifulSoup

from .playwright_base import PlaywrightBaseScraper, PLAYWRIGHT_AVAILABLE

logger = logging.getLogger(__name__)


class BiccameraPlaywrightScraper(PlaywrightBaseScraper):
    def __init__(self):
        super().__init__()
        self.search_url = "https://www.biccamera.com/bc/category/?q=ポケモンカード+抽選"
        self.source_name = 'ビックカメラ (biccamera.com)'

    def scrape(self):
        """Playwrightで抽選情報をスクレイピング"""
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'timestamp': datetime.now().isoformat(),
                'source': self.source_name,
                'source_url': self.search_url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': 'playwright not installed'
            }

        lotteries = []

        try:
            # ビックカメラはタイムアウト長めに設定（重い場合がある）
            content = self.run_async(self.fetch_page_content(
                self.search_url,
                wait_selector='.bcs_item',
                extra_wait=8
            ))

            if content:
                # 403エラーページのチェック
                if '403' in content or 'forbidden' in content.lower():
                    logger.warning("ビックカメラ: 403 Forbidden - アクセス制限中")
                    return {
                'timestamp': datetime.now().isoformat(),
                        'source': self.source_name,
                        'source_url': self.search_url,
                        'scraped_at': datetime.now().isoformat(),
                        'lotteries': [],
                        'error': '403 Forbidden'
                    }

                lotteries = self._parse_content(content)
        except TimeoutError:
            logger.error("Error scraping biccamera: Timeout - site may be slow or blocking")
            return {
                'timestamp': datetime.now().isoformat(),
                'source': self.source_name,
                'source_url': self.search_url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': 'Timeout'
            }
        except Exception as e:
            logger.error(f"Error scraping biccamera: {e}")

        unique_lotteries = self.remove_duplicates(lotteries)

        return {
                'timestamp': datetime.now().isoformat(),
            'source': self.source_name,
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

    def _parse_content(self, content):
        """HTMLコンテンツをパース"""
        lotteries = []
        soup = BeautifulSoup(content, 'html.parser')

        # 商品アイテムを探す
        items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
            kw in str(x).lower() for kw in ['item', 'product', 'bcs_item', 'goods']
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

            if self.is_pokemon_card(text) and '/bc/item/' in href:
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
                href = 'https://www.biccamera.com' + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'ttl']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name:
                product_name = text[:150]

            # 抽選・予約関連のみ
            if not any(kw in text for kw in ['抽選', '予約', 'BOX', 'ボックス', 'パック']):
                return None

            price = self.extract_price(text)
            status = self.determine_status(text)

            if product_name and href:
                return {
                'timestamp': datetime.now().isoformat(),
                    'store': 'ビックカメラ',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
                    'period': self.extract_period(text),
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.error(f"Error: {e}")

        return None

    def _parse_link(self, link, href, text):
        """リンクから情報を抽出"""
        try:
            if not href.startswith('http'):
                href = 'https://www.biccamera.com' + href

            parent = link.find_parent(['div', 'li', 'article'])
            parent_text = parent.get_text() if parent else text

            if not any(kw in parent_text for kw in ['抽選', '予約', 'BOX', 'ボックス', 'パック']):
                return None

            price = self.extract_price(parent_text)
            status = self.determine_status(parent_text)

            if len(text) > 10:
                return {
                'timestamp': datetime.now().isoformat(),
                    'store': 'ビックカメラ',
                    'product': text,
                    'lottery_type': '抽選販売' if '抽選' in parent_text else '予約販売',
                    'period': self.extract_period(parent_text),
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.error(f"Error: {e}")

        return None


if __name__ == '__main__':
    scraper = BiccameraPlaywrightScraper()
    data = scraper.scrape()

    if data:
        logger.info(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            logger.info(f"  - {lottery['product'][:50]}...")
