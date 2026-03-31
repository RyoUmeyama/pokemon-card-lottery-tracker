"""
入荷Now（nyuka-now.com）からポケモンカード抽選情報をスクレイピング
改良版: テーブルの前にある h3 を正確に識別、detail_url の検証、動的日付取得
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, date
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
        self.check_availability = check_availability
        self.pokemon_keywords = [
            'ポケモンカード', 'ポケカ', 'pokemon', 'ポケモン',
            'スカーレット', 'バイオレット', 'テラスタル',
            'シャイニートレジャー', 'バトルマスター', 'TCG'
        ]
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

                # 記事の更新日時を取得
                update_date = self._extract_update_date(soup)

                # 全テーブルを走査して抽選情報を抽出
                lotteries = self._parse_all_tables(soup)

                # 重複除外
                unique_lotteries = self._dedup_lotteries(lotteries)

                result = {
                    'source': 'nyuka-now.com',
                    'scraped_at': datetime.now().isoformat(),
                    'update_date': update_date,
                    'lotteries': unique_lotteries
                }

                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) ** 2
                    logging.warning(f"Retry {attempt + 1}/{max_retries} for nyuka-now.com, waiting {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Error scraping nyuka-now.com after {max_retries} retries: {e}")
                    import traceback
                    traceback.print_exc()
                    return None

    def _extract_update_date(self, soup):
        """更新日時を抽出"""
        title = soup.find('h1')
        if title:
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title.text)
            if date_match:
                return f"{date_match.group(1)}-{date_match.group(2):0>2}-{date_match.group(3):0>2}"
        return None

    def _parse_all_tables(self, soup):
        """全テーブルを走査して抽選情報を抽出"""
        lotteries = []

        # 全テーブルを取得
        tables = soup.find_all('table')

        for table in tables:
            # テーブルの前にある h3 を探す（find_previous）
            h3 = table.find_previous('h3')
            if not h3:
                continue

            h3_text = self._normalize_store_name(h3.get_text(strip=True))

            # h3 内の span に「終了」クラスがあればスキップ
            if self._is_h3_closed(h3):
                continue

            # Type1判定: h3 に「在庫あり」を含む → スキップ
            if '在庫あり' in h3_text:
                continue

            # 除外店舗チェック
            if self._is_excluded_store(h3_text):
                continue

            # テーブルから抽選情報を抽出
            table_lotteries = self._parse_lottery_table_strict(table, h3_text, h3)
            lotteries.extend(table_lotteries)

        return lotteries

    def _is_h3_closed(self, h3):
        """h3 内の span に「終了」クラスまたはテキストがあるかチェック"""
        span = h3.find('span')
        if span:
            span_class = span.get('class', [])
            if any('終了' in c or 'closed' in c for c in span_class):
                return True
        return False

    def _is_excluded_store(self, store_name):
        """除外店舗かチェック"""
        for excluded in self.excluded_stores:
            if excluded in store_name:
                return True
        return False

    def _normalize_store_name(self, name):
        """store 名を正規化"""
        if not name:
            return ''
        normalized = re.sub(r'[\s\n\r]+', ' ', name)
        return normalized.strip()

    def _parse_lottery_table_strict(self, table, store_name, h3_elem):
        """
        テーブルから抽選情報を厳密に抽出
        detail_url: テーブル内 → h3 内 → テーブルの次 p 内の順で探索
        """
        lotteries = []

        # テーブルの終了ラベル検出
        table_text = table.get_text()
        for closed_kw in self.closed_keywords:
            if closed_kw in table_text:
                return lotteries

        # th/td ペアから情報辞書を作成
        info_dict = self._parse_th_td_pairs(table.find_all('tr'))

        # 対象商品を取得
        product = self._extract_product_name(info_dict)
        if not product:
            return lotteries

        # ポケカキーワード確認
        if not self._has_pokemon_keyword(product, store_name):
            return lotteries

        # 終了日時を取得
        end_date_str = (info_dict.get('終了日時', '') or
                        info_dict.get('応募終了', '') or
                        info_dict.get('締切', ''))

        # 期限切れチェック（date.today() を使用）
        if end_date_str and self._is_date_expired(end_date_str, date.today()):
            return lotteries

        # detail_url を探索（優先度順）
        detail_url = self._find_detail_url(table, h3_elem)

        # URL が見つからない、または nyuka-now フォールバックの場合は除外
        if not detail_url:
            return lotteries

        # nyuka-now.com へのフォールバックURL は禁止（実際のリンクがない扱い）
        if 'nyuka-now.com' in detail_url:
            return lotteries

        # URL の妥当性チェック（HTTP 200 でない場合は除外）
        if not self._is_url_accessible(detail_url):
            return lotteries

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

        lotteries.append(lottery)
        return lotteries

    def _parse_th_td_pairs(self, rows):
        """th/td ペアから情報を辞書化"""
        info_dict = {}
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                for i in range(len(cells) - 1):
                    if cells[i].name == 'th' and cells[i + 1].name == 'td':
                        label = cells[i].get_text(strip=True)
                        value = cells[i + 1].get_text(strip=True)
                        if label and value:
                            info_dict[label] = value
        return info_dict

    def _extract_product_name(self, info_dict):
        """商品名を抽出"""
        product = (info_dict.get('対象商品', '') or
                  info_dict.get('商品名', '') or
                  info_dict.get('ポケモンカード商品', ''))

        if product:
            product = product.split('\n')[0].strip()

        return product

    def _has_pokemon_keyword(self, product, store_name):
        """ポケモンカード関連かチェック"""
        text = (product + ' ' + store_name).lower()
        has_kw = any(kw.lower() in text for kw in self.pokemon_keywords)
        return has_kw or 'カード' in product

    def _is_date_expired(self, date_str, today):
        """日付が今日より前かチェック"""
        try:
            month_match = re.search(r'(\d{1,2})月', date_str)
            day_match = re.search(r'(\d{1,2})日', date_str)

            if month_match and day_match:
                month = int(month_match.group(1))
                day = int(day_match.group(1))
                year_match = re.search(r'(\d{4})年', date_str)
                year = int(year_match.group(1)) if year_match else today.year

                end_date = date(year, month, day)
                return end_date < today
        except Exception:
            pass

        return False

    def _find_detail_url(self, table, h3_elem):
        """
        detail_url を探索（優先度順）
        1. テーブル内のaタグ
        2. h3内のaタグ
        3. テーブルの次のp内のaタグ
        """
        # 1. テーブル内のaタグ
        link = table.find('a', href=True)
        if link:
            url = link.get('href', '')
            if url:
                return url

        # 2. h3 内のaタグ
        if h3_elem:
            h3_link = h3_elem.find('a', href=True)
            if h3_link:
                url = h3_link.get('href', '')
                if url:
                    return url

        # 3. テーブルの次のp内のaタグ
        next_p = table.find_next('p')
        if next_p:
            p_link = next_p.find('a', href=True)
            if p_link:
                url = p_link.get('href', '')
                if url:
                    return url

        return None

    def _is_url_accessible(self, url):
        """URL が HTTP 200 でアクセス可能かチェック（HEAD, timeout=5秒）"""
        if not url:
            return False

        try:
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False

    def _determine_status(self, text):
        """ステータスを判定"""
        if '受付中' in text or '実施中' in text:
            return 'active'
        elif '終了' in text:
            return 'closed'
        return 'unknown'

    def _dedup_lotteries(self, lotteries):
        """重複を除外"""
        unique = []
        seen = set()

        for lottery in lotteries:
            if not lottery.get('product') or not lottery.get('store'):
                continue

            key = (lottery.get('product', ''), lottery.get('detail_url', ''))
            if key not in seen:
                seen.add(key)
                lottery['source'] = 'nyuka-now.com'
                unique.append(lottery)

        return unique


if __name__ == '__main__':
    scraper = NyukaNowScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/nyuka_now_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {output_file}")
        logger.info(f"Found {len(data['lotteries'])} lottery entries")
