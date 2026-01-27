"""
ファミリーマート（FamilyMart）からポケモンカード抽選・予約情報をスクレイピング
ファミマの公式サイトとキャンペーンページを監視
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class FamilyMartScraper:
    def __init__(self):
        # ファミリーマートの公式サイト・キャンペーンページ
        self.urls = [
            "https://www.family.co.jp/campaign.html",
        ]
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

        for url in self.urls:
            try:
                lotteries = self._scrape_url(url)
                all_lotteries.extend(lotteries)
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'ファミリーマート (family.co.jp)',
            'source_url': self.urls[0],
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_url(self, url):
        """URLからポケモンカード情報を取得"""
        lotteries = []

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # キャンペーン・商品アイテムを探す
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                if self._is_pokemon_card(link_text):
                    lottery = self._parse_campaign_link(link, href)
                    if lottery:
                        lotteries.append(lottery)

            # 商品リスト要素を探す
            product_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'campaign', 'bnr']
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

    def _parse_campaign_link(self, link, href):
        """キャンペーンリンクから情報を抽出"""
        try:
            link_text = link.get_text(strip=True)

            if href.startswith('/'):
                href = 'https://www.family.co.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.family.co.jp/' + href

            parent = link.find_parent(['div', 'li', 'article'])
            period = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()

                # 期間を抽出
                period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', parent_text)
                if period_match:
                    period = period_match.group(1)

                if '開催中' in parent_text or '実施中' in parent_text:
                    status = 'active'
                elif '終了' in parent_text:
                    status = 'closed'
                elif '近日' in parent_text or '予定' in parent_text:
                    status = 'upcoming'

            # 抽選または予約関連のキーワードがなければスキップ
            combined_text = link_text + (parent.get_text() if parent else '')
            if not any(kw in combined_text for kw in ['抽選', '予約', 'くじ', 'キャンペーン', '販売']):
                return None

            if len(link_text) > 5:
                return {
                    'store': 'ファミリーマート',
                    'product': link_text,
                    'lottery_type': '抽選販売' if '抽選' in combined_text else 'キャンペーン',
                    'period': period,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None

    def _parse_product_item(self, item):
        """商品要素から情報を抽出"""
        try:
            text = item.get_text(strip=True)

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href.startswith('/'):
                href = 'https://www.family.co.jp' + href
            elif href and not href.startswith('http'):
                href = 'https://www.family.co.jp/' + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span'])
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    if self._is_pokemon_card(line) and len(line) > 5:
                        product_name = line[:150]
                        break

            # 期間を抽出
            period = ''
            period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', text)
            if period_match:
                period = period_match.group(1)

            # ステータス判定
            status = 'unknown'
            if '開催中' in text or '実施中' in text or '販売中' in text:
                status = 'active'
            elif '終了' in text:
                status = 'closed'

            # 抽選または予約関連のキーワードがなければスキップ
            if not any(kw in text for kw in ['抽選', '予約', 'くじ', 'キャンペーン', '販売']):
                return None

            if product_name and href:
                return {
                    'store': 'ファミリーマート',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else 'キャンペーン',
                    'period': period,
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
    scraper = FamilyMartScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
