"""
楽天ブックス（books.rakuten.co.jp）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class RakutenBooksScraper:
    def __init__(self):
        self.url = "https://books.rakuten.co.jp/event/game/card/entry/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def scrape(self):
        """抽選情報をスクレイピング"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 抽選情報を抽出
            lotteries = []

            # ページ全体から商品情報を探す
            products = soup.find_all(['h2', 'h3', 'h4', 'div'], class_=re.compile(r'product|item|entry|lottery', re.I))

            # 抽選受付中かどうかを確認
            page_text = soup.get_text()

            # 「抽選受付は終了しました」などのメッセージをチェック
            if '抽選受付は終了' in page_text or '受付終了' in page_text or '受付は終了' in page_text:
                # 抽選終了の場合は空リストを返す
                return {
                    'source': 'books.rakuten.co.jp',
                    'scraped_at': datetime.now().isoformat(),
                    'lotteries': []
                }

            # テキストから期間情報を抽出
            period_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日.*?(\d{1,2}):(\d{2}).*?(\d{4})年(\d{1,2})月(\d{1,2})日.*?(\d{1,2}):(\d{2})', page_text)

            entry_period = ""
            if period_match:
                start_date = f"{period_match.group(1)}-{period_match.group(2):0>2}-{period_match.group(3):0>2} {period_match.group(4):0>2}:{period_match.group(5)}"
                end_date = f"{period_match.group(6)}-{period_match.group(7):0>2}-{period_match.group(8):0>2} {period_match.group(9):0>2}:{period_match.group(10)}"
                entry_period = f"{start_date} ～ {end_date}"

            # 除外キーワード
            exclude_keywords = [
                '抽選受付ページ', '抽選エントリー', 'こちら', '楽天ブックス:',
                '<b>', '</b>', '<br', '■ポケモン'
            ]

            # 商品名を抽出（ポケモンカードゲームを含むもの）
            for element in soup.find_all(string=re.compile(r'ポケモンカードゲーム|ポケカ')):
                product_name = element.strip()

                # 長すぎるテキストや不要なテキストを除外
                if len(product_name) > 200 or len(product_name) < 10:
                    continue

                # 除外キーワードチェック
                if any(keyword in product_name for keyword in exclude_keywords):
                    continue

                # 【】で囲まれた商品名のみを対象
                if '【' in product_name and '】' in product_name:
                    lottery = {
                        'store': '楽天ブックス',
                        'product': product_name,
                        'lottery_type': '抽選販売',
                        'start_date': '',
                        'end_date': '',
                        'announcement_date': '',
                        'conditions': '楽天会員登録必須',
                        'detail_url': self.url,
                        'status': 'active' if entry_period else 'unknown',
                        'entry_period': entry_period
                    }

                    # 重複チェック
                    if not any(l['product'] == product_name for l in lotteries):
                        lotteries.append(lottery)

            # 抽選情報が見つからない場合は空のリストを返す
            result = {
                'source': 'books.rakuten.co.jp',
                'scraped_at': datetime.now().isoformat(),
                'lotteries': lotteries
            }

            return result

        except Exception as e:
            print(f"Error scraping books.rakuten.co.jp: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == '__main__':
    scraper = RakutenBooksScraper()
    data = scraper.scrape()

    if data:
        # 結果をJSONファイルに保存
        output_file = '../data/rakuten_books_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['lotteries'])} lottery entries")
