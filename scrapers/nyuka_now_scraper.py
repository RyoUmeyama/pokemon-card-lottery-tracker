"""
入荷Now（nyuka-now.com）からポケモンカード抽選情報をスクレイピング
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import time
import logging

logger = logging.getLogger(__name__)


class NyukaNowScraper:
    def __init__(self, check_availability=False):
        self.url = "https://nyuka-now.com/archives/2459"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.check_availability = check_availability  # 在庫チェックを行うかどうか
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]
        # 除外店舗リスト
        self.excluded_stores = [
            'amazon', 'Amazon', 'AMAZON',
            'yahoo', 'Yahoo', 'YAHOO',
            'ノジマオンライン', 'ノジマ',
            'アイリスプラザ', 'アイリス',
            'ヤマシロヤ', 'ジョーシン',
            'ドラゴンスター', '竜のしっぽ', '古本市場',
            'ホビーステーション', 'トレカプラザ', 'TCGショップ193',
            'ポケモンカードラウンジ', 'POKEMON CARD LOUNGE'
        ]
        # 終了ラベルキーワード（より明示的なフレーズに限定）
        self.closed_keywords = [
            '受付終了', '販売終了', '抽選終了', '受付は終了',
            'closed', 'Closed', 'CLOSED'
        ]

    def scrape(self):
        """抽選情報をスクレイピング（リトライ機構付き）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(self.url, headers=self.headers, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # 抽選情報を抽出
                lotteries = []

                # 記事の更新日時を取得
                update_date = self._extract_update_date(soup)

                # 記事本文を取得（複数のセレクタを試行）
                article = soup.find('article')
                if not article:
                    article = soup.find('main')
                if not article:
                    article = soup.find(class_='content')
                if not article:
                    article = soup.find(class_='post-content')
                if not article:
                    article = soup.find(class_='entry-content')
                if not article:
                    article = soup.find(id='post-content')
                if not article:
                    # 全体を対象にする
                    article = soup

                if article:
                    # 全テーブルを対象に解析（シンプル化）
                    all_tables = article.find_all('table')
                    for table in all_tables:
                        lottery_info = self._parse_lottery_table(table)
                        if lottery_info:
                            lotteries.extend(lottery_info)

                    # テーブルがない場合はリスト形式(ul/li)も探す
                    if not all_tables:
                        ul_elements = article.find_all('ul')
                        for ul in ul_elements:
                            lottery_info = self._parse_lottery_list(ul)
                            if lottery_info:
                                lotteries.extend(lottery_info)

                # 重複を除外（商品名とURLの組み合わせで判定）
                unique_lotteries = []
                seen = set()
                for lottery in lotteries:
                    # 最小限の品質フィルター
                    # (a) product が空の場合は除外
                    if not lottery.get('product', ''):
                        continue

                    # (b) store が空の場合は除外
                    if not lottery.get('store', ''):
                        continue

                    key = (lottery.get('product', ''), lottery.get('detail_url', ''))
                    if key not in seen:
                        seen.add(key)
                        # 各lottery itemに source フィールドを追加
                        lottery['source'] = 'nyuka-now.com'
                        unique_lotteries.append(lottery)

                result = {
                    'source': 'nyuka-now.com',
                    'scraped_at': datetime.now().isoformat(),
                    'update_date': update_date,
                    'lotteries': unique_lotteries
                }

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) ** 2  # exponential backoff: 1, 4, 9秒
                    logging.warning(f"Retry {attempt + 1}/{max_retries} for nyuka-now.com, waiting {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Error scraping nyuka-now.com after {max_retries} retries: {e}")
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

    def _normalize_store_name(self, store_name):
        """store名を正規化（空白・改行除去）"""
        if not store_name:
            return ''
        # 複数の空白・改行を単一空白に統一
        normalized = re.sub(r'[\s\n\r]+', ' ', store_name)
        # 両端の空白を除去
        return normalized.strip()

    def _parse_th_td_pairs(self, rows):
        """th/tdペアから抽選情報を辞書化して抽出
        戻り値: {ラベル: 値} の辞書"""
        info_dict = {}

        for row in rows:
            cells = row.find_all(['th', 'td'])
            # th + tdの構造を探す
            if len(cells) >= 2:
                for i in range(len(cells) - 1):
                    if cells[i].name == 'th' and cells[i + 1].name == 'td':
                        label = cells[i].get_text(strip=True)
                        value = cells[i + 1].get_text(strip=True)
                        if label and value:
                            info_dict[label] = value

        return info_dict

    def _is_date_expired(self, date_str, today):
        """日付文字列が今日より前かチェック
        Args:
            date_str: 日付文字列（例：「2026年3月31日」「3月31日」「3/31」等）
            today: datetime.date オブジェクト
        Returns:
            True: 期限切れ / False: 有効
        """
        try:
            # 「2026年3月31日」「3月31日」「3/31」等の形式に対応
            # 月日を抽出（簡易版）
            month_match = re.search(r'(\d{1,2})月', date_str)
            day_match = re.search(r'(\d{1,2})日', date_str)

            if month_match and day_match:
                month = int(month_match.group(1))
                day = int(day_match.group(1))

                # 年を抽出（なければ2026と仮定）
                year_match = re.search(r'(\d{4})年', date_str)
                year = int(year_match.group(1)) if year_match else 2026

                end_date = datetime.date(year, month, day)
                return end_date < today
        except Exception:
            pass

        return False  # 解析失敗時はスキップしない

    def _parse_accordion_table(self, table, product_name):
        """accordion構造（h3 + table）から抽選情報を抽出"""
        lotteries = []
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # 最初のセル（th）が店舗名、2番目のセル（td）が商品リンク
                store_name = cells[0].get_text(strip=True) if len(cells) > 0 else ''
                product_link = cells[1].find('a') if len(cells) > 1 else None

                if store_name and product_link:
                    link_text = product_link.get_text(strip=True)
                    link_href = product_link.get('href', '')

                    lottery = {
                        'store': store_name,
                        'product': product_name,
                        'lottery_type': '',
                        'start_date': '',
                        'end_date': '',
                        'announcement_date': '',
                        'conditions': '',
                        'detail_url': link_href,
                        'status': 'active'
                    }

                    # 除外店舗チェック
                    if 'amazon' not in store_name.lower() and 'yahoo' not in store_name.lower() and \
                       '駿河屋' not in store_name and 'エディオン' not in store_name:
                        lotteries.append(lottery)

        return lotteries

    def _parse_lottery_table(self, table):
        """テーブルから抽選情報を抽出（Type1/Type2判定付き）"""
        lotteries = []

        # テーブルの前にあるh3タグから店舗名を取得
        store_name = ''
        h3 = table.find_previous('h3')
        if h3:
            h3_text = h3.get_text(strip=True)
            # Type1判定: h3に「在庫あり」を含む → 在庫情報テーブル → スキップ
            if '在庫あり' in h3_text:
                return lotteries  # 空リストを返す（このテーブルはスキップ）
            store_name = self._normalize_store_name(h3_text)

        # 除外店舗チェック
        for excluded_store in self.excluded_stores:
            if excluded_store in store_name:
                logger.info(f"除外店舗: {store_name} (除外リスト: {excluded_store})")
                return lotteries

        rows = table.find_all('tr')

        # テーブル全体の終了ラベル検出（テーブル内のtdに終了キーワード）
        table_text = table.get_text()
        for closed_kw in self.closed_keywords:
            if closed_kw in table_text:
                logger.info(f"終了ラベル検出: {store_name} (キーワード: {closed_kw})")
                return lotteries

        # Type2: th/tdペア辞書を作成して、対象商品・期間を抽出
        info_dict = self._parse_th_td_pairs(rows)

        # 「対象商品」を取得
        product = info_dict.get('対象商品', '')
        if not product:
            product = info_dict.get('商品名', '')
        if not product:
            product = info_dict.get('ポケモンカード商品', '')

        # 複数商品が連結されている場合は、最初の商品のみを抽出
        if product:
            # 改行で分割して最初のものを取得
            product_lines = product.split('\n')
            product = product_lines[0].strip() if product_lines else product

            # それでも複数商品が含まれている場合（例：「商品Aポケモンカード商品B」）
            # 「ポケモンカード」で分割して最初のものを取得
            if 'ポケモンカード' in product and product.count('ポケモンカード') > 1:
                parts = product.split('ポケモンカード')
                product = 'ポケモンカード' + parts[1] if len(parts) > 1 else product

        # 終了日時を取得（期限切れチェック用）
        end_date_str = info_dict.get('終了日時', '')
        if not end_date_str:
            end_date_str = info_dict.get('応募終了', '')
        if not end_date_str:
            end_date_str = info_dict.get('締切', '')

        # 期限切れチェック（終了日が今日2026/3/31以前 → スキップ）
        if end_date_str:
            import datetime
            today = datetime.date(2026, 3, 31)
            if self._is_date_expired(end_date_str, today):
                logger.info(f"期限切れ除外: {store_name} - {product} (end_date: {end_date_str})")
                return lotteries  # 期限切れ → スキップ

        # store_nameと productが両方存在する場合のみ抽出
        if store_name and product:
            # detail_urlを取得（テーブル内またはh3内のaタグを探す）
            detail_url = ''

            # テーブル内のaタグを探す
            link = table.find('a', href=True)
            if link:
                detail_url = link.get('href', '')

            # テーブル内にaタグがない場合、h3内を探す
            if not detail_url and h3:
                h3_link = h3.find('a', href=True)
                if h3_link:
                    detail_url = h3_link.get('href', '')

            # URLが見つからない場合はフォールバック
            if not detail_url:
                detail_url = 'https://nyuka-now.com/archives/2459'

            lottery = {
                'store': store_name,
                'product': product,
                'lottery_type': info_dict.get('抽選形式', ''),
                'start_date': info_dict.get('開始日時', ''),
                'end_date': end_date_str,
                'announcement_date': info_dict.get('当選発表', ''),
                'conditions': info_dict.get('応募条件', ''),
                'detail_url': detail_url,
                'status': self._determine_status(product)
            }

            # ポケモンカード関連かどうか確認（緩和版）
            product_text = (product + ' ' + store_name).lower()
            has_pokemon_keyword = any(kw.lower() in product_text for kw in self.pokemon_keywords)
            if not has_pokemon_keyword and 'カード' in product:
                has_pokemon_keyword = True

            if has_pokemon_keyword:
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
            response = requests.get(nyuka_now_url, headers=self.headers, timeout=30)
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

                        # chusen.infoの場合、実際の販売ページURLを取得
                        if 'chusen.info' in href:
                            actual_url = self._extract_url_from_chusen_info(href)
                            if actual_url:
                                href = actual_url

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
            logger.info(f"  Warning: Could not extract direct URL from {nyuka_now_url}: {e}")
            return None

    def _extract_url_from_chusen_info(self, chusen_info_url):
        """chusen.infoのページから実際の販売ページURLを抽出"""
        try:
            response = requests.get(chusen_info_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            article = soup.find('article') or soup.find('main') or soup.find(class_='content')

            if article:
                # 外部リンク（エディオンなど）を探す
                links = article.find_all('a', href=True)

                for link in links:
                    href = link.get('href', '')
                    href_lower = href.lower()

                    # エディオンのリンクを優先的に取得（アフィリエイトリンク対応）
                    if 'edion.com' in href_lower or 'edion' in href_lower:
                        # アフィリエイトリンクの場合はmurlパラメータから実URLを抽出
                        if 'linksynergy.com' in href_lower and 'murl=' in href_lower:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(href)
                            params = urllib.parse.parse_qs(parsed.query)
                            if 'murl' in params:
                                actual_url = urllib.parse.unquote(params['murl'][0])
                                return actual_url
                        return href

                # エディオン以外の外部リンクも対象
                for link in links:
                    href = link.get('href', '')
                    if (href.startswith('http') and
                        'chusen.info' not in href and
                        'nyuka-now.com' not in href and
                        'twitter.com' not in href and
                        'facebook.com' not in href and
                        'linksynergy.com' not in href):
                        return href

            return None

        except Exception as e:
            logger.info(f"  Warning: Could not extract URL from {chusen_info_url}: {e}")
            return None

    def _check_availability(self, url):
        """販売ページが在庫ありかチェック"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            html = response.text.lower()

            # 在庫切れを示すキーワード（より厳密に）
            out_of_stock_keywords = [
                '在庫切れ', '売り切れ', '販売終了', '完売', '品切れ',
                'sold out', 'out of stock', '取り扱いを終了',
                '現在お取り扱いできません', '申し訳ございません',
                '販売を終了しました', 'この商品は現在お取り扱いできません',
                'ご指定の商品は販売しておりません', '商品が見つかりませんでした',
                'お探しの商品は見つかりませんでした', '予約受付は終了',
                '受付終了', '抽選受付は終了', '予約終了', '終了しました',
                '受付期間外', 'ただいま品切れ', '入荷待ち',
                'カートに入れることができません', '購入できません',
                'お取り扱いしておりません', '販売しておりません'
            ]

            # 在庫切れキーワードが含まれているかチェック
            for keyword in out_of_stock_keywords:
                if keyword in html:
                    logger.info(f"  Info: {url} - 在庫切れ検出: {keyword}")
                    return False

            # 購入可能を示すキーワードがあるかチェック（より厳密な判定）
            available_keywords = [
                'カートに入れる', 'カートに追加', '購入する', '予約する',
                '抽選に応募', '応募する', '申し込む', '予約受付中',
                '抽選受付中', '販売中', 'add to cart', 'buy now'
            ]

            has_available_keyword = any(keyword in html for keyword in available_keywords)

            # 購入可能キーワードがない場合も在庫切れとみなす
            if not has_available_keyword:
                logger.info(f"  Info: {url} - 購入可能キーワードなし")
                return False

            return True

        except requests.exceptions.Timeout:
            # タイムアウトの場合は除外（確認できないため）
            logger.info(f"  Warning: Timeout checking availability for {url}, excluding")
            return False
        except requests.exceptions.HTTPError as e:
            # HTTPエラーの場合は除外
            logger.info(f"  Info: {url} - HTTPエラー({e.response.status_code})により除外")
            return False
        except Exception as e:
            logger.info(f"  Warning: Could not check availability for {url}: {e}")
            # その他のエラーの場合も除外
            return False


if __name__ == '__main__':
    scraper = NyukaNowScraper()
    data = scraper.scrape()

    if data:
        # 結果をJSONファイルに保存
        output_file = '../data/nyuka_now_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {output_file}")
        logger.info(f"Found {len(data['lotteries'])} lottery entries")
