"""
TSUTAYAオンラインからのポケモンカード予約・抽選情報スクレイピング
"""
from datetime import datetime
import json
import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TsutayaScraper:
    def __init__(self):
        # TSUTAYAオンラインのポケモンカード検索ページ
        self.base_url = "https://tsutaya.tsite.jp"
        self.search_urls = [
            "https://tsutaya.tsite.jp/search/?keyword=ポケモンカード&sort=release_date&area=&status=",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Referer': 'https://tsutaya.tsite.jp',
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
            "source": "tsutaya.tsite.jp",
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
            product_items = soup.select('div.product-box, div.item-box, li.item-list')

            for item in product_items:
                try:
                    # 商品名を取得
                    name_elem = item.select_one('a.product-title, a.item-name, h3')
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
                    price_elem = item.select_one('span.price, span.sale-price, span.item-price')
                    price = price_elem.get_text(strip=True) if price_elem else "価格未定"

                    # 入荷/在庫状況を取得
                    status_elem = item.select_one('span.status, span.stock-status')
                    status = status_elem.get_text(strip=True) if status_elem else "確認中"

                    # 予約か抽選かを判定
                    if '予約' in status or '予約受付' in status or '予約可能' in status:
                        reservations.append({
                            'title': product_name,
                            'price': price,
                            'availability': status,
                            'url': product_link,
                            'store': 'TSUTAYA',
                            'source': 'tsutaya.tsite.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                    elif '抽選' in status or '抽選受付' in status:
                        lotteries.append({
                            'product': product_name,
                            'price': price,
                            'status': status,
                            'url': product_link,
                            'store': 'TSUTAYA',
                            'source': 'tsutaya.tsite.jp',
                            'scraped_at': datetime.now().isoformat()
                        })
                    else:
                        # その他の場合は予約リストに追加
                        reservations.append({
                            'title': product_name,
                            'price': price,
                            'availability': status,
                            'url': product_link,
                            'store': 'TSUTAYA',
                            'source': 'tsutaya.tsite.jp',
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
