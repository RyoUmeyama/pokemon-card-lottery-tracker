"""
Amazon予約情報スクレイパー
ポケモンカードの予約可能商品を検出
"""
from datetime import datetime
import json
import logging

from .requests_base import RequestsBaseScraper

logger = logging.getLogger(__name__)


class AmazonReservationScraper(RequestsBaseScraper):
    def __init__(self):
        super().__init__(timeout=30, wait_time=1)
        self.base_url = "https://www.amazon.co.jp"
        self.search_url = "https://www.amazon.co.jp/s"
        self.source_name = 'amazon.co.jp'
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'Pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """ポケモンカードの予約情報をスクレイピング"""
        try:
            products = []

            # 検索キーワード
            keywords = [
                "ポケモンカード 予約",
                "ポケモンカードゲーム 拡張パック",
                "ポケモンカード BOX"
            ]

            for keyword in keywords:
                logger.info(f"  検索中: {keyword}")
                keyword_products = self._search_products(keyword)
                products.extend(keyword_products)

            # 重複除外
            unique_products = self._remove_duplicates(products)

            result = {
                'source': 'amazon.co.jp',
                'scraped_at': datetime.now().isoformat(),
                'reservations': unique_products
            }

            return result

        except Exception as e:
            logger.error(f"Error scraping Amazon: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _search_products(self, keyword):
        """キーワードで商品を検索"""
        products = []

        try:
            params = {
                'k': keyword,
                'i': 'toys',
                '__mk_ja_JP': 'カタカナ',
                'crid': '2M096C61O4MLT',
                'sprefix': keyword,
                'ref': 'nb_sb_noss'
            }

            url = self.search_url + '?' + '&'.join(f"{k}={v}" for k, v in params.items())
            html_content = self.fetch_html(url)
            if not html_content:
                return products

            soup = self.parse_soup(html_content)
            if not soup:
                return products

            # 商品要素を取得
            items = soup.select('[data-component-type="s-search-result"]')

            for item in items[:20]:  # 上位20件を確認
                try:
                    product = self._parse_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"  Warning: Search error for '{keyword}': {e}")

        return products

    def _parse_product(self, item):
        """商品情報を抽出"""
        try:
            # タイトル（h2 span を探す）
            title_elem = item.select_one('h2 span')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # ポケモンカード関連でない場合はスキップ
            if not any(keyword in title for keyword in self.pokemon_keywords):
                return None

            # URL（h2 を囲むaタグを探す）
            h2 = item.select_one('h2')
            if not h2:
                return None
            link_elem = h2.find_parent('a', href=True)
            if not link_elem or not link_elem.get('href'):
                return None
            url = self.base_url + link_elem['href']

            # ASIN抽出
            asin = self._extract_asin(url)

            # 価格
            price_elem = item.select_one('.a-price .a-offscreen')
            price = price_elem.get_text(strip=True) if price_elem else '価格情報なし'

            # 在庫・予約状況
            availability = self._check_availability(item)

            # 予約可能または在庫ありの場合のみ返す
            if availability['is_available'] or availability['is_reservation']:
                return {
                'timestamp': datetime.now().isoformat(),
                    'title': title,
                    'price': price,
                    'url': url,
                    'asin': asin,
                    'availability': availability['status'],
                    'is_reservation': availability['is_reservation'],
                    'detected_at': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            return None

    def _check_availability(self, item):
        """在庫・予約状況をチェック"""
        result = {
            'is_available': False,
            'is_reservation': False,
            'status': '不明'
        }

        try:
            # item全体のテキスト
            item_text = item.get_text()

            # 配送情報エリア
            delivery_elem = item.select_one('[class*="deliver"]')
            if delivery_elem:
                delivery_text = delivery_elem.get_text(strip=True)

                if '予約' in delivery_text:
                    result['is_reservation'] = True
                    result['is_available'] = True
                    result['status'] = '予約受付中'
                elif '日にお届け' in delivery_text or '発売予定' in delivery_text:
                    # 配送日があれば購入可能と判定
                    result['is_available'] = True
                    result['status'] = '購入可能'
                elif '在庫あり' in delivery_text or '配送料無料' in delivery_text:
                    result['is_available'] = True
                    result['status'] = '在庫あり'

            # 価格があれば購入可能
            price_elem = item.select_one('.a-price .a-offscreen')
            if price_elem and not result['is_available']:
                result['is_available'] = True
                result['status'] = '購入可能'

        except Exception:
            pass

        return result

    def _extract_asin(self, url):
        """URLからASINを抽出"""
        try:
            if '/dp/' in url:
                asin = url.split('/dp/')[1].split('/')[0].split('?')[0]
                return asin
        except (IndexError, AttributeError):
            pass
        return None

    def _remove_duplicates(self, products):
        """重複商品を除外"""
        seen = set()
        unique = []

        for product in products:
            key = product.get('asin') or product.get('url')
            if key and key not in seen:
                seen.add(key)
                unique.append(product)

        return unique


if __name__ == '__main__':
    scraper = AmazonReservationScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/amazon_reservation_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {output_file}")
        logger.info(f"Found {len(data['reservations'])} reservation products")
