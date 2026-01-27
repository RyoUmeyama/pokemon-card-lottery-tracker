"""
エディオン（EDION）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class EdionScraper:
    def __init__(self):
        # エディオンの抽選販売ページ
        self.urls = [
            "https://www.edion.com/detail.html?p_cd=00077889999",  # ポケモンカード特集
            "https://www.edion.com/event/",
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
        """抽選情報をスクレイピング"""
        all_lotteries = []

        for url in self.urls:
            try:
                lotteries = self._scrape_url(url)
                all_lotteries.extend(lotteries)
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        unique_lotteries = self._remove_duplicates(all_lotteries)

        result = {
            'source': 'エディオン (edion.com)',
            'source_url': self.urls[0],
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
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'lottery', 'event']
            ))

            for item in product_items:
                item_text = item.get_text()
                if self._is_pokemon_card(item_text):
                    lottery = self._parse_product_item(item)
                    if lottery:
                        lotteries.append(lottery)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"Access forbidden for {url} (bot protection)")
            else:
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
                href = 'https://www.edion.com' + href
            elif not href.startswith('http'):
                href = 'https://www.edion.com/' + href

            parent = link.find_parent(['div', 'li', 'article', 'tr'])
            period = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()
                period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', parent_text)
                if period_match:
                    period = period_match.group(1)

                if '受付中' in parent_text or '申込' in parent_text or '抽選' in parent_text:
                    status = 'active'
                elif '終了' in parent_text:
                    status = 'closed'

            lottery = {
                'store': 'エディオン',
                'product': link_text,
                'lottery_type': '抽選販売',
                'period': period,
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

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href.startswith('/'):
                href = 'https://www.edion.com' + href
            elif href and not href.startswith('http'):
                href = 'https://www.edion.com/' + href

            title_elem = item.find(['h2', 'h3', 'h4', 'span', 'p', 'strong'])
            product_name = title_elem.get_text(strip=True) if title_elem else text[:100]

            period = ''
            period_match = re.search(r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)', text)
            if period_match:
                period = period_match.group(1)

            if product_name and href:
                return {
                    'store': 'エディオン',
                    'product': product_name,
                    'lottery_type': '抽選販売',
                    'period': period,
                    'detail_url': href,
                    'status': 'active' if '受付中' in text or '抽選' in text else 'unknown'
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
    scraper = EdionScraper()
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
