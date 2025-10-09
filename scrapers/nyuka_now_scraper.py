"""
入荷Now（nyuka-now.com）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class NyukaNowScraper:
    def __init__(self, check_availability=False):
        self.url = "https://nyuka-now.com/archives/2459"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.check_availability = check_availability  # 在庫チェックを行うかどうか

    def scrape(self):
        """抽選情報をスクレイピング"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 抽選情報を抽出
            lotteries = []

            # 記事の更新日時を取得
            update_date = self._extract_update_date(soup)

            # 記事本文を取得
            article = soup.find('article')
            if not article:
                article = soup.find('main') or soup.find(class_='content')

            if article:
                # 見出しとテーブルのペアを探す
                h2_sections = article.find_all('h2')

                for h2 in h2_sections:
                    section_title = h2.get_text(strip=True)

                    # 抽選・予約受付中のセクションのみを対象
                    if '抽選' in section_title or '予約' in section_title:
                        # このh2の後ろにあるテーブルを全て取得
                        next_elem = h2.find_next_sibling()
                        while next_elem and next_elem.name != 'h2':
                            if next_elem.name == 'table':
                                lottery_info = self._parse_lottery_table(next_elem)
                                if lottery_info:
                                    lotteries.extend(lottery_info)
                            elif next_elem.name in ['h3', 'h4']:
                                # h3の後ろのテーブルも確認
                                h3_table = next_elem.find_next_sibling('table')
                                if h3_table:
                                    lottery_info = self._parse_lottery_table(h3_table)
                                    if lottery_info:
                                        lotteries.extend(lottery_info)
                            next_elem = next_elem.find_next_sibling()

            result = {
                'source': 'nyuka-now.com',
                'scraped_at': datetime.now().isoformat(),
                'update_date': update_date,
                'lotteries': lotteries
            }

            return result

        except Exception as e:
            print(f"Error scraping nyuka-now.com: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_update_date(self, soup):
        """更新日時を抽出"""
        # タイトルから日付を抽出（例：【2025年10月7日更新】）
        title = soup.find('h1')
        if title:
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title.text)
            if date_match:
                return f"{date_match.group(1)}-{date_match.group(2):0>2}-{date_match.group(3):0>2}"
        return None

    def _parse_lottery_table(self, table):
        """テーブルから抽選情報を抽出"""
        lotteries = []
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])

            # 最低限のセル数をチェック
            if len(cells) >= 2:
                cell_texts = [c.get_text(strip=True) for c in cells]

                # データ行かヘッダー行かを判定（ヘッダーは除外）
                if any(text for text in cell_texts if text and not any(header in text for header in ['対象商品', '抽選形式', '開始日', '終了日'])):
                    lottery = {
                        'store': cell_texts[0] if len(cell_texts) > 0 else '',
                        'product': cell_texts[1] if len(cell_texts) > 1 else '',
                        'lottery_type': cell_texts[2] if len(cell_texts) > 2 else '',
                        'start_date': cell_texts[3] if len(cell_texts) > 3 else '',
                        'end_date': cell_texts[4] if len(cell_texts) > 4 else '',
                        'announcement_date': cell_texts[5] if len(cell_texts) > 5 else '',
                        'conditions': cell_texts[6] if len(cell_texts) > 6 else '',
                        'detail_url': '',
                        'status': self._determine_status(' '.join(cell_texts))
                    }

                    # リンクを抽出
                    link = row.find('a')
                    if link and link.get('href'):
                        nyuka_now_url = link['href']
                        # 入荷Nowの記事ページから実際の販売・抽選ページのURLを取得
                        direct_url = self._extract_direct_url(nyuka_now_url)
                        lottery['detail_url'] = direct_url if direct_url else nyuka_now_url

                    # 直接URLが取得できなかった（在庫切れなど）場合は除外
                    if not lottery['detail_url'] or lottery['detail_url'] == '':
                        continue

                    # Amazon、Yahoo!ショッピング、駿河屋を除外
                    store_text = lottery['store'].lower()
                    url_text = lottery['detail_url'].lower()
                    if 'amazon' in store_text or 'amazon' in url_text:
                        continue
                    if 'yahoo' in store_text or 'yahoo' in url_text or 'shopping.yahoo' in url_text:
                        continue
                    if '駿河屋' in lottery['store'] or 'suruga' in url_text:
                        continue

                    # 中身がない情報を除外（ヘッダー行など）
                    if lottery['store'] in ['販売開始日時', '店舗/サイト名', '']:
                        continue
                    if lottery['product'] in ['詳細', '商品名', '']:
                        continue

                    # 空のデータは除外
                    if lottery['store'] and lottery['product']:
                        lotteries.append(lottery)

        return lotteries

    def _determine_status(self, period_text):
        """抽選期間から状態を判定"""
        if '受付中' in period_text or '実施中' in period_text:
            return 'active'
        elif '終了' in period_text:
            return 'closed'
        else:
            return 'unknown'

    def _extract_direct_url(self, nyuka_now_url):
        """入荷Nowの記事ページから実際の販売・抽選ページのURLを抽出"""
        if not nyuka_now_url or 'nyuka-now.com' not in nyuka_now_url:
            return None

        try:
            response = requests.get(nyuka_now_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            article = soup.find('article') or soup.find('main')

            if article:
                # 外部リンクを探す（入荷Nowの内部リンク以外）
                links = article.find_all('a', href=True)

                for link in links:
                    href = link.get('href', '')

                    # 外部の販売・抽選ページリンクを優先
                    # 除外: 内部リンク、アプリストア、SNSなど
                    if (href.startswith('http') and
                        'nyuka-now.com' not in href and
                        'apple.co' not in href and
                        'play.google.com' not in href and
                        'twitter.com' not in href and
                        'facebook.com' not in href and
                        'instagram.com' not in href):

                        # 在庫チェックが有効な場合のみチェック
                        if self.check_availability:
                            if self._check_availability(href):
                                return href
                            else:
                                return None  # 在庫切れの場合はNoneを返す
                        else:
                            # 在庫チェックしない場合はそのまま返す
                            return href

            return None

        except Exception as e:
            # エラーが発生してもスクレイピング全体は継続
            print(f"  Warning: Could not extract direct URL from {nyuka_now_url}: {e}")
            return None

    def _check_availability(self, url):
        """販売ページが在庫ありかチェック"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            html = response.text.lower()

            # 在庫切れを示すキーワード
            out_of_stock_keywords = [
                '在庫切れ', '売り切れ', '販売終了', '完売', '品切れ',
                'sold out', 'out of stock', '取り扱いを終了',
                '現在お取り扱いできません', '申し訳ございません',
                '販売を終了しました', 'この商品は現在お取り扱いできません'
            ]

            # 在庫切れキーワードが含まれているかチェック
            for keyword in out_of_stock_keywords:
                if keyword in html:
                    print(f"  Info: {url} - 在庫切れ検出: {keyword}")
                    return False

            return True

        except Exception as e:
            print(f"  Warning: Could not check availability for {url}: {e}")
            # エラーの場合は在庫ありとして扱う（過剰にフィルタしないため）
            return True


if __name__ == '__main__':
    scraper = NyukaNowScraper()
    data = scraper.scrape()

    if data:
        # 結果をJSONファイルに保存
        output_file = '../data/nyuka_now_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['lotteries'])} lottery entries")
