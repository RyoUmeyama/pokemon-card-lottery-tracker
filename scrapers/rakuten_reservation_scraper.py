"""
楽天ブックス予約情報スクレイパー
ポケモンカードの予約可能商品を検出
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time


class RakutenReservationScraper:
    def __init__(self):
        self.base_url = "https://books.rakuten.co.jp"
        self.search_url = "https://books.rakuten.co.jp/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3'
        }

    def scrape(self):
        """ポケモンカードの予約情報をスクレイピング"""
        try:
            products = []

            # 検索キーワード
            keywords = [
                "ポケモンカードゲーム",
                "ポケモンカード 拡張パック",
            ]

            for keyword in keywords:
                print(f"  検索中: {keyword}")
                keyword_products = self._search_products(keyword)
                products.extend(keyword_products)
                time.sleep(2)  # レート制限対策

            # 重複除外
            unique_products = self._remove_duplicates(products)

            result = {
                'source': 'books.rakuten.co.jp',
                'scraped_at': datetime.now().isoformat(),
                'reservations': unique_products
            }

            return result

        except Exception as e:
            print(f"Error scraping Rakuten Books: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _search_products(self, keyword):
        """キーワードで商品を検索"""
        products = []

        try:
            params = {
                'sv': '30',
                'f': '0',
                'g': '001',
                'v': '2',
                'e': '0',
                's': '5',  # 発売日順
                'sitem': keyword,
            }

            response = requests.get(
                self.search_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 商品要素を取得
            items = soup.select('.item-list .item')

            for item in items[:20]:  # 上位20件を確認
                try:
                    product = self._parse_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"  Warning: Search error for '{keyword}': {e}")

        return products

    def _parse_product(self, item):
        """商品情報を抽出"""
        try:
            # タイトル
            title_elem = item.select_one('.item__title a')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # URL
            url = title_elem.get('href')
            if not url:
                return None

            # 価格
            price_elem = item.select_one('.item__price')
            price = price_elem.get_text(strip=True) if price_elem else '価格情報なし'

            # 在庫・予約状況
            availability = self._check_availability(item)

            # 予約可能または在庫ありの場合のみ返す
            if availability['is_available'] or availability['is_reservation']:
                return {
                    'title': title,
                    'price': price,
                    'url': url,
                    'availability': availability['status'],
                    'is_reservation': availability['is_reservation'],
                    'release_date': availability.get('release_date', ''),
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
            # 在庫状況
            stock_elem = item.select_one('.item__stock')
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True)

                if '予約受付中' in stock_text or '予約' in stock_text:
                    result['is_reservation'] = True
                    result['is_available'] = True
                    result['status'] = '予約受付中'
                elif '在庫あり' in stock_text or '24時間以内' in stock_text:
                    result['is_available'] = True
                    result['status'] = '在庫あり'
                elif '通常1～2日' in stock_text:
                    result['is_available'] = True
                    result['status'] = '在庫あり（1-2日）'

            # 発売日情報
            date_elem = item.select_one('.item__date')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                result['release_date'] = date_text
                if '発売予定' in date_text or '発売日' in date_text:
                    result['is_reservation'] = True

        except Exception:
            pass

        return result

    def _remove_duplicates(self, products):
        """重複商品を除外"""
        seen = set()
        unique = []

        for product in products:
            key = product.get('url')
            if key and key not in seen:
                seen.add(key)
                unique.append(product)

        return unique


if __name__ == '__main__':
    scraper = RakutenReservationScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/rakuten_reservation_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['reservations'])} reservation products")
