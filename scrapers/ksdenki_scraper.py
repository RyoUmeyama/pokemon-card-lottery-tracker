"""
ケーズデンキ（K's Denki）からポケモンカード抽選情報をスクレイピング
"""
import logging
import json
from datetime import datetime
import re

import requests
from .requests_base import RequestsBaseScraper

logger = logging.getLogger(__name__)


class KsDenkiScraper(RequestsBaseScraper):
    def __init__(self):
        super().__init__(timeout=30, wait_time=1)
        self.urls = []
        self.search_url = None
        self.source_name = 'ksdenki.co.jp'
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """抽選情報をスクレイピング"""
        all_lotteries = []

        # ケーズデンキはタイムアウトが頻発するため、現在は無効化
        # 将来的にAPIやより安定したエンドポイントが見つかれば再有効化

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'ケーズデンキ (ksdenki.co.jp)',
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_url(self, url):
        """URLから抽選情報を取得"""
        lotteries = []

        try:
            html_content = self.fetch_html(url)
            if not html_content:
                return lotteries

            soup = self.parse_soup(html_content)
            if not soup:
                return lotteries

            # リンクを探す
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                if self._is_pokemon_card(link_text):
                    lottery_info = self._parse_lottery_link(link, href)
                    if lottery_info:
                        lotteries.append(lottery_info)

            # 商品リスト要素を探す
            product_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['item', 'product', 'goods']
            ))

            for item in product_items:
                item_text = item.get_text()
                if self._is_pokemon_card(item_text):
                    lottery = self._parse_product_item(item)
                    if lottery:
                        lotteries.append(lottery)

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error for {url}: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}", exc_info=True)

        return lotteries

    def _is_pokemon_card(self, text):
        """ポケモンカード関連かチェック"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.pokemon_keywords)

    def _parse_lottery_link(self, link, href):
        """リンクから抽選情報を抽出"""
        try:
            link_text = link.get_text(strip=True)

            if href.startswith('/'):
                href = 'https://www.ksdenki.co.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.ksdenki.co.jp/' + href

            # 抽選関連キーワードがない場合はスキップ
            if not any(kw in link_text for kw in ['抽選', '予約', 'BOX', 'ボックス', 'パック']):
                return None

            parent = link.find_parent(['div', 'li', 'article', 'tr'])
            period = ''
            status = 'unknown'
            price = ''

            if parent:
                parent_text = parent.get_text()
                period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', parent_text)
                if period_match:
                    period = period_match.group(1)

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                if '受付中' in parent_text or '予約受付' in parent_text:
                    status = 'active'
                elif '終了' in parent_text or '売切' in parent_text:
                    status = 'closed'

            lottery = {
                'store': 'ケーズデンキ',
                'product': link_text,
                'lottery_type': '抽選販売' if '抽選' in link_text else '予約販売',
                'period': period,
                'price': price,
                'detail_url': href,
                'status': status
            }

            return lottery if link_text and len(link_text) > 5 else None

        except Exception:
            return None

    def _parse_product_item(self, item):
        """商品要素から抽選情報を抽出"""
        try:
            text = item.get_text(strip=True)

            # 抽選または予約関連でない場合はスキップ
            if not any(kw in text for kw in ['抽選', '予約', 'BOX', 'ボックス']):
                return None

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href.startswith('/'):
                href = 'https://www.ksdenki.co.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://www.ksdenki.co.jp/' + href

            title_elem = item.find(['h2', 'h3', 'h4', 'span', 'p', 'strong'])
            product_name = title_elem.get_text(strip=True) if title_elem else text[:100]

            period = ''
            period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', text)
            if period_match:
                period = period_match.group(1)

            price = ''
            price_match = re.search(r'[\d,]+円', text)
            if price_match:
                price = price_match.group()

            if product_name and href:
                return {
                    'store': 'ケーズデンキ',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': 'active' if '受付中' in text else 'unknown'
                }

        except Exception as e:
            logger.warning(f"Error: {e}", exc_info=False)

        return None

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
    scraper = KsDenkiScraper()
    data = scraper.scrape()

    if data:
        logger.info(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            logger.info(f"  - {lottery['product']}")
