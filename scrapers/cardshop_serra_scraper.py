"""
カードショップセラ（Card Shop Serra）からポケモンカード抽選・予約情報をスクレイピング
トレカ専門店として有名なカードショップ
"""
import logging
import json
from datetime import datetime
import re

from .requests_base import RequestsBaseScraper

logger = logging.getLogger(__name__)


class CardShopSerraScraper(RequestsBaseScraper):
    def __init__(self):
        super().__init__(timeout=30, wait_time=1)
        # カードショップセラ（ドメインが解決できないため無効化）
        self.urls = []  # DNS解決エラーのためスキップ
        self.source_name = 'cardshopserra.jp'
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """抽選・予約情報をスクレイピング"""
        all_lotteries = []

        for url in self.urls:
            try:
                lotteries = self._scrape_url(url)
                all_lotteries.extend(lotteries)
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}", exc_info=True)

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'カードショップセラ (cardshopserra.jp)',
            'source_url': 'https://www.cardshopserra.jp/',
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries,
            'note': 'DNS解決エラーのため現在無効化'
        }

        return result

    def _scrape_url(self, url):
        """URLからポケモンカード情報を取得"""
        lotteries = []

        try:
            html_content = self.fetch_html(url)
            if not html_content:
                return lotteries

            soup = self.parse_soup(html_content)
            if not soup:
                return lotteries

            # 商品アイテムを探す
            product_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'list']
            ))

            for item in product_items:
                lottery = self._parse_product_item(item)
                if lottery:
                    lotteries.append(lottery)

            # リンクから直接探す
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                if self._is_pokemon_card(link_text) and '/shopdetail/' in href:
                    lottery = self._parse_product_link(link, href)
                    if lottery:
                        lotteries.append(lottery)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}", exc_info=True)

        return lotteries

    def _parse_product_item(self, item):
        """商品要素から情報を抽出"""
        try:
            text = item.get_text(strip=True)

            if not self._is_pokemon_card(text):
                return None

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href.startswith('/'):
                href = 'https://www.cardshopserra.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://www.cardshopserra.jp/' + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    if self._is_pokemon_card(line) and len(line) > 10:
                        product_name = line[:150]
                        break

            # 価格を取得
            price = ''
            price_match = re.search(r'[\d,]+円', text)
            if price_match:
                price = price_match.group()

            # ステータス判定
            status = 'unknown'
            if '予約受付中' in text or '在庫あり' in text:
                status = 'active'
            elif '売切' in text or '品切' in text or '完売' in text:
                status = 'closed'

            # 予約または抽選関連のみ
            if not any(kw in text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック']):
                return None

            if product_name and href:
                return {
                'timestamp': datetime.now().isoformat(),
                    'store': 'カードショップセラ',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
                    'period': '',
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.warning(f"Error: {e}", exc_info=False)

        return None

    def _parse_product_link(self, link, href):
        """商品リンクから情報を抽出"""
        try:
            link_text = link.get_text(strip=True)

            if not any(kw in link_text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック']):
                return None

            if href.startswith('/'):
                href = 'https://www.cardshopserra.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.cardshopserra.jp/' + href

            parent = link.find_parent(['div', 'li', 'article'])
            price = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                if '予約受付中' in parent_text or '在庫あり' in parent_text:
                    status = 'active'
                elif '売切' in parent_text or '品切' in parent_text:
                    status = 'closed'

            if len(link_text) > 10:
                return {
                'timestamp': datetime.now().isoformat(),
                    'store': 'カードショップセラ',
                    'product': link_text,
                    'lottery_type': '抽選販売' if '抽選' in link_text else '予約販売',
                    'period': '',
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception as e:
            logger.warning(f"Error: {e}", exc_info=False)

        return None

    def _is_pokemon_card(self, text):
        """ポケモンカード関連かチェック"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.pokemon_keywords)

    def _remove_duplicates(self, lotteries):
        """重複を除去"""
        seen = set()
        unique = []

        for lottery in lotteries:
            key = (lottery.get('product', ''), lottery.get('detail_url', ''))
            if key not in seen and lottery.get('product'):
                seen.add(key)
                unique.append(lottery)

        return unique


if __name__ == '__main__':
    scraper = CardShopSerraScraper()
    data = scraper.scrape()

    if data:
        logger.info(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            logger.info(f"  - {lottery['product']}")
