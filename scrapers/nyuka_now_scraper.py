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
                        lottery['detail_url'] = link['href']

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
