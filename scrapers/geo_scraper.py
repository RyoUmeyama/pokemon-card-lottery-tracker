"""
GEO（ゲオ）オンラインストアからのポケモンカード予約・抽選情報スクレイピング
"""
from datetime import datetime
import json
import logging
import re
import time

from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class GeoScraper:
    def __init__(self):
        # GEOオンラインストアのポケモンカード検索ページ
        self.base_url = "https://www.geo-online.co.jp"
        self.search_urls = [
            "https://www.geo-online.co.jp/search?q=ポケモンカード&category=game_card",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Referer': 'https://www.geo-online.co.jp',
        }
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'ナイトワンダラー',
            'テラスタル', 'クリムゾンヘイズ', 'シャイニートレジャー',
            'レイジングサーフ', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """予約・抽選情報をスクレイピング"""
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
            "source": "geo-online.co.jp",
            "scraped_at": datetime.now().isoformat(),
            "lotteries": all_lotteries,
            "reservations": all_reservations
        }

    def _scrape_url(self, url):
        """指定URLをスクレイピング"""
        lotteries = []
        reservations = []

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                logger.warning(f"HTTP Error: {response.status_code}")
                return lotteries, reservations

            soup = BeautifulSoup(response.content, 'html.parser')

            # 商品一覧を取得
            product_items = soup.select('div.product-item, div.goods-item, li.goods-list-item')

            for item in product_items:
                try:
                    # 商品名を取得
                    name_elem = item.select_one('a.product-name, a.goods-name, h2')
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
                    price_elem = item.select_one('span.price, span.sale-price, span.goods-price')
                    price = price_elem.get_text(strip=True) if price_elem else "価格未定"

                    # ステータス確認
                    status_text = item.get_text(strip=True)

                    # 予約か抽選かを判定
                    if '予約' in status_text or '予約受付' in status_text:
                        reservations.append({
                            'title': product_name,
                            'price': price,
                            'availability': '予約受付中',
                            'url': product_link,
                            'store': 'GEO',
                            'source': 'geo-online.co.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                    elif '抽選' in status_text or '抽選受付' in status_text:
                        lotteries.append({
                            'product': product_name,
                            'price': price,
                            'status': '抽選受付中',
                            'url': product_link,
                            'store': 'GEO',
                            'source': 'geo-online.co.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                    else:
                        # ステータス不明の場合は予約リストに追加
                        reservations.append({
                            'title': product_name,
                            'price': price,
                            'availability': '確認中',
                            'url': product_link,
                            'store': 'GEO',
                            'source': 'geo-online.co.jp',
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
