"""
ポケモンカード抽選情報収集メインスクリプト
"""
import json
import os
import logging
from datetime import datetime
from scrapers.nyuka_now_scraper import NyukaNowScraper
from scrapers.pokemon_center_scraper import PokemonCenterScraper
from scrapers.pokemoncenter_playwright_scraper import PokemonCenterPlaywrightScraper
from scrapers.rakuten_books_scraper import RakutenBooksScraper
from scrapers.amazon_reservation_scraper import AmazonReservationScraper
from scrapers.rakuten_reservation_scraper import RakutenReservationScraper
from scrapers.yodobashi_scraper import YodobashiScraper
from scrapers.x_lottery_scraper import XLotteryScraper
from scrapers.biccamera_scraper import BiccameraScraper
from scrapers.joshin_scraper import JoshinScraper
from scrapers.edion_scraper import EdionScraper
from scrapers.ksdenki_scraper import KsDenkiScraper
from scrapers.nojima_scraper import NojimaScraper
from scrapers.yellow_submarine_scraper import YellowSubmarineScraper
from scrapers.cardshop_serra_scraper import CardShopSerraScraper
from scrapers.sevennet_playwright_scraper import SevenNetPlaywrightScraper
from scrapers.seven_eleven_scraper import SevenElevenScraper
from scrapers.lawson_scraper import LawsonScraper
from scrapers.aeon_playwright_scraper import AeonPlaywrightScraper
from scrapers.familymart_scraper import FamilyMartScraper

# logging設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def load_previous_data(filename):
    """前回のデータを読み込み"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_data(data, filename):
    """データを保存"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_composite_key(item, data_type):
    """URL+タイトルの複合キーを生成（重複排除用）"""
    if data_type == 'lottery':
        url = item.get('url', '')
        title = item.get('product', '')
    else:  # reservation
        url = item.get('url', '')
        title = item.get('title', '')
    return f"{url}|{title}"


