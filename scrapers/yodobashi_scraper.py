"""
ヨドバシカメラ抽選販売ページからポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class YodobashiScraper:
    def __init__(self):
        self.url = "https://limited.yodobashi.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        }
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'ナイトワンダラー',
            'テラスタル', 'クリムゾンヘイズ', 'シャイニートレジャー',
            'レイジングサーフ', 'バトルマスター'
        ]

    def scrape(self):
        """抽選情報をスクレイピング"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            lotteries = []

            # 抽選商品のリストを探す
            lottery_items = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['product', 'item', 'lottery', 'campaign']
            ))

            # 全体のHTMLからリンクと商品情報を抽出
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                # ポケモンカード関連かどうかチェック
                if self._is_pokemon_card(link_text) or self._is_pokemon_card(href):
                    lottery_info = self._parse_lottery_link(link, href)
                    if lottery_info:
                        lotteries.append(lottery_info)

            # 商品リストエリアを探して解析
            product_areas = soup.find_all(['section', 'div'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['lottery', 'campaign', 'limited', 'product']
            ))

            for area in product_areas:
                items = self._parse_product_area(area)
                lotteries.extend(items)

            # 重複除去
            unique_lotteries = self._remove_duplicates(lotteries)

            result = {
                'source': 'ヨドバシカメラ (limited.yodobashi.com)',
                'source_url': self.url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': unique_lotteries
            }

            return result

        except requests.exceptions.HTTPError as e:
            print(f"Error scraping limited.yodobashi.com: HTTP {e.response.status_code}")
            return {
                'source': 'ヨドバシカメラ (limited.yodobashi.com)',
                'source_url': self.url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': f'HTTP {e.response.status_code}'
            }
        except Exception as e:
            print(f"Error scraping limited.yodobashi.com: {e}")
            return {
                'source': 'ヨドバシカメラ (limited.yodobashi.com)',
                'source_url': self.url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': str(e)
            }

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
                href = 'https://limited.yodobashi.com' + href
            elif not href.startswith('http'):
                href = 'https://limited.yodobashi.com/' + href

            # 親要素から追加情報を取得
            parent = link.find_parent(['div', 'li', 'article'])
            period = ''
            status = 'unknown'

            if parent:
                period_elem = parent.find(string=re.compile(r'\d{1,2}[/月]\d{1,2}'))
                if period_elem:
                    period = period_elem.strip()

                # ステータスを判定
                parent_text = parent.get_text()
                if '受付中' in parent_text or '申込中' in parent_text:
                    status = 'active'
                elif '終了' in parent_text or '締切' in parent_text:
                    status = 'closed'
                elif '予定' in parent_text or '近日' in parent_text:
                    status = 'upcoming'

            lottery = {
                'store': 'ヨドバシカメラ',
                'product': link_text,
                'lottery_type': '抽選販売',
                'period': period,
                'detail_url': href,
                'status': status
            }

            return lottery if link_text else None

        except Exception as e:
            return None

    def _parse_product_area(self, area):
        """商品エリアから抽選情報を抽出"""
        lotteries = []

        try:
            items = area.find_all(['div', 'li', 'article'], recursive=True)

            for item in items:
                text = item.get_text(strip=True)

                if self._is_pokemon_card(text):
                    link = item.find('a', href=True)
                    href = link.get('href', '') if link else ''

                    if href.startswith('/'):
                        href = 'https://limited.yodobashi.com' + href
                    elif href and not href.startswith('http'):
                        href = 'https://limited.yodobashi.com/' + href

                    # 商品名を抽出
                    title_elem = item.find(['h2', 'h3', 'h4', 'span', 'p'])
                    product_name = title_elem.get_text(strip=True) if title_elem else text[:100]

                    # 期間を抽出
                    period = ''
                    period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', text)
                    if period_match:
                        period = period_match.group(1)

                    if product_name and href:
                        lottery = {
                            'store': 'ヨドバシカメラ',
                            'product': product_name,
                            'lottery_type': '抽選販売',
                            'period': period,
                            'detail_url': href,
                            'status': 'active' if '受付中' in text else 'unknown'
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
    scraper = YodobashiScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/yodobashi_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
