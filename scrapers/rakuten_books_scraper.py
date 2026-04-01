"""
楽天ブックス（books.rakuten.co.jp）からポケモンカード抽選情報をスクレイピング
"""
from datetime import datetime
import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RakutenBooksScraper:
    def __init__(self):
        self.url = "https://books.rakuten.co.jp/event/game/card/entry/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def scrape(self):
        """抽選情報をスクレイピング"""
        try:
            time.sleep(1)
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # ページテキストを抽出
            page_text = soup.get_text()

            # 抽選情報を抽出
            lotteries = []
            seen_products = set()  # 重複排除用

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

                # 【】条件を削除し、商品名を直接対象とする
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

                # 重複チェック（setで高速化）
                if product_name not in seen_products:
                    seen_products.add(product_name)
                    lotteries.append(lottery)

            # 抽選情報が見つからない場合は空のリストを返す
            result = {
                'source': 'books.rakuten.co.jp',
                'scraped_at': datetime.now().isoformat(),
                'lotteries': lotteries
            }

            return result

        except Exception as e:
            logger.error(f"Error scraping books.rakuten.co.jp: {e}", exc_info=True)
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
        logger.info(f"Saved to {output_file}")
        logger.info(f"Found {len(data['lotteries'])} lottery entries")
