"""
ノジマ（Nojima）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class NojimaScraper:
    def __init__(self):
        # ノジマオンライン（403エラーが頻発するため簡略化）
        self.urls = []
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
        """抽選情報をスクレイピング"""
        all_lotteries = []

        # ノジマはBot対策が厳しく403エラーになるため、現在は無効化

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'ノジマオンライン (online.nojima.co.jp)',
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_url(self, url):
        """URLから抽選情報を取得"""
        lotteries = []

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

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
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'catalog']
            ))

            for item in product_items:
                item_text = item.get_text()
                if self._is_pokemon_card(item_text):
                    lottery = self._parse_product_item(item)
                    if lottery:
                        lotteries.append(lottery)

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error for {url}: {e.response.status_code}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")

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
                href = 'https://online.nojima.co.jp' + href
            elif not href.startswith('http'):
                href = 'https://online.nojima.co.jp/' + href

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

                if '受付中' in parent_text or '予約受付' in parent_text or 'カートに入れる' in parent_text:
                    status = 'active'
                elif '終了' in parent_text or '売切' in parent_text or '品切れ' in parent_text:
                    status = 'closed'

            lottery = {
                'store': 'ノジマ',
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
                href = 'https://online.nojima.co.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://online.nojima.co.jp/' + href

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
                    'store': 'ノジマ',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': 'active' if '受付中' in text or 'カートに入れる' in text else 'unknown'
                }

        except Exception:
            pass

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
    scraper = NojimaScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
