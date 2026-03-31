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
        # 除外すべきセクション見出しパターン
        self.excluded_section_patterns = [
            '直近の販売履歴', '通知履歴', 'ポケモン×', 'コラボ',
            '過去の', '終了した', 'その他', 'おすすめ',
            'ニュース', '推奨', 'FAQ', '質問', 'サービス'
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
                    product = lottery.get('product', '')

                    # 品質フィルター: 商品名の妥当性チェック
                    # 1. テキスト長チェック (5文字未満 or 100文字以上)
                    if len(product) < 5 or len(product) >= 100:
                        continue

                    # 2. 日付のみのパターン除外 (例: "3月27日(金)10:00", "4月6日 18時以降順次")
                    if re.match(r'^\d{1,2}月\d{1,2}日', product):
                        continue

                    # 3. 販売方法のみのパターン除外
                    if product in ['WEB抽選受付（当選者には店頭販売）', 'WEB抽選受付（当選者にはオンライン販売）',
                                   '先着配布', '追記', 'WEB抽選受付', '先着販売']:
                        continue

                    key = (product, lottery.get('detail_url', ''))
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

    def _is_valid_store_name(self, store_name):
        """store名が有効か判定（除外パターンチェック）"""
        if not store_name:
            return False
        # 除外パターンに該当するか確認
        for pattern in self.excluded_section_patterns:
            if pattern in store_name:
                return False
        return True

    def _normalize_store_name(self, store_name):
        """store名を正規化（空白・改行除去）"""
        if not store_name:
            return ''
        # 複数の空白・改行を単一空白に統一
        normalized = re.sub(r'[\s\n\r]+', ' ', store_name)
        # 両端の空白を除去
        return normalized.strip()

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
        """テーブルから抽選情報を抽出（ヘッダー動的マッピング対応）"""
        lotteries = []

        # テーブルの前にあるh3タグから店舗名を取得（除外パターン・正規化付き）
        store_name = ''
        h3 = table.find_previous('h3')
        if h3:
            raw_store_name = h3.get_text(strip=True)
            # 正規化と有効性チェック
            normalized_name = self._normalize_store_name(raw_store_name)
            if self._is_valid_store_name(normalized_name):
                store_name = normalized_name

        rows = table.find_all('tr')

        # ★ ステップ1: 全行をスキャンしてヘッダーパターン（最初のセルがth + 続くセルがtd）を検出
        header_mapping = {}  # 列ラベル → インデックス（2番目のセル td の値がヘッダー）

        for idx, row in enumerate(rows[:5]):  # 最初の5行をスキャン
            cells = row.find_all(['td', 'th'])

            # パターン：最初のセルがth（列ラベル）+ 2番目のセルがtd（データ）
            if (len(cells) >= 2 and
                cells[0].name == 'th' and
                cells[1].name == 'td' and
                len(cells[1].get_text(strip=True)) < 50):  # ラベルは短い

                # 最初のセルがヘッダーキーワード候補
                header_text = cells[0].get_text(strip=True)

                # キーワードマッチングで列ラベルを判定
                if any(kw in header_text for kw in ['終了日', '応募終了', '締切', 'End']):
                    header_mapping['end_date'] = header_text
                elif any(kw in header_text for kw in ['開始日', '応募開始', 'Start']):
                    header_mapping['start_date'] = header_text
                elif any(kw in header_text for kw in ['抽選形式', '販売形式', 'Type']):
                    header_mapping['lottery_type'] = header_text
                elif any(kw in header_text for kw in ['当選発表', '発表日']):
                    header_mapping['announcement_date'] = header_text
                elif any(kw in header_text for kw in ['応募条件', '条件']):
                    header_mapping['conditions'] = header_text

        for row in rows:
            cells = row.find_all(['td', 'th'])

            # 最低限のセル数をチェック
            if len(cells) >= 1:
                cell_texts = [c.get_text(strip=True) for c in cells]

                # ヘッダー行を除外：thタグを含む行は全てスキップ（ラベル値ペア含む）
                has_th = any(cell.name == 'th' for cell in cells)
                if has_th:
                    continue

                # ここ以降、全てのセルは td のみ
                store = store_name  # h3 から取得した店舗名を使う
                product = cell_texts[1] if len(cell_texts) > 1 else ''

                # 店舗と商品の両方があれば抽出対象
                if store and product:
                    # 品質フィルタ：productの品質チェック
                    # (a) 10文字未満は除外（「先着配布」「1月26日(月)」等のゴミデータ）
                    if len(product) < 10:
                        continue

                    # (b) 日付のみの場合は除外
                    if re.match(r'^[0-9/月日年()（）\s]+$', product):
                        continue

                    # (c) 先頭100文字で切り詰め（長すぎる説明文を防止）
                    product = product[:100]

                    # フォールバック：th がない場合は固定インデックス
                    lottery_type = ''
                    start_date = ''
                    end_date = cell_texts[4] if len(cell_texts) > 4 else ''
                    announcement_date = cell_texts[5] if len(cell_texts) > 5 else ''
                    conditions = cell_texts[6] if len(cell_texts) > 6 else ''

                    lottery = {
                        'store': store,
                        'product': product,
                        'lottery_type': lottery_type,
                        'start_date': start_date,
                        'end_date': end_date,
                        'announcement_date': announcement_date,
                        'conditions': conditions,
                        'detail_url': '',
                        'status': self._determine_status(' '.join(cell_texts))
                    }

                    # リンクを抽出
                    link = row.find('a')
                    if link and link.get('href'):
                        url = link['href']

                        # chusen.infoの場合は直接実URLを取得
                        if 'chusen.info' in url:
                            actual_url = self._extract_url_from_chusen_info(url)
                            if actual_url:
                                url = actual_url
                                # 在庫チェック
                                if self.check_availability:
                                    if not self._check_availability(url):
                                        continue  # 在庫切れの場合はスキップ
                            lottery['detail_url'] = url
                        # 入荷Nowの記事ページから実際の販売・抽選ページのURLを取得
                        elif 'nyuka-now.com' in url:
                            direct_url = self._extract_direct_url(url)
                            if direct_url:
                                lottery['detail_url'] = direct_url
                            elif self.check_availability:
                                # 在庫チェックが有効で、直接URLが取得できない場合はスキップ
                                continue
                            else:
                                # 在庫チェックが無効の場合はnyuka-now.comのURLをそのまま使用
                                lottery['detail_url'] = url
                        else:
                            lottery['detail_url'] = url

                    # 直接URLが取得できなかった場合はnyuka-nowのURLをそのまま使う
                    if not lottery['detail_url'] or lottery['detail_url'] == '':
                        lottery['detail_url'] = self.url  # nyuka-nowの記事URLを使用

                    # Amazon、Yahoo!ショッピング、駿河屋、エディオンを除外
                    store_text = lottery['store'].lower()
                    url_text = lottery['detail_url'].lower()
                    if 'amazon' in store_text or 'amazon' in url_text:
                        continue
                    if 'yahoo' in store_text or 'yahoo' in url_text or 'shopping.yahoo' in url_text:
                        continue
                    if '駿河屋' in lottery['store'] or 'suruga' in url_text:
                        continue
                    if 'エディオン' in lottery['store'] or 'edion' in url_text:
                        continue

                    # 中身がない情報を除外（ヘッダー行など）
                    if lottery['store'] in ['販売開始日時', '店舗/サイト名', '対象商品', '店舗', 'Store', '']:
                        continue
                    if lottery['product'] in ['詳細', '商品名', '商品', 'Product', '']:
                        continue

                    # 空のデータは除外
                    if lottery['store'] and lottery['product']:
                        # ポケモンカード関連かどうか確認（緩和版）
                        product_text = (lottery['product'] + ' ' + lottery['store']).lower()

                        # ポケモンキーワードが含まれているか確認
                        has_pokemon_keyword = any(kw.lower() in product_text for kw in self.pokemon_keywords)

                        # キーワードがなくても「カード」を含む場合は対象に
                        if not has_pokemon_keyword and 'カード' in lottery['product']:
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
