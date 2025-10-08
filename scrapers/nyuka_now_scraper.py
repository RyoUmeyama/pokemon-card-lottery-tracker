"""
入荷Now（nyuka-now.com）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re


class NyukaNowScraper:
    def __init__(self):
        self.url = "https://nyuka-now.com/archives/2459"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def scrape(self):
        """抽選情報をスクレイピング"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # 抽選情報を抽出
            lotteries = []

            # 記事の更新日時を取得
            update_date = self._extract_update_date(soup)

            # テーブルやリストから抽選情報を抽出
            # （実際のHTML構造に応じて調整が必要）
            tables = soup.find_all('table')
            for table in tables:
                lottery_info = self._parse_lottery_table(table)
                if lottery_info:
                    lotteries.extend(lottery_info)

            result = {
                'source': 'nyuka-now.com',
                'scraped_at': datetime.now().isoformat(),
                'update_date': update_date,
                'lotteries': lotteries
            }

            return result

        except Exception as e:
            print(f"Error scraping nyuka-now.com: {e}")
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
            if len(cells) >= 3:
                lottery = {
                    'store': cells[0].get_text(strip=True),
                    'product': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                    'period': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                    'status': self._determine_status(cells[2].get_text(strip=True) if len(cells) > 2 else '')
                }
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
