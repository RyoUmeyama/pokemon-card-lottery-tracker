"""
Google Formsからのポケモンカード抽選・予約情報スクレイピング
Playwrightを使用してフォーム情報を取得
"""
import asyncio
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from scrapers.playwright_base import PlaywrightBaseScraper

logger = logging.getLogger(__name__)


class GoogleFormsScraper(PlaywrightBaseScraper):
    """Google Formsスクレイパー"""

    def __init__(self):
        super().__init__()
        # 調査対象のGoogle Forms
        self.forms = [
            {
                'name': 'トレカプラザ55',
                'url': 'https://docs.google.com/forms/d/e/1FAIpQLSf5h7fCUFaxELstaVEK36zcjFgifqmmlkY8UsGCq_iiGs8bkQ/viewform',
                'store': 'トレカプラザ55通販'
            },
            {
                'name': 'ノジマオンライン',
                'url': 'https://docs.google.com/forms/d/e/1FAIpQLSdYHmBreNk1egfE7F5YsVs7LEDoVkhA5r2onCH4rZvxwpOmDg/viewform',
                'store': 'ノジマオンライン'
            }
        ]

    def scrape(self):
        """Google Formsから抽選情報をスクレイピング"""
        all_forms = []

        for form in self.forms:
            try:
                logger.info(f"Scraping Google Form: {form['name']}")
                form_data = self._scrape_form(form['url'], form['name'], form['store'])
                if form_data:
                    all_forms.append(form_data)
            except Exception as e:
                logger.warning(f"Error scraping {form['name']}: {e}")
                continue

        return {
            "source": "google-forms",
            "scraped_at": datetime.now().isoformat(),
            "forms": all_forms,
            "lotteries": self._extract_lotteries(all_forms)
        }

    def _scrape_form(self, url, form_name, store_name):
        """指定URLのGoogle Formをスクレイピング"""
        content = self.run_async(self.fetch_page_content(
            url,
            wait_for_js=True,
            scroll=False,
            extra_wait=5,
            wait_selector='[role="form"]'  # フォーム要素の出現を待機
        ))

        if not content:
            logger.warning(f"Failed to fetch content for {form_name}")
            return None

        soup = BeautifulSoup(content, 'html.parser')

        form_data = {
            'form_name': form_name,
            'store': store_name,
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'form_title': '',
            'form_description': '',
            'form_status': 'accepting',  # デフォルトをacceptingに変更
            'is_accepting': True  # デフォルトをTrueに変更
        }

        # フォームタイトルを取得（複数セレクタ試行）
        title_elem = soup.find('div', {'class': 'OA0qFb'})
        if not title_elem:
            title_elem = soup.find('h1')
        if not title_elem:
            title_elem = soup.find('div', {'class': 'freebirdFormviewerViewHeaderTitleRequiredLegend'})
        if title_elem:
            form_data['form_title'] = title_elem.get_text(strip=True)

        # フォーム説明文を取得（複数セレクタ試行）
        description_elem = soup.find('div', {'class': 'EWp5xe'})
        if not description_elem:
            description_elem = soup.find('div', {'class': 'freebirdFormviewerViewHeaderDescription'})
        if description_elem:
            form_data['form_description'] = description_elem.get_text(strip=True)

        # フォーム全体のテキストを取得（ステータス判定用）
        page_text = soup.get_text(separator=' ', strip=True).lower()

        # 受付終了判定（終了キーワードがあれば閉鎖）
        if any(keyword in page_text for keyword in ['受付終了', '終了しました', 'closed form', 'form is closed']):
            form_data['form_status'] = 'closed'
            form_data['is_accepting'] = False
        else:
            # フォーム要素が存在すれば受付中と判断
            if soup.find('[role="form"]') or soup.find('form') or 'input' in str(soup):
                form_data['form_status'] = 'accepting'
                form_data['is_accepting'] = True
            else:
                form_data['form_status'] = 'unknown'
                form_data['is_accepting'] = False

        # ポケモンカード関連のキーワード検出（デフォルトはTrue）
        form_data['is_pokemon_card'] = True  # Google Formsスクレイパーなので全て抽選対象

        return form_data

    def _extract_lotteries(self, forms):
        """Google Formsから抽選情報を抽出"""
        lotteries = []

        for form in forms:
            # フォームが取得でき、かつ受付中の場合のみ出力
            if form['is_accepting']:
                lottery_item = {
                    'product': form['form_title'] or form['form_name'],
                    'store': form['store'],
                    'form_name': form['form_name'],
                    'description': form['form_description'],
                    'url': form['url'],
                    'status': form['form_status'],
                    'source': 'google-forms',
                    'scraped_at': form['scraped_at']
                }
                lotteries.append(lottery_item)
                logger.info(f"Added lottery: {lottery_item['product']} from {form['store']}")

        return lotteries
