"""
イエローサブマリン（Yellow Submarine）からポケモンカード抽選・予約情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class YellowSubmarineScraper:
    def __init__(self):
        # イエローサブマリンのトップページ（旧URLは404）
        self.urls = [
            "https://www.yellowsubmarine.co.jp/",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
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
            'source': 'イエローサブマリン (yellowsubmarine.co.jp)',
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

            # エンコーディングを検出
            response.encoding = response.apparent_encoding or 'shift_jis'

            soup = BeautifulSoup(response.content, 'html.parser')

            # リンクを探す
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                if self._is_pokemon_card(link_text):
                    lottery = self._parse_lottery_link(link, href)
                    if lottery:
                        lotteries.append(lottery)

            # テーブル内の情報も探す
            tables = soup.find_all('table')
            for table in tables:
                table_lotteries = self._parse_table(table)
                lotteries.extend(table_lotteries)

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error for {url}: {e.response.status_code}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")

        return lotteries

    def _parse_lottery_link(self, link, href):
        """リンクから情報を抽出"""
        try:
            link_text = link.get_text(strip=True)

            if href.startswith('/'):
                href = 'https://www.yellowsubmarine.co.jp' + href
            elif not href.startswith('http'):
                href = 'https://www.yellowsubmarine.co.jp/' + href

            parent = link.find_parent(['div', 'li', 'tr', 'td'])
            price = ''
            period = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', parent_text)
                if period_match:
                    period = period_match.group(1)

                if '予約受付中' in parent_text or '抽選受付中' in parent_text:
                    status = 'active'
                elif '終了' in parent_text or '売切' in parent_text:
                    status = 'closed'

            lottery_type = '抽選販売' if '抽選' in link_text else '予約販売'

            if len(link_text) > 5:
                return {
                    'store': 'イエローサブマリン',
                    'product': link_text,
                    'lottery_type': lottery_type,
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None

    def _parse_table(self, table):
        """テーブルからポケモンカード情報を抽出"""
        lotteries = []

        try:
            rows = table.find_all('tr')

            for row in rows:
                row_text = row.get_text()

                if not self._is_pokemon_card(row_text):
                    continue

                cells = row.find_all(['td', 'th'])
                link = row.find('a', href=True)
                href = link.get('href', '') if link else ''

                if href.startswith('/'):
                    href = 'https://www.yellowsubmarine.co.jp' + href
                elif href and not href.startswith('http'):
                    href = 'https://www.yellowsubmarine.co.jp/' + href

                # 商品名を取得
                product_name = ''
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    if self._is_pokemon_card(cell_text) and len(cell_text) > 10:
                        product_name = cell_text
                        break

                if not product_name and link:
                    product_name = link.get_text(strip=True)

                # 価格を取得
                price = ''
                price_match = re.search(r'[\d,]+円', row_text)
                if price_match:
                    price = price_match.group()

                if product_name and href:
                    lottery = {
                        'store': 'イエローサブマリン',
                        'product': product_name,
                        'lottery_type': '予約販売',
                        'period': '',
                        'price': price,
                        'detail_url': href,
                        'status': 'active' if '受付中' in row_text else 'unknown'
                    }
                    lotteries.append(lottery)

        except Exception:
            pass

        return lotteries

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
    scraper = YellowSubmarineScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
