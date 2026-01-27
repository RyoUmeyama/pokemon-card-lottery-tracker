"""
セブンネットショッピング - Playwright版スクレイパー
Bot対策(Incapsula)を回避するためヘッドレスブラウザを使用
"""
from bs4 import BeautifulSoup
from datetime import datetime
from .playwright_base import PlaywrightBaseScraper, PLAYWRIGHT_AVAILABLE
import re


class SevenNetPlaywrightScraper(PlaywrightBaseScraper):
    def __init__(self):
        super().__init__()
        # ポケモンカード特集ページ
        self.lottery_url = "https://7net.omni7.jp/general/010007/230428pokemoncard"
        # ポケモンカードMEGA特集
        self.mega_url = "https://7net.omni7.jp/general/010007/230616pokemoncard"
        # ポケモンカード検索ページ
        self.search_url = "https://7net.omni7.jp/search/?keyword=%E3%83%9D%E3%82%B1%E3%83%A2%E3%83%B3%E3%82%AB%E3%83%BC%E3%83%89"
        self.base_url = "https://7net.omni7.jp"
        self.source_name = 'セブンネットショッピング (7net.omni7.jp)'

    def scrape(self):
        """Playwrightで抽選情報をスクレイピング"""
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'source': self.source_name,
                'source_url': self.lottery_url,
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': 'playwright not installed'
            }

        lotteries = []

        # ポケモンカード特集ページを試す
        urls_to_try = [
            (self.lottery_url, 'ポケモンカード特集'),
            (self.mega_url, 'MEGAシリーズ特集'),
            (self.search_url, '検索ページ'),
        ]

        for url, name in urls_to_try:
            try:
                content = self.run_async(self.fetch_page_content(
                    url,
                    wait_selector='[class*="product"], [class*="item"], [class*="goods"]',
                    extra_wait=5
                ))

                if content:
                    # Incapsulaブロックチェック
                    if 'Incapsula' in content or 'Request unsuccessful' in content:
                        print(f"セブンネット{name}: Incapsulaでブロック")
                        continue
                    parsed = self._parse_content(content)
                    lotteries.extend(parsed)
                    print(f"セブンネット{name}: {len(parsed)}件")
            except Exception as e:
                print(f"Error scraping sevennet {name}: {e}")

        unique_lotteries = self.remove_duplicates(lotteries)

        return {
            'source': self.source_name,
            'source_url': self.lottery_url,
            'scraped_at': datetime.now().isoformat(),
            'lotteries': unique_lotteries
        }

    def _parse_content(self, content):
        """HTMLコンテンツをパース"""
        lotteries = []
        soup = BeautifulSoup(content, 'html.parser')

        # Incapsulaのブロックページかチェック
        if 'Incapsula' in content or 'Request unsuccessful' in content:
            print("Warning: Blocked by Incapsula WAF")
            return []

        # 商品アイテムを探す
        items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and any(
            kw in str(x).lower() for kw in ['product', 'item', 'goods', 'card', 'lottery']
        ))

        for item in items:
            lottery = self._parse_item(item)
            if lottery:
                lotteries.append(lottery)

        # 抽選関連のリンクを探す
        links = soup.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            href = link.get('href', '')

            # 抽選販売商品を探す
            if ('抽選' in text or '抽選' in href) and self.is_pokemon_card(text):
                lottery = self._parse_link(link, href, text)
                if lottery:
                    lotteries.append(lottery)
            # 商品詳細ページへのリンク
            elif '/detail/' in href and self.is_pokemon_card(text):
                lottery = self._parse_link(link, href, text)
                if lottery:
                    lotteries.append(lottery)

        return lotteries

    def _parse_item(self, item):
        """商品アイテムから情報を抽出"""
        try:
            text = item.get_text(strip=True)

            if not self.is_pokemon_card(text):
                return None

            # 抽選関連のキーワードがあるか確認
            if not any(kw in text for kw in ['抽選', '予約', 'BOX', 'ボックス', 'パック']):
                return None

            link = item.find('a', href=True)
            href = link.get('href', '') if link else ''

            if href and not href.startswith('http'):
                href = self.base_url + href

            # 商品名を取得
            title_elem = item.find(['h2', 'h3', 'h4', 'p', 'span', 'a'], class_=lambda x: x and any(
                kw in str(x).lower() for kw in ['name', 'title', 'ttl', 'product']
            ))
            product_name = title_elem.get_text(strip=True) if title_elem else ''

            if not product_name or len(product_name) < 10:
                # リンクのテキストから取得
                if link:
                    product_name = link.get_text(strip=True)
                if not product_name or len(product_name) < 10:
                    product_name = text[:200]

            price = self.extract_price(text)
            status = self.determine_status(text)
            period = self.extract_period(text)

            # 発売日を探す
            release_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', text)
            if release_match and not period:
                period = release_match.group(1)

            if product_name and href:
                return {
                    'store': 'セブンネットショッピング',
                    'product': product_name,
                    'lottery_type': '抽選販売' if '抽選' in text else '予約販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None

    def _parse_link(self, link, href, text):
        """リンクから情報を抽出"""
        try:
            if not href.startswith('http'):
                href = self.base_url + href

            parent = link.find_parent(['div', 'li', 'article'])
            parent_text = parent.get_text() if parent else text

            # 抽選関連のキーワードがあるか確認
            combined_text = text + parent_text
            if not any(kw in combined_text for kw in ['抽選', '予約', 'BOX', 'ボックス', 'パック']):
                return None

            price = self.extract_price(parent_text)
            status = self.determine_status(parent_text)
            period = self.extract_period(parent_text)

            # 発売日を探す
            release_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', parent_text)
            if release_match and not period:
                period = release_match.group(1)

            if len(text) > 10:
                return {
                    'store': 'セブンネットショッピング',
                    'product': text,
                    'lottery_type': '抽選販売' if '抽選' in combined_text else '予約販売',
                    'period': period,
                    'price': price,
                    'detail_url': href,
                    'status': status
                }

        except Exception:
            pass

        return None


if __name__ == '__main__':
    scraper = SevenNetPlaywrightScraper()
    data = scraper.scrape()

    print(f"Source: {data['source']}")
    print(f"Found {len(data['lotteries'])} entries")
    for lottery in data['lotteries']:
        print(f"  - {lottery['product'][:60]}... ({lottery['status']})")
