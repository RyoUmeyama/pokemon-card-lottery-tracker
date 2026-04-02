"""
駿河屋（suruga-ya.jp）からのポケモンカード抽選・予約情報スクレイピング
"""
from datetime import datetime
import json
import logging
import re

from .requests_base import RequestsBaseScraper

logger = logging.getLogger(__name__)


class SurugayaScraper(RequestsBaseScraper):
    def __init__(self):
        super().__init__(timeout=30, wait_time=1)
        self.base_url = "https://www.suruga-ya.jp"
        self.search_urls = [
            "https://www.suruga-ya.jp/search?keyword=ポケモンカード&cabinet=1&sort=popular&condition=all"
        ]
        self.source_name = 'suruga-ya.jp'
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'ナイトワンダラー',
            'テラスタル', 'クリムゾンヘイズ', 'シャイニートレジャー',
            'レイジングサーフ', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """抽選・予約情報をスクレイピング"""
        all_lotteries = []
        all_reservations = []

        for url in self.search_urls:
            try:
                logger.info(f"Scraping {url}")
                lotteries, reservations = self._scrape_url(url)
                all_lotteries.extend(lotteries)
                all_reservations.extend(reservations)
            except Exception as e:
                logger.warning(f"Error scraping {url}: {e}")
                continue

        return {
                'timestamp': datetime.now().isoformat(),
            "source": "suruga-ya.jp",
            "scraped_at": datetime.now().isoformat(),
            "lotteries": all_lotteries,
            "reservations": all_reservations
        }

    def _scrape_url(self, url):
        """指定URLをスクレイピング"""
        lotteries = []
        reservations = []

        try:
            html_content = self.fetch_html(url)
            if not html_content:
                return lotteries, reservations

            soup = self.parse_soup(html_content)
            if not soup:
                return lotteries, reservations

            # 商品一覧を取得
            product_items = soup.select('div.item_box, div.product-item')

            for item in product_items:
                try:
                    # 商品名を取得
                    name_elem = item.select_one('a.item_name, a.product-name')
                    if not name_elem:
                        continue

                    product_name = name_elem.get_text(strip=True)

                    # ポケモンキーワードフィルタ
                    if not any(keyword in product_name for keyword in self.pokemon_keywords):
                        continue

                    # リンク取得
                    product_link = name_elem.get('href', '')
                    if product_link and not product_link.startswith('http'):
                        product_link = self.base_url + product_link

                    # 価格取得
                    price_elem = item.select_one('span.price, span.sale-price')
                    price = price_elem.get_text(strip=True) if price_elem else "価格未定"

                    # ステータス確認（予約中/販売中/抽選中等）
                    status_elem = item.select_one('span.status, span.badge')
                    status = status_elem.get_text(strip=True) if status_elem else "未定"

                    # 予約か抽選かを判定
                    if '予約' in status or '予約受付' in status:
                        reservations.append({
                            'title': product_name,
                            'price': price,
                            'availability': status,
                            'url': product_link,
                            'source': 'suruga-ya.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                    elif '抽選' in status or '抽選受付' in status:
                        lotteries.append({
                            'product': product_name,
                            'price': price,
                            'status': status,
                            'url': product_link,
                            'store': '駿河屋',
                            'source': 'suruga-ya.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.debug(f"Error parsing product item: {e}")
                    continue

            logger.info(f"Found {len(lotteries)} lottery entries and {len(reservations)} reservations")

        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Scraping error: {e}")

        return lotteries, reservations
