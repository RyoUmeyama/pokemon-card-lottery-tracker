"""
ビックカメラ抽選販売ページからポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class BiccameraScraper:
    def __init__(self):
        # ビックカメラの抽選販売ページ
        # ビックカメラのポケモンカード検索結果ページ
        self.urls = [
            "https://www.biccamera.com/bc/category/?q=ポケモンカード",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        }
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'ナイトワンダラー',
            'テラスタル', 'クリムゾンヘイズ', 'シャイニートレジャー',
            'レイジングサーフ', 'バトルマスター', 'TCG'
        ]

    def scrape(self):
        """抽選情報をスクレイピング"""
        all_lotteries = []

        for url in self.urls:
            try:
                lotteries = self._scrape_url(url)
                all_lotteries.extend(lotteries)
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        # 重複除去
        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'ビックカメラ (biccamera.com)',
            'source_url': self.urls[0],
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_url(self, url):
        """URLから抽選情報を取得"""
        lotteries = []

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 抽選商品リンクを探す
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                # ポケモンカード関連かチェック
                if self._is_pokemon_card(link_text):
                    lottery_info = self._parse_lottery_link(link, href)
                    if lottery_info:
                        lotteries.append(lottery_info)

            # 商品カード要素を探す
            product_cards = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['item', 'product', 'card', 'goods', 'lottery']
            ))

            for card in product_cards:
                card_text = card.get_text()
                if self._is_pokemon_card(card_text):
                    lottery_info = self._parse_product_card(card)
                    if lottery_info:
                        lotteries.append(lottery_info)

            # テーブルからも情報を探す
            tables = soup.find_all('table')
            for table in tables:
                table_lotteries = self._parse_lottery_table(table)
                lotteries.extend(table_lotteries)

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

            # URLを完全なものに変換
            if href.startswith('/'):
                href = 'https://www.biccamera.com' + href
            elif not href.startswith('http'):
                href = 'https://www.biccamera.com/' + href

            # 親要素から追加情報を取得
            parent = link.find_parent(['div', 'li', 'article', 'tr'])
            period = ''
            status = 'unknown'
            price = ''

            if parent:
                parent_text = parent.get_text()

                # 期間を抽出
                period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', parent_text)
                if period_match:
                    period = period_match.group(1)

                # 価格を抽出
                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                # ステータスを判定
                if '受付中' in parent_text or '申込受付' in parent_text or '実施中' in parent_text:
                    status = 'active'
                elif '終了' in parent_text or '締切' in parent_text:
                    status = 'closed'
                elif '予定' in parent_text or '近日' in parent_text:
                    status = 'upcoming'

            lottery = {
                'store': 'ビックカメラ',
                'product': link_text,
                'lottery_type': '抽選販売',
                'period': period,
                'price': price,
                'detail_url': href,
                'status': status
            }

            return lottery if link_text and len(link_text) > 5 else None

        except Exception as e:
            return None

    def _parse_product_card(self, card):
        """商品カードから抽選情報を抽出"""
        try:
            text = card.get_text(strip=True)

            if not self._is_pokemon_card(text):
                return None

            link = card.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href.startswith('/'):
                href = 'https://www.biccamera.com' + href
            elif href and not href.startswith('http'):
                href = 'https://www.biccamera.com/' + href

            # 商品名を抽出
            title_elem = card.find(['h2', 'h3', 'h4', 'span', 'p', 'strong'])
            product_name = ''
            if title_elem:
                product_name = title_elem.get_text(strip=True)
            else:
                # テキストから商品名を推定
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in lines:
                    if self._is_pokemon_card(line) and len(line) > 10:
                        product_name = line[:100]
                        break

            # 期間を抽出
            period = ''
            period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', text)
            if period_match:
                period = period_match.group(1)

            # 価格を抽出
            price = ''
            price_match = re.search(r'[\d,]+円', text)
            if price_match:
                price = price_match.group()

            if product_name and href:
                lottery = {
                    'store': 'ビックカメラ',
                    'product': product_name,
                    'lottery_type': '抽選販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': 'active' if '受付中' in text else 'unknown'
                }
                return lottery

        except Exception as e:
            pass

        return None

    def _parse_lottery_table(self, table):
        """テーブルから抽選情報を抽出"""
        lotteries = []

        try:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_text = row.get_text()

                if self._is_pokemon_card(row_text):
                    # リンクを取得
                    link = row.find('a', href=True)
                    href = link.get('href', '') if link else ''

                    if href.startswith('/'):
                        href = 'https://www.biccamera.com' + href
                    elif href and not href.startswith('http'):
                        href = 'https://www.biccamera.com/' + href

                    # セルからデータを抽出
                    cell_texts = [c.get_text(strip=True) for c in cells]

                    # 商品名を探す
                    product_name = ''
                    for cell_text in cell_texts:
                        if self._is_pokemon_card(cell_text):
                            product_name = cell_text
                            break

                    if product_name and href:
                        lottery = {
                            'store': 'ビックカメラ',
                            'product': product_name,
                            'lottery_type': '抽選販売',
                            'period': '',
                            'detail_url': href,
                            'status': 'active' if '受付中' in row_text else 'unknown'
                        }
                        lotteries.append(lottery)

        except Exception as e:
            pass

        return lotteries

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
    scraper = BiccameraScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/biccamera_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
