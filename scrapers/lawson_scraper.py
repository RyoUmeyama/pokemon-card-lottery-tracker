"""
ローソン（Lawson）からポケモンカード抽選・予約情報をスクレイピング
ローソンHMVオンラインを監視
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class LawsonScraper:
    def __init__(self):
        # HMV&BOOKS onlineのポケモンカード検索
        self.search_url = "https://www.hmv.co.jp/search/?category=ALL&keyword=ポケモンカード"
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

        try:
            lotteries = self._scrape_search_results()
            all_lotteries.extend(lotteries)
        except Exception as e:
            print(f"Error scraping HMV: {e}")

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'ローソン HMV (hmv.co.jp)',
            'source_url': self.search_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_search_results(self):
        """検索結果からポケモンカード情報を取得"""
        lotteries = []

        try:
            response = requests.get(self.search_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 商品アイテムを探す
            product_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'list', 'search']
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

                if self._is_pokemon_card(link_text) and '/product/' in href:
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
                href = 'https://www.hmv.co.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://www.hmv.co.jp/' + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'ttl']
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

            # 発売日を取得
            release_date = ''
            date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}/\d{1,2}/\d{1,2})', text)
            if date_match:
                release_date = date_match.group(1)

            # ステータス判定
            status = 'unknown'
            if '予約受付中' in text or 'カートに入れる' in text or '在庫あり' in text:
                status = 'active'
            elif '在庫切れ' in text or '品切れ' in text or '販売終了' in text:
                status = 'closed'
            elif '近日発売' in text:
                status = 'upcoming'

            # 予約または抽選関連のみ
            if not any(kw in text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック', '新発売']):
                return None

            if product_name and href:
                return {
                    'store': 'ローソン HMV',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
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

            if href.startswith('/'):
                href = 'https://www.hmv.co.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.hmv.co.jp/' + href

            parent = link.find_parent(['div', 'li', 'article'])
            price = ''
            status = 'unknown'
            release_date = ''

            if parent:
                parent_text = parent.get_text()

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}/\d{1,2}/\d{1,2})', parent_text)
                if date_match:
                    release_date = date_match.group(1)

                if '予約受付中' in parent_text or 'カートに入れる' in parent_text:
                    status = 'active'
                elif '在庫切れ' in parent_text or '品切れ' in parent_text:
                    status = 'closed'

            # 予約または抽選関連のみ
            if not any(kw in link_text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック']):
                return None

            if len(link_text) > 10:
                return {
                    'store': 'ローソン HMV',
                    'product': link_text,
                    'lottery_type': '抽選販売' if '抽選' in link_text else '予約販売',
                    'period': release_date,
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
    scraper = LawsonScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
