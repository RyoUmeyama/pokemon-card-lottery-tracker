"""
ポケモンセンターオンライン公式サイトからポケモンカード抽選情報をスクレイピング
"""
from datetime import datetime
import json
import logging

from .requests_base import RequestsBaseScraper

logger = logging.getLogger(__name__)


class PokemonCenterScraper(RequestsBaseScraper):
    def __init__(self):
        super().__init__(timeout=30, wait_time=1)
        self.url = "https://www.pokemoncenter-online.com/lottery/apply.html"
        self.source_name = 'pokemoncenter-online.com'

    def scrape(self):
        """抽選情報をスクレイピング"""
        lotteries = []
        has_active = False

        try:
            html_content = self.fetch_html(self.url)
            if not html_content:
                return {
                    'source': 'pokemoncenter-online.com',
                    'scraped_at': datetime.now().isoformat(),
                    'has_active_lottery': False,
                    'lotteries': []
                }

            soup = self.parse_soup(html_content)
            if not soup:
                return {
                    'source': 'pokemoncenter-online.com',
                    'scraped_at': datetime.now().isoformat(),
                    'has_active_lottery': False,
                    'lotteries': []
                }

            # 抽選商品のリストを探す
            lottery_items = soup.find_all(class_=lambda x: x and 'lottery' in x.lower())

            for item in lottery_items:
                lottery_info = self._parse_lottery_item(item)
                if lottery_info:
                    lotteries.append(lottery_info)

            # 「公開中の抽選がありません」のチェック
            no_lottery_msg = soup.find(text=lambda x: x and '公開中の抽選がありません' in x)
            has_active = len(lotteries) > 0 and not no_lottery_msg

        except Exception as e:
            logger.warning(f"Error scraping pokemoncenter-online.com direct: {e}")
            # fallback to gamepedia
            logger.info("Attempting fallback to gamepedia scraper for Pokemon Center info...")
            try:
                from .gamepedia_scraper import GamepediaScraper
                gp = GamepediaScraper()
                gp_result = gp.scrape()
                if gp_result and gp_result.get('lotteries'):
                    # gamepediaからポケセン情報を抽出
                    lotteries = [l for l in gp_result.get('lotteries', [])
                               if 'ポケモンセンター' in l.get('store', '')]
                    if lotteries:
                        logger.info(f"Found {len(lotteries)} items from gamepedia fallback")
                        has_active = True
            except Exception as fallback_e:
                logger.warning(f"Gamepedia fallback also failed: {fallback_e}")

        result = {
            'source': 'pokemoncenter-online.com',
            'scraped_at': datetime.now().isoformat(),
            'has_active_lottery': has_active,
            'lotteries': lotteries
        }

        return result

    def _parse_lottery_item(self, item):
        """抽選アイテムから情報を抽出"""
        try:
            lottery = {
                'product_name': '',
                'period': '',
                'price': '',
                'url': ''
            }

            # 商品名を取得
            title = item.find(['h2', 'h3', 'h4', 'a'])
            if title:
                lottery['product_name'] = title.get_text(strip=True)
                if title.name == 'a' and title.get('href'):
                    lottery['url'] = title['href']

            # 期間を取得
            period = item.find(text=lambda x: x and '期間' in x)
            if period:
                lottery['period'] = period.strip()

            # 価格を取得
            price = item.find(text=lambda x: x and '円' in x)
            if price:
                lottery['price'] = price.strip()

            return lottery if lottery['product_name'] else None

        except Exception as e:
            logger.error(f"Error parsing lottery item: : {e}")
            return None


if __name__ == '__main__':
    scraper = PokemonCenterScraper()
    data = scraper.scrape()

    if data:
        # 結果をJSONファイルに保存
        output_file = '../data/pokemon_center_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {output_file}")
        logger.info(f"Has active lottery: {data['has_active_lottery']}")
        logger.info(f"Found {len(data['lotteries'])} lottery entries")
