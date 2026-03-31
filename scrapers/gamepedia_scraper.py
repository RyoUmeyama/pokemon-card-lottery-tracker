"""
GamePedia ポケモンカード抽選情報スクレイパー
https://premium.gamepedia.jp/pokeca/archives/124
"""
import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class GamepediaScraper:
    def __init__(self):
        self.url = "https://premium.gamepedia.jp/pokeca/archives/124"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def scrape(self):
        """ゲームペディアから抽選情報を取得"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            lotteries = []
            upcoming_products = []

            # 「受付中のショップ」セクションを処理
            current_section = soup.find('h3', string='受付中のショップ')
            if current_section:
                lotteries = self._extract_ongoing_lotteries(soup, current_section)

            # 「今後の発売日情報」セクションを処理
            upcoming = self._extract_upcoming_products(soup)
            if upcoming:
                upcoming_products.extend(upcoming)

            result = {
                'source': 'gamepedia.jp',
                'scraped_at': datetime.now().isoformat(),
                'lotteries': lotteries,
                'upcoming_products': upcoming_products
            }

            logger.info(f"GamePedia: {len(lotteries)}件の抽選、{len(upcoming_products)}件の予定を取得")
            return result

        except Exception as e:
            logger.error(f"Error scraping GamePedia: {e}")
            import traceback
            traceback.print_exc()
            return {
                'source': 'gamepedia.jp',
                'lotteries': [],
                'upcoming_products': []
            }

    def _extract_ongoing_lotteries(self, soup, start_section):
        """受付中のショップセクションから抽選情報を抽出"""
        lotteries = []
        today = date.today()

        # h3タグを順次処理（最初の「受付中のショップ」以降、次のセクション見出しまで）
        h3_tags = soup.find_all('h3')
        start_idx = h3_tags.index(start_section)

        for i in range(start_idx + 1, len(h3_tags)):
            h3 = h3_tags[i]
            store_name = h3.get_text(strip=True)

            # 次のセクション見出しで終了（例：年号h4やその他の大見出し）
            if store_name == '受付中のショップ' or i > start_idx + 50:
                # 十分に多くの店舗を処理したら終了
                if len(lotteries) > 0:
                    break

            # この店舗に紐づくテーブルをすべて抽出
            current = h3.find_next()
            while current:
                # 次のh3に達したら終了
                if current.name == 'h3':
                    break

                # テーブルを処理
                if current.name == 'table':
                    lottery_info = self._parse_table(current, store_name, today)
                    if lottery_info:
                        lotteries.append(lottery_info)

                current = current.find_next()

        return lotteries

    def _parse_table(self, table, store_name, today):
        """テーブルから抽選情報を抽出"""
        info_dict = {}

        # th/tdペアを抽出
        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                th = cells[0].get_text(strip=True)
                td = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                if th and td:
                    info_dict[th] = td

        # 必須フィールドが揃っているか確認
        product = info_dict.get('対象商品', '')
        if not product:
            return None

        # 販売種別がない場合はスキップ
        sales_type = info_dict.get('販売種別', '')
        if not sales_type:
            return None

        # 期限切れチェック（終了日を確認）
        end_date_str = info_dict.get('抽選終了日時', '') or info_dict.get('抽選終了日', '')
        if end_date_str:
            parsed_end_date = self._parse_date(end_date_str)
            if parsed_end_date and parsed_end_date < today:
                return None  # 期限切れは除外

        # start_dateを整形
        start_date_str = info_dict.get('抽選開始日時', '') or info_dict.get('抽選開始日', '')

        # detail_url を抽出（テーブル内のaタグを探す）
        detail_url = ''
        link = table.find('a', href=True)
        if link:
            detail_url = link.get('href', '')

        # URLがない場合はページURLをデフォルト
        if not detail_url:
            detail_url = 'https://premium.gamepedia.jp/pokeca/archives/124'

        lottery = {
            'store': store_name,
            'product': product,
            'lottery_type': sales_type,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'detail_url': detail_url,
            'status': 'active'
        }

        return lottery

    def _extract_upcoming_products(self, soup):
        """今後の発売日情報セクションから予定情報を抽出"""
        upcoming = []

        # 「今後の発売日情報」を含むテキストを探す
        for text_node in soup.find_all(string=True):
            if '今後の発売日情報' in text_node:
                # このテキストノードの親要素から次のセクションまでを処理
                parent = text_node.parent
                current = parent.find_next()

                while current:
                    # h3に達したら終了
                    if current.name == 'h3':
                        break

                    # テーブルを処理
                    if current.name == 'table':
                        rows = current.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['th', 'td'])
                            if len(cells) >= 2:
                                # cells[0] = 日付, cells[1] = 商品名
                                # （テーブルヘッダーが示す通り）
                                release_date = cells[0].get_text(strip=True)
                                product_name = cells[1].get_text(strip=True)

                                if product_name and release_date:
                                    # 日付フォーマットの確認（ヘッダー行をスキップ）
                                    if '発売日' not in release_date:
                                        item = {
                                            'product_name': product_name,
                                            'release_date': release_date,
                                            'lottery_schedule': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                                            'store': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                                            'detail_url': 'https://premium.gamepedia.jp/pokeca/archives/124'
                                        }
                                        upcoming.append(item)

                    current = current.find_next()
                break

        return upcoming

    def _parse_date(self, date_str):
        """
        日付文字列をパースして date オブジェクトを返す
        対応形式: '3/13(金)', '3月13日', '2026年3月13日'
        """
        try:
            # 形式1: '3/13(金)' or '3/13'
            match = re.search(r'(\d{1,2})/(\d{1,2})', date_str)
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                # 年が指定されていなければ2026と仮定
                year = 2026
                try:
                    return date(year, month, day)
                except ValueError:
                    return None

            # 形式2: '3月13日' or '2026年3月13日'
            match = re.search(r'(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日', date_str)
            if match:
                year = int(match.group(1)) if match.group(1) else 2026
                month = int(match.group(2))
                day = int(match.group(3))
                try:
                    return date(year, month, day)
                except ValueError:
                    return None

        except Exception:
            pass

        return None
