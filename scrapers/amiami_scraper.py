"""
あみあみ（AmiAmi）からポケモンカード抽選・予約情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class AmiAmiScraper:
    def __init__(self):
        # あみあみのポケモンカード関連ページ（403エラー対策: 現在無効化）
        self.search_url = None  # Bot対策で403エラーになるためスキップ
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        }
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """抽選・予約情報をスクレイピング"""
        all_lotteries = []

        # あみあみはBot対策が厳しく403エラーになるため、現在は無効化

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'あみあみ (amiami.jp)',
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_search_results(self):
        """検索結果ページからポケモンカード情報を取得"""
        lotteries = []

        try:
            response = requests.get(self.search_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 商品アイテムを探す
            product_items = soup.find_all(['div', 'li'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['product', 'item', 'thumb']
            ))

            for item in product_items:
                lottery = self._parse_product_item(item)
                if lottery:
                    lotteries.append(lottery)

            # 商品リンクから直接取得
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/top/detail/' in href or 'gcode=' in href:
                    lottery = self._parse_product_link(link, href)
                    if lottery:
                        lotteries.append(lottery)

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code}")
        except Exception as e:
            print(f"Error scraping search results: {e}")

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
                href = 'https://www.amiami.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://www.amiami.jp/' + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and 'name' in str(x).lower())
            if not title_elem:
                title_elem = item.find(['h2', 'h3', 'h4'])
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name:
                # テキストから商品名を推定
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

            # 発売日・予約状態を取得
            release_date = ''
            date_match = re.search(r'(\d{4}年\d{1,2}月|\d{4}/\d{1,2})', text)
            if date_match:
                release_date = date_match.group(1)

            # ステータス判定
            status = 'unknown'
            if '予約受付中' in text or '予約可' in text:
                status = 'active'
            elif '予約締切' in text or '予約終了' in text or '売切' in text:
                status = 'closed'
            elif '近日予約開始' in text:
                status = 'upcoming'

            if product_name and href:
                return {
                    'store': 'あみあみ',
                    'product': product_name,
                    'lottery_type': '予約販売',
                    'period': release_date,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None

    def _parse_product_link(self, link, href):
        """商品リンクから情報を抽出"""
        try:
            link_text = link.get_text(strip=True)

            if not self._is_pokemon_card(link_text):
                return None

            if href.startswith('/'):
                href = 'https://www.amiami.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.amiami.jp/' + href

            parent = link.find_parent(['div', 'li', 'article'])
            price = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                if '予約受付中' in parent_text or '予約可' in parent_text:
                    status = 'active'
                elif '売切' in parent_text or '予約終了' in parent_text:
                    status = 'closed'

            if len(link_text) > 10:
                return {
                    'store': 'あみあみ',
                    'product': link_text,
                    'lottery_type': '予約販売',
                    'period': '',
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

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
    scraper = AmiAmiScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
