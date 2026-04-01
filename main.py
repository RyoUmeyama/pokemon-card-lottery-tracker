"""
ポケモンカード抽選情報収集メインスクリプト
"""
import asyncio
import importlib
import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

import yaml

from constants import EXCLUDE_KEYWORDS, POKEMON_KEYWORDS
from utils import (_extract_year_from_string, _parse_date_flexible,
                   build_composite_key)
# Scraper imports moved to dynamic loading via config/scrapers.yaml
# (All imports are now loaded dynamically in load_scrapers_from_config())

# logging設定
# 今後の改善: config/logging.yaml を作成し、以下のように外部化することを推奨
# import logging.config
# logging.config.fileConfig('config/logging.yaml')
# ただし、現在はmain.pyで直接設定することで簡潔性を優先している。
DETAIL_DISPLAY_THRESHOLD = 3

# logs/ ディレクトリを自動作成
os.makedirs('logs', exist_ok=True)

# ログハンドラを設定
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
today_str = datetime.now().strftime('%Y%m%d')
log_filename = f'logs/scraping_{today_str}.log'

# ストリームハンドラ（コンソール出力）
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(log_format))

# ファイルハンドラ（RotatingFileHandler: 5MB, 最大3世代）
file_handler = RotatingFileHandler(
    log_filename,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,  # 最大3世代
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(log_format))

logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler]
)
logger = logging.getLogger(__name__)