def detect_changes(old_data, new_data, data_type='lottery'):
    """変更を検出（URL+タイトル複合キー対応）"""
    if not old_data:
        return True, "初回実行"

    changes = []
    key_name = 'lotteries' if data_type == 'lottery' else 'reservations'

    old_count = len(old_data.get(key_name, []))
    new_count = len(new_data.get(key_name, []))

    if old_count != new_count:
        changes.append(f"件数が変化: {old_count} → {new_count}")

    # 複合キーで重複排除しながら比較
    old_items = {build_composite_key(item, data_type) for item in old_data.get(key_name, [])}
    new_items = {build_composite_key(item, data_type) for item in new_data.get(key_name, [])}

    added = new_items - old_items
    if added and len(added) <= 3:
        changes.append(f"新規: {len(added)}件")
    elif added:
        changes.append(f"新規: {len(added)}件")

    removed = old_items - new_items
    if removed:
        changes.append(f"終了: {len(removed)}件")

    return len(changes) > 0, changes


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("ポケモンカード抽選情報収集開始")
    logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'sources': []
    }

    # スクレイパー定義 (H1対応: ループ化用)
    scrapers = [
        {
            'num': 1, 'name': '入荷Now',
            'class': NyukaNowScraper, 'kwargs': {'check_availability': True},
            'filename': 'data/nyuka_now_latest.json'
        },
        {
            'num': 2, 'name': '楽天ブックス',
            'class': RakutenBooksScraper, 'kwargs': {},
            'filename': 'data/rakuten_books_latest.json'
        },
        {
            'num': 3, 'name': 'ポケモンセンター公式',
            'class': PokemonCenterScraper, 'kwargs': {},
            'filename': 'data/pokemon_center_latest.json'
        },
        {
            'num': 4, 'name': 'ポケモンセンター公式(Playwright)',
            'class': PokemonCenterPlaywrightScraper, 'kwargs': {},
            'filename': 'data/pokemon_center_pw_latest.json',
            'skip_on_empty': True
        },
        {
            'num': 5, 'name': 'Amazon',
            'class': AmazonReservationScraper, 'kwargs': {},
            'filename': 'data/amazon_reservation_latest.json',
            'data_type': 'reservation'
        },
        {
            'num': 6, 'name': '楽天ブックス予約',
            'class': RakutenReservationScraper, 'kwargs': {},
            'filename': 'data/rakuten_reservation_latest.json',
            'data_type': 'reservation'
        },
        {
            'num': 7, 'name': 'ヨドバシカメラ',
            'class': YodobashiScraper, 'kwargs': {},
            'filename': 'data/yodobashi_latest.json'
        },
        {
            'num': 8, 'name': 'ビックカメラ',
            'class': BiccameraPlaywrightScraper, 'kwargs': {},
            'filename': 'data/biccamera_latest.json'
        },
        {
            'num': 9, 'name': 'X(Twitter)',
            'class': XLotteryScraper, 'kwargs': {},
            'filename': 'data/x_lottery_latest.json'
        },
        {
            'num': 10, 'name': 'ジョーシン',
            'class': JoshinPlaywrightScraper, 'kwargs': {},
            'filename': 'data/joshin_latest.json'
        },
        {
            'num': 11, 'name': 'エディオン',
            'class': EdionPlaywrightScraper, 'kwargs': {},
            'filename': 'data/edion_latest.json'
        },
        {
            'num': 12, 'name': 'ケーズデンキ',
            'class': KsDenkiScraper, 'kwargs': {},
            'filename': 'data/ksdenki_latest.json'
        },
        {
            'num': 13, 'name': 'ノジマ',
            'class': NojimaScraper, 'kwargs': {},
            'filename': 'data/nojima_latest.json'
        },
        {
            'num': 14, 'name': 'あみあみ',
            'skip': True, 'reason': 'サプライ品中心のため除外'
        },
        {
            'num': 15, 'name': 'イエローサブマリン',
            'class': YellowSubmarineScraper, 'kwargs': {},
            'filename': 'data/yellow_submarine_latest.json'
        },
        {
            'num': 16, 'name': 'カードショップセラ',
            'class': CardShopSerraScraper, 'kwargs': {},
            'filename': 'data/cardshop_serra_latest.json'
        },
        {
            'num': 17, 'name': 'セブンネットショッピング',
            'class': SevenElevenScraper, 'kwargs': {'check_availability': True},
            'filename': 'data/seven_eleven_latest.json'
        },
        {
            'num': 18, 'name': 'セブンネット抽選(Playwright)',
            'class': SevenNetPlaywrightScraper, 'kwargs': {},
            'filename': 'data/sevennet_lottery_latest.json',
            'skip_on_empty': True
        },
        {
            'num': 19, 'name': 'ローソンHMV',
            'class': LawsonScraper, 'kwargs': {},
            'filename': 'data/lawson_latest.json'
        },
        {
            'num': 20, 'name': 'イオン',
            'class': AeonPlaywrightScraper, 'kwargs': {},
            'filename': 'data/aeon_latest.json'
        },
        {
            'num': 21, 'name': 'ファミリーマート',
            'class': FamilyMartScraper, 'kwargs': {},
            'filename': 'data/familymart_latest.json'
        },
    ]

    total_sources = len(scrapers)

    # ループでスクレイパー処理実行 (H1対応)
    for config in scrapers:
        num = config['num']
        name = config['name']

        if config.get('skip'):
            logger.info(f"\n[{num}/{total_sources}] {name}をスキップ（{config.get('reason', '')}）")
            continue

        logger.info(f"\n[{num}/{total_sources}] {name}をチェック中...")

        try:
            scraper = config['class'](**config['kwargs'])
            data = scraper.scrape()
        except Exception as e:
            logger.warning(f"✗ {name}の取得に失敗: {e}")
            continue

        if not data:
            logger.warning(f"✗ {name}の取得に失敗")
            continue

        # skip_on_empty: 空の場合はスキップ
        if config.get('skip_on_empty') and not data.get('lotteries'):
            logger.info(f"✓ {name}: 抽選なし（スキップ）")
            continue

        all_results['sources'].append(data)

        # 件数表示
        data_type = config.get('data_type', 'lottery')
        key = 'reservations' if data_type == 'reservation' else 'lotteries'
        count = len(data.get(key, []))
        label = '予約' if data_type == 'reservation' else '抽選'
        logger.info(f"✓ {name}: {count}件の{label}情報を取得")

        # 変更検出
        prev_data = load_previous_data(config['filename'])
        has_changes, changes = detect_changes(prev_data, data, data_type)
        if has_changes and changes != ["初回実行"]:
            logger.info(f"  変更検出: {changes}")

        save_data(data, config['filename'])

    # 統合データを保存
    save_data(all_results, 'data/all_lotteries.json')

    logger.info("\n" + "=" * 60)
    logger.info("収集完了")
    logger.info("=" * 60)

    # サマリー表示
    total_lotteries = sum(len(s.get('lotteries', [])) for s in all_results['sources'])
    total_reservations = sum(len(s.get('reservations', [])) for s in all_results['sources'])
    logger.info(f"\n合計: {total_lotteries}件の抽選情報、{total_reservations}件の予約情報を収集")

    # Gmail通知
    if os.environ.get('ENABLE_EMAIL_NOTIFICATION') == 'true':
        logger.info("\n📧 メール通知を送信中...")
        from notify import GmailNotifier
        notifier = GmailNotifier()
        notifier.send_notification(all_results)


if __name__ == '__main__':
    main()
