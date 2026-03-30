"""
ポケモンカード抽選情報収集メインスクリプト
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
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
from scrapers.surugaya_scraper import SurugayaScraper
from scrapers.geo_scraper import GeoScraper
from scrapers.tsutaya_scraper import TsutayaScraper

# logging設定
# 今後の改善: config/logging.yaml を作成し、以下のように外部化することを推奨
# import logging.config
# logging.config.fileConfig('config/logging.yaml')
# ただし、現在はmain.pyで直接設定することで簡潔性を優先している。
DETAIL_DISPLAY_THRESHOLD = 3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ポケカキーワード定義
POKEMON_CARD_KEYWORDS = [
    'ポケモンカード', 'ポケカ', 'pokemon card', 'pokemon tcg',
    'ポケモン カード', 'ポケモンtcg',
    'スカーレット', 'バイオレット', 'テラスタル',
    'バトルマスター', 'シャイニートレジャー',
    'サイバージャッジ', 'ワイルドフォース',
    'クリムゾンヘイズ', 'ステラミラクル',
    'レイジングサーフ', 'ナイトワンダラー',
    '変幻の仮面', 'プロモカード',
    'ポケセン', 'トレカ',
]

EXCLUDE_KEYWORDS = [
    'ぬいぐるみ', 'フィギュア', 'ギフト', 'Tシャツ', 'アパレル',
    'ハイキュー', '一番くじ', 'グッズセット', 'ミスド', 'クッション',
    'タオル', 'バッグ', 'ポーチ', '母の日', 'スリッパ', 'パジャマ',
    'キーホルダー', 'ストラップ', 'マグカップ', 'お菓子', 'お弁当',
]


def filter_expired(items: list) -> list:
    """期限切れの抽選・予約を除外"""
    import re
    from datetime import date
    today = date.today()
    filtered = []
    for item in items:
        end_date_str = item.get('end_date', '') or item.get('deadline', '') or ''
        if not end_date_str:
            period = item.get('period', '') or ''
            if period:
                # 範囲形式: 「1/15～2/20」「2025/1/15～2025/2/20」→ 終了日を抽出
                m = re.search(r'[～〜\-→]\s*(\d{1,4}[/年]\d{1,2}(?:[/月]\d{1,2}日?)?)', period)
                if m:
                    end_date_str = m.group(1)
                else:
                    # 単一日付: period自体を日付として使う
                    end_date_str = period.strip()
        if not end_date_str:
            item['expiry_status'] = 'unknown'
            filtered.append(item)
            continue
        try:
            parsed = None
            for fmt in ['%Y/%m/%d', '%Y-%m-%d', '%Y年%m月%d日', '%m/%d', '%m月%d日']:
                try:
                    parsed = datetime.strptime(end_date_str.strip(), fmt).date()
                    if fmt in ['%m/%d', '%m月%d日']:
                        parsed = parsed.replace(year=today.year)
                    break
                except ValueError:
                    continue
            if parsed is None:
                item['expiry_status'] = 'unparseable'
                filtered.append(item)
            elif parsed >= today:
                item['expiry_status'] = 'active'
                filtered.append(item)
            else:
                logger.info(f"期限切れ除外: {item.get('product', '?')} (end: {end_date_str})")
        except Exception:
            item['expiry_status'] = 'error'
            filtered.append(item)
    return filtered


def filter_pokemon_card_only(items: list) -> list:
    """ポケモンカード関連のみ残す"""
    filtered = []
    for item in items:
        text = ' '.join([
            str(item.get('product', '')),
            str(item.get('product_name', '')),
            str(item.get('title', '')),
            str(item.get('description', '')),
        ]).lower()
        if any(kw.lower() in text for kw in POKEMON_CARD_KEYWORDS):
            # ポケカKWマッチ後、除外KWに該当したら除外
            if any(kw.lower() in text for kw in EXCLUDE_KEYWORDS):
                logger.info(f"非カード商品除外: {item.get('product', '?')}")
            else:
                filtered.append(item)
        else:
            logger.info(f"ポケカ外除外: {item.get('product', '?')}")
    return filtered


def load_previous_data(filename: str) -> Optional[Dict[str, Any]]:
    """前回のデータを読み込み"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_data(data: Dict[str, Any], filename: str) -> None:
    """データを保存"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_composite_key(item: Dict[str, Any], data_type: str) -> str:
    """URL+タイトルの複合キーを生成（重複排除用）

    Args:
        item: スクレイパーから取得した抽選/予約情報辞書
        data_type: 'lottery' または 'reservation'
                  - 'lottery': product フィールドを使用
                  - 'reservation': title フィールドを使用

    Returns:
        str: "{url}|{title}" 形式の複合キー（重複検出に使用）
    """
    if data_type == 'lottery':
        url = item.get('url', '')
        title = item.get('product', '')
    else:  # reservation
        url = item.get('url', '')
        title = item.get('title', '')
    return f"{url}|{title}"


def detect_changes(old_data: Optional[Dict[str, Any]], new_data: Dict[str, Any], data_type: str = 'lottery') -> tuple[bool, List[str]]:
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
    if added and len(added) <= DETAIL_DISPLAY_THRESHOLD:
        changes.append(f"新規: {len(added)}件")
    elif added:
        changes.append(f"新規: {len(added)}件")

    removed = old_items - new_items
    if removed:
        changes.append(f"終了: {len(removed)}件")

    return len(changes) > 0, changes


def main() -> None:
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
            'skip': True, 'reason': 'WAF/アクセス拒否 (cmd_219: 403)'
            # BLOCKED: PokemonCenterPlaywrightScraper - 403 Forbidden
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
            'skip': True, 'reason': 'Timeout (cmd_219: 000) - URL調査必要'
            # BLOCKED: BiccameraPlaywrightScraper - URL接続タイムアウト
        },
        {
            'num': 9, 'name': 'X(Twitter)',
            'class': XLotteryScraper, 'kwargs': {},
            'filename': 'data/x_lottery_latest.json'
        },
        {
            'num': 10, 'name': 'ジョーシン',
            'skip': True, 'reason': 'Timeout (cmd_219: 000) - URL調査必要'
            # BLOCKED: JoshinPlaywrightScraper - URL接続タイムアウト
        },
        {
            'num': 11, 'name': 'エディオン',
            'class': EdionScraper, 'kwargs': {},
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
        {
            'num': 22, 'name': '駿河屋',
            'class': SurugayaScraper, 'kwargs': {},
            'filename': 'data/surugaya_latest.json'
        },
        {
            'num': 23, 'name': 'GEO',
            'class': GeoScraper, 'kwargs': {},
            'filename': 'data/geo_latest.json'
        },
        {
            'num': 24, 'name': 'TSUTAYA',
            'class': TsutayaScraper, 'kwargs': {},
            'filename': 'data/tsutaya_latest.json'
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

        # フィルタ適用（抽選データの場合）
        data_type = config.get('data_type', 'lottery')
        if data_type == 'lottery':
            before_count = len(data.get('lotteries', []))
            data['lotteries'] = filter_pokemon_card_only(data.get('lotteries', []))
            data['lotteries'] = filter_expired(data.get('lotteries', []))
            after_count = len(data.get('lotteries', []))
            if before_count > after_count:
                logger.info(f"  フィルタ適用: {before_count}件 → {after_count}件")

        all_results['sources'].append(data)

        # 件数表示
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