def load_scrapers_from_config(config_path: str = 'config/scrapers.yaml') -> List[Dict[str, Any]]:
    """config/scrapers.yaml からスクレイパー設定を読み込む"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        scrapers = config_data.get('scrapers', [])

        # 動的にスクレイパークラスをロード
        for scraper_config in scrapers:
            if not scraper_config.get('skip') and 'class' not in scraper_config:
                module_name = scraper_config.get('module')
                class_name = scraper_config.get('class')
                if module_name and class_name:
                    try:
                        module = importlib.import_module(module_name)
                        scraper_config['class'] = getattr(module, class_name)
                    except (ImportError, AttributeError) as e:
                        logger.warning(f"Failed to load {module_name}.{class_name}: {e}")
                        scraper_config['skip'] = True
                        scraper_config['reason'] = f'Import failed: {e}'

            # スキップされていなくてもkwargsがない場合は空辞書を設定
            if not scraper_config.get('skip') and 'kwargs' not in scraper_config:
                scraper_config['kwargs'] = {}

        return scrapers
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        return []
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML: {e}")
        return []


def filter_expired(items: list) -> list:
    """期限切れの抽選・予約を除外（改良版：年号チェック＋多様な日付形式対応）"""
    import re
    from datetime import date
    today = date.today()
    filtered = []

    # ポケカ専門ショップのホワイトリスト（期限切れ判定をバイパス）
    WHITELIST_STORES = []  # ドラゴンスター削除

    for item in items:
        # ドラゴンスター固有フィルタ：status==closed または detail_url が # で終わるエントリを除外
        store = item.get('store', '')
        if 'ドラゴンスター' in store:
            status = item.get('status', '')
            detail_url = item.get('detail_url', '')
            if status == 'closed' or (detail_url and detail_url.endswith('#')):
                logger.info(f"ドラゴンスター除外: {item.get('product', '?')} (status: {status}, url: {detail_url})")
                continue

        # ホワイトリスト対象は常に通す（期限切れ判定をスキップ）
        if any(store_name in store for store_name in WHITELIST_STORES):
            filtered.append(item)
            continue
        # ステップ1: 年号チェック（2025年以前を完全除外）
        end_date_str = item.get('end_date', '') or item.get('deadline', '') or ''
        start_date_str = item.get('start_date', '') or ''
        period_str = item.get('period', '') or ''

        # 年号抽出対象
        check_strings = [end_date_str, start_date_str, period_str]
        skip_item = False
        for check_str in check_strings:
            if check_str:
                year = _extract_year_from_string(check_str)
                if year and year <= 2025:
                    logger.info(f"2025年以前除外: {item.get('product', '?')} (year: {year})")
                    skip_item = True
                    break

        if skip_item:
            continue

        # ステップ2: 期限日を抽出（end_dateがない場合、periodから抽出）
        if not end_date_str:
            if period_str:
                # 範囲形式: 「1/15～2/20」「2025/1/15～2025/2/20」→ 終了日を抽出
                m = re.search(r'[～〜\-→]\s*(\d{1,4}[/年]\d{1,2}(?:[/月]\d{1,2}日?)?)', period_str)
                if m:
                    end_date_str = m.group(1)
                else:
                    end_date_str = period_str.strip()

        if not end_date_str:
            item['expiry_status'] = 'unknown'
            filtered.append(item)
            continue

        # ステップ3: 柔軟な日付パース
        try:
            parsed = _parse_date_flexible(end_date_str, today)

            if parsed is None:
                # パース失敗は除外（expiry_status='unparseable'として除外）
                logger.info(f"日付パース失敗で除外: {item.get('product', '?')} (end: {end_date_str})")
            elif parsed >= today:
                item['expiry_status'] = 'active'
                filtered.append(item)
            else:
                logger.info(f"期限切れ除外: {item.get('product', '?')} (end: {end_date_str})")
        except Exception as e:
            logger.warning(f"日付パースエラーで除外: {end_date_str} - {e}")

    return filtered


def filter_pokemon_card_only(items: list) -> list:
    """ポケモンカード関連のみ残す

    ホワイトリスト: ポケカ専門ショップ（ドラゴンスター等）は自動通過
    """
    # ポケカ専門ショップのホワイトリスト（キーワード不要で通す）
    WHITELIST_STORES = []  # ドラゴンスター削除

    # 抽選情報集約サイトのホワイトリスト（複数商品を一覧にするため、全て通す）
    WHITELIST_SOURCES = []

    filtered = []
    for item in items:
        store = item.get('store', '')
        source = item.get('source', '')

        # ホワイトリスト対象は自動通過
        if any(store_name in store for store_name in WHITELIST_STORES):
            filtered.append(item)
            continue

        # ホワイトリストソースも自動通過
        if any(src in source for src in WHITELIST_SOURCES):
            filtered.append(item)
            continue

        # それ以外はキーワードチェック
        text = ' '.join([
            str(item.get('product', '')),
            str(item.get('product_name', '')),
            str(item.get('title', '')),
            str(item.get('description', '')),
        ]).lower()
        if any(kw.lower() in text for kw in POKEMON_KEYWORDS):
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


def detect_changes(old_data: Optional[Dict[str, Any]], new_data: Dict[str, Any], data_type: str = 'lottery') -> tuple[bool, List[str]]:
    """変更を検出（URL+タイトル複合キー対応）"""
    if not old_data:
        return True, ["初回実行"]

    changes = []
    key_name = 'lotteries' if data_type == 'lottery' else 'reservations'

    old_count = len(old_data.get(key_name, []))
    new_count = len(new_data.get(key_name, []))

    if old_count != new_count:
        changes.append(f"件数が変化: {old_count} → {new_count}")

    old_items = old_data.get(key_name, [])
    new_items = new_data.get(key_name, [])

    old_keys = {build_composite_key(item, data_type) for item in old_items}
    new_keys = {build_composite_key(item, data_type) for item in new_items}

    # 新規アイテム
    added = new_keys - old_keys
    if added:
        changes.append(f"新規: {len(added)}件")

    # 削除されたアイテム
    removed = old_keys - new_keys
    if removed:
        changes.append(f"終了: {len(removed)}件")

    has_changes = len(changes) > 0
    return has_changes, changes


async def execute_scraper(config: Dict[str, Any], semaphore: asyncio.Semaphore, total_sources: int) -> Optional[Dict[str, Any]]:
    """単一スクレイパーを実行（Semaphoreで同時実行数制限）"""
    async with semaphore:
        num = config['num']
        name = config['name']

        if config.get('skip'):
            logger.info(f"[{num}/{total_sources}] {name}をスキップ")
            return None

        logger.info(f"[{num}/{total_sources}] {name}をチェック中...")

        try:
            scraper = config['class'](**config['kwargs'])
            data = scraper.scrape()
        except Exception as e:
            logger.warning(f"✗ {name}の取得に失敗: {e}")
            return None

        if not data:
            logger.warning(f"✗ {name}の取得に失敗")
            return None

        if config.get('skip_on_empty') and not data.get('lotteries'):
            logger.info(f"✓ {name}: 抽選なし（スキップ）")
            return None

        data_type = config.get('data_type', 'lottery')
        if data_type == 'lottery':
            for item in data.get('lotteries', []):
                if 'source' not in item:
                    item['source'] = data.get('source', '')

            before_count = len(data.get('lotteries', []))
            data['lotteries'] = filter_pokemon_card_only(data.get('lotteries', []))
            data['lotteries'] = filter_expired(data.get('lotteries', []))
            after_count = len(data.get('lotteries', []))
            if before_count > after_count:
                logger.info(f"  フィルタ適用: {before_count}件 → {after_count}件")

        key = 'reservations' if data_type == 'reservation' else 'lotteries'
        count = len(data.get(key, []))
        label = '予約' if data_type == 'reservation' else '抽選'
        logger.info(f"✓ {name}: {count}件の{label}情報を取得")

        if count == 0:
            logger.warning(f"⚠️  {name}: 0件の{label}情報")
            return {'data': data, 'zero_alert': True, 'name': name}

        prev_data = load_previous_data(config['filename'])
        has_changes, changes = detect_changes(prev_data, data, data_type)
        if has_changes and changes != ["初回実行"]:
            logger.info(f"  変更検出: {changes}")

        save_data(data, config['filename'])
        return {'data': data, 'zero_alert': False, 'name': name}


async def run_scrapers_async(scrapers: List[Dict[str, Any]], all_results: Dict[str, Any]) -> None:
    """asyncio.gatherでスクレイパーを並列実行"""
    total_sources = len(scrapers)
    semaphore = asyncio.Semaphore(5)  # 同時実行数を5に制限
    
    tasks = [execute_scraper(config, semaphore, total_sources) for config in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if result is None or isinstance(result, Exception):
            continue
        if isinstance(result, dict) and 'data' in result:
            all_results['sources'].append(result['data'])
            if result['zero_alert']:
                all_results['zero_alert_sources'].append(result['name'])


def main() -> None:
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("ポケモンカード抽選情報収集開始")
    logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'sources': [],
        'zero_alert': False,
        'zero_alert_sources': []
    }

    scrapers = load_scrapers_from_config('config/scrapers.yaml')

    if not scrapers:
        logger.error("Failed to load scrapers from config/scrapers.yaml")
        return

    # asyncio.run で並列実行
    asyncio.run(run_scrapers_async(scrapers, all_results))

    # 統合データを保存
    save_data(all_results, 'data/all_lotteries.json')

    logger.info("\n" + "=" * 60)
    logger.info("収集完了")
    logger.info("=" * 60)

    # サマリー表示
    total_lotteries = sum(len(s.get('lotteries', [])) for s in all_results['sources'])
    total_reservations = sum(len(s.get('reservations', [])) for s in all_results['sources'])
    logger.info(f"\n合計: {total_lotteries}件の抽選情報、{total_reservations}件の予約情報を収集")

    # 全体0件アラート
    if total_lotteries == 0 and total_reservations == 0:
        logger.critical("⚠️  全スクレイパーで0件: データ取得に重大な問題の可能性")
        all_results['zero_alert'] = True
    elif all_results['zero_alert_sources']:
        logger.warning(f"⚠️  以下のスクレイパーで0件: {', '.join(all_results['zero_alert_sources'])}")

    # URL検証
    logger.info("\n🔗 detail_url検証を実行中...")
    import subprocess
    result = subprocess.run(['python3', 'scripts/verify_urls.py', '--remove'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        logger.warning("URLチェックで無効なURLが検出されました")

    # Gmail通知
    if os.environ.get('ENABLE_EMAIL_NOTIFICATION') == 'true':
        logger.info("\n📧 メール通知を送信中...")
        from notify import GmailNotifier
        notifier = GmailNotifier()
        notifier.send_notification(all_results)


if __name__ == '__main__':
    main()
