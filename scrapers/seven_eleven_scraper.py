"""
セブンイレブン（7-Eleven）からポケモンカード抽選・予約情報をスクレイピング
セブンネットショッピングを監視
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class SevenElevenScraper:
    def __init__(self, check_availability=True):
        # セブンネットショッピングのポケモンカード関連ページ
        self.search_url = "https://7net.omni7.jp/search/?keyword=ポケモンカード&searchKeywordFlg=1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        }
        self.check_availability = check_availability
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
            print(f"Error scraping 7net: {e}")

        unique_lotteries = self._remove_duplicates(all_lotteries)

        # 在庫チェックが有効な場合、各商品の在庫を確認
        if self.check_availability:
            available_lotteries = []
            for lottery in unique_lotteries:
                if self._check_availability(lottery.get('detail_url', '')):
                    available_lotteries.append(lottery)
            unique_lotteries = available_lotteries

        result = {
            'source': 'セブンネットショッピング (7net.omni7.jp)',
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
                kw in str(x).lower() for kw in ['item', 'product', 'goods', 'list']
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

                if self._is_pokemon_card(link_text) and '/detail/' in href:
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

            # URLの正規化
            href = self._normalize_url(href)

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
            elif '売り切れ' in text or '品切れ' in text or '販売終了' in text:
                status = 'closed'
            elif '近日発売' in text or '予約開始前' in text:
                status = 'upcoming'

            # 予約または抽選関連のみ
            if not any(kw in text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック', '新発売']):
                return None

            if product_name and href:
                return {
                    'store': 'セブンネットショッピング',
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

            # URLの正規化
            href = self._normalize_url(href)

            parent = link.find_parent(['div', 'li', 'article'])
            price = ''
            status = 'unknown'

            if parent:
                parent_text = parent.get_text()

                price_match = re.search(r'[\d,]+円', parent_text)
                if price_match:
                    price = price_match.group()

                if '予約受付中' in parent_text or 'カートに入れる' in parent_text:
                    status = 'active'
                elif '売り切れ' in parent_text or '品切れ' in parent_text:
                    status = 'closed'

            # 予約または抽選関連のみ
            if not any(kw in link_text for kw in ['予約', '抽選', 'BOX', 'ボックス', 'パック']):
                return None

            if len(link_text) > 10:
                return {
                    'store': 'セブンネットショッピング',
                    'product': link_text,
                    'lottery_type': '抽選販売' if '抽選' in link_text else '予約販売',
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

    def _normalize_url(self, href):
        """URLを正規化"""
        if not href:
            return ''

        # 既に正しいURLの場合はそのまま返す
        if href.startswith('https://7net.omni7.jp/'):
            return href

        # //7net.omni7.jp/... 形式
        if href.startswith('//7net.omni7.jp/'):
            return 'https:' + href

        # /7net.omni7.jp/... 形式（誤った形式）
        if href.startswith('/7net.omni7.jp/'):
            return 'https:/' + href

        # // で始まる場合
        if href.startswith('//'):
            return 'https:' + href

        # /detail/... などの相対パス
        if href.startswith('/'):
            return 'https://7net.omni7.jp' + href

        # detail/... など
        if href.startswith('detail/'):
            return 'https://7net.omni7.jp/' + href

        # http(s)で始まる場合はそのまま
        if href.startswith('http'):
            return href

        return 'https://7net.omni7.jp/' + href

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

    def _check_availability(self, url):
        """商品ページにアクセスして在庫があるかチェック"""
        if not url:
            return False

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            html = response.text.lower()

            # ページが見つからない・アクセスできないパターン
            not_found_keywords = [
                'ご指定のページにアクセスできませんでした',
                'ページが見つかりません',
                'お探しのページは見つかりませんでした',
                'ページにアクセスできません',
                '404'
            ]

            for keyword in not_found_keywords:
                if keyword in html:
                    print(f"  Info: {url} - ページなし: {keyword}")
                    return False

            # 在庫切れを示すキーワード
            out_of_stock_keywords = [
                '在庫切れ', '売り切れ', '販売終了', '完売', '品切れ',
                'sold out', 'out of stock', '取り扱いを終了',
                '現在お取り扱いできません', '販売を終了しました',
                '予約受付は終了', '受付終了', '抽選受付は終了',
                '予約終了', '終了しました', '受付期間外',
                'カートに入れることができません', '購入できません',
                'お取り扱いしておりません', '販売しておりません',
                'ただいまお取り扱いできません', '現在販売しておりません'
            ]

            for keyword in out_of_stock_keywords:
                if keyword in html:
                    print(f"  Info: {url} - 在庫切れ: {keyword}")
                    return False

            # 購入可能を示すキーワードがあるかチェック
            available_keywords = [
                'カートに入れる', 'カートに追加', '購入する', '予約する',
                '抽選に応募', '応募する', '申し込む', '予約受付中',
                '抽選受付中', '販売中', 'お気に入りに追加'
            ]

            has_available_keyword = any(keyword in html for keyword in available_keywords)

            if not has_available_keyword:
                print(f"  Info: {url} - 購入可能キーワードなし")
                return False

            return True

        except requests.exceptions.HTTPError as e:
            print(f"  Info: {url} - HTTPエラー({e.response.status_code})")
            return False
        except requests.exceptions.Timeout:
            print(f"  Warning: {url} - タイムアウト")
            return False
        except Exception as e:
            print(f"  Warning: {url} - エラー: {e}")
            return False


if __name__ == '__main__':
    scraper = SevenElevenScraper(check_availability=True)
    data = scraper.scrape()

    if data:
        print(f"Found {len(data['lotteries'])} entries")
        for lottery in data['lotteries']:
            print(f"  - {lottery['product']}")
