"""
ポケモンカード抽選情報のHTMLレポート生成
"""
import html
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 定数定義
DEFAULT_CLEANUP_DAYS = 30
MAX_CONDITION_LENGTH = 200


def normalize_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """H8: all_lotteries.json スキーマ整理
    - キー命名統一
    - 不要フィールド削除
    """
    normalized_sources = []

    for source in data.get('sources', []):
        normalized_source = {
            'source': source.get('source', 'unknown'),
            'lotteries': [],
            'upcoming_products': []
        }

        # タイムスタンプがあれば記録
        if 'scraped_at' in source:
            normalized_source['scraped_at'] = source['scraped_at']

        # 各ロッテリーのスキーマ統一
        for lottery in source.get('lotteries', []):
            normalized_lottery = {
                'product': lottery.get('product', ''),
                'store': lottery.get('store', ''),
                'lottery_type': lottery.get('lottery_type', ''),
                'start_date': lottery.get('start_date', ''),
                'end_date': lottery.get('end_date', ''),
                'announcement_date': lottery.get('announcement_date', ''),
                'conditions': lottery.get('conditions', ''),
                'detail_url': lottery.get('detail_url', ''),
            }
            # 不要フィールドを除去（status, _source など）

            normalized_source['lotteries'].append(normalized_lottery)

        # 今後の発売予定情報のスキーマ統一
        for upcoming in source.get('upcoming_products', []):
            normalized_upcoming = {
                'product_name': upcoming.get('product_name', ''),
                'release_date': upcoming.get('release_date', ''),
                'lottery_schedule': upcoming.get('lottery_schedule', ''),
                'store': upcoming.get('store', ''),
                'detail_url': upcoming.get('detail_url', ''),
            }
            normalized_source['upcoming_products'].append(normalized_upcoming)

        normalized_sources.append(normalized_source)

    return {
        'timestamp': data.get('timestamp', ''),
        'sources': normalized_sources
    }


def parse_date(date_string: Any) -> Any:
    """M7: 日付文字列をdatetime形式に正規化（パース失敗時は元文字列保持）"""
    if not date_string or not isinstance(date_string, str):
        return date_string

    # 複数フォーマットを試す
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y年%m月%d日',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    # パース失敗時は元文字列を返す
    return date_string


def get_lottery_status(lottery: Dict[str, Any]) -> str:
    """抽選のステータスを判定（受付中/終了/予定）"""
    start_date_str = lottery.get('start_date', '')
    end_date_str = lottery.get('end_date', '')
    today = datetime.now().date()

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    # datetime オブジェクトに変換できたかチェック
    if isinstance(end_date, datetime):
        if end_date.date() < today:
            return '終了'
    if isinstance(start_date, datetime):
        if start_date.date() > today:
            return '予定'

    return '受付中'


def is_new_lottery(timestamp: str) -> bool:
    """24時間以内に追加されたかチェック（新着判定）"""
    if not timestamp or not isinstance(timestamp, str):
        return False
    try:
        from datetime import timedelta
        item_time = datetime.fromisoformat(timestamp)
        current_time = datetime.now()
        return (current_time - item_time) < timedelta(hours=24)
    except (ValueError, TypeError):
        return False


def cleanup_old_data(data: Dict[str, Any], days: int = 30) -> Dict[str, Any]:
    """M6: 30日以上前のデータを削除＆2025年以前のデータを非表示"""
    if 'timestamp' not in data:
        return data

    try:
        base_time = datetime.fromisoformat(data['timestamp'])
    except (ValueError, AttributeError):
        return data

    cutoff_time = base_time - timedelta(days=days)
    cutoff_year = 2025  # 2025年以前のデータを非表示

    for source in data.get('sources', []):
        if 'lotteries' not in source:
            continue

        # 各ロッテリーのstart_dateをチェック
        filtered_lotteries = []
        for lottery in source['lotteries']:
            start_date_str = lottery.get('start_date', '')
            if start_date_str:
                start_dt = parse_date(start_date_str)
                if isinstance(start_dt, datetime):
                    # 年が2025以下のデータは完全に除外
                    if start_dt.year <= cutoff_year:
                        continue
                    # 30日以内のデータのみ保持
                    if start_dt >= cutoff_time:
                        filtered_lotteries.append(lottery)
                else:
                    # パース失敗の場合は保持
                    filtered_lotteries.append(lottery)
            else:
                # start_dateがない場合は保持
                filtered_lotteries.append(lottery)

        source['lotteries'] = filtered_lotteries

    return data


def load_data(filename: str = 'data/all_lotteries.json') -> Dict[str, Any]:
    """データを読み込み（スキーマ検証 + クリーンアップ付き）"""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # M5: スキーマ検証 - 必須フィールド確認
    if 'timestamp' not in data:
        raise ValueError("Missing required field: 'timestamp'")
    if 'sources' not in data or not isinstance(data['sources'], list):
        raise ValueError("Missing or invalid required field: 'sources' (must be list)")

    # 各ソースの検証
    for i, source in enumerate(data['sources']):
        if 'source' not in source:
            raise ValueError(f"Source[{i}]: Missing required field 'source'")
        if 'lotteries' in source and isinstance(source['lotteries'], list):
            for j, lottery in enumerate(source['lotteries']):
                if 'product' not in lottery or not lottery['product']:
                    raise ValueError(f"Source[{i}].lotteries[{j}]: Missing required field 'product'")

    # M6: 30日以上前のデータを削除
    data = cleanup_old_data(data, days=DEFAULT_CLEANUP_DAYS)

    # H8: スキーマ統一（キー命名統一 + 不要フィールド削除）
    data = normalize_schema(data)

    return data


def generate_html_report(data: Dict[str, Any], output_file: str = 'data/lottery_report.html') -> None:
    """HTMLレポートを生成"""

    timestamp = datetime.fromisoformat(data['timestamp'])

    # 全抽選情報と今後の発売予定を収集
    all_lotteries = []
    all_upcoming = []
    for source in data['sources']:
        for lottery in source.get('lotteries', []):
            lottery['_source'] = source['source']
            all_lotteries.append(lottery)
        for upcoming in source.get('upcoming_products', []):
            upcoming['_source'] = source['source']
            all_upcoming.append(upcoming)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ポケモンカード抽選・販売情報</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}

        header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .summary {{
            background: #f8f9fa;
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .summary h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
        }}

        .filter-controls {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .filter-controls input {{
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #ddd;
            border-radius: 25px;
            font-size: 1em;
            transition: border-color 0.3s;
        }}

        .filter-controls input:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .lotteries {{
            padding: 30px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        table thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}

        table th {{
            padding: 15px;
            text-align: left;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}

        table th:hover {{
            background: linear-gradient(135deg, #5568d3 0%, #6a3d91 100%);
        }}

        table th.sortable::after {{
            content: ' ↕️';
            opacity: 0.5;
        }}

        table th.sorted-asc::after {{
            content: ' ↑';
            opacity: 1;
        }}

        table th.sorted-desc::after {{
            content: ' ↓';
            opacity: 1;
        }}

        table tbody tr {{
            border-bottom: 1px solid #e0e0e0;
            transition: background-color 0.2s;
        }}

        table tbody tr:hover {{
            background-color: #f5f5f5;
        }}

        table td {{
            padding: 12px 15px;
        }}

        table td.store {{
            font-weight: bold;
            color: #667eea;
        }}

        table td.deadline {{
            color: #d32f2f;
            font-weight: 500;
        }}

        table td a {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.85em;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        table td a:hover {{
            transform: translateY(-1px);
            box-shadow: 0 3px 10px rgba(102, 126, 234, 0.4);
        }}

        .status-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 700;
            margin: 3px 0;
        }}

        .status-badge.active {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }}

        .status-badge.ended {{
            background: linear-gradient(135deg, #999999 0%, #777777 100%);
            color: white;
        }}

        .status-badge.upcoming {{
            background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
            color: white;
        }}

        .status-badge.new {{
            background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
            color: white;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{
                opacity: 1;
            }}
            50% {{
                opacity: 0.7;
            }}
            100% {{
                opacity: 1;
            }}
        }}

        .lottery-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}

        .lottery-card:hover {{
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
            border-color: #667eea;
        }}

        .lottery-card .header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}

        .lottery-card .store {{
            font-size: 1.1em;
            color: #667eea;
            font-weight: bold;
        }}

        .lottery-card .source {{
            background: #e0e7ff;
            color: #667eea;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }}

        .status-badge.active {{
            background: #4CAF50;
            color: white;
        }}

        .status-badge.ended {{
            background: #999999;
            color: white;
        }}

        .status-badge.upcoming {{
            background: #FF9800;
            color: white;
        }}

        .lottery-card .product {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 15px;
            line-height: 1.5;
            font-weight: 600;
        }}

        .lottery-card .detail-row {{
            display: flex;
            align-items: start;
            margin: 10px 0;
            color: #555;
        }}

        .lottery-card .detail-row .icon {{
            width: 25px;
            margin-right: 10px;
            flex-shrink: 0;
        }}

        .lottery-card .detail-row .content {{
            flex: 1;
        }}

        .lottery-card .lottery-type {{
            display: inline-block;
            background: #ffd700;
            color: #333;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            margin: 10px 0;
        }}

        .lottery-card a {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            margin-top: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 600;
        }}

        .lottery-card a:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}

        .no-results .emoji {{
            font-size: 4em;
            margin-bottom: 20px;
        }}

        .upcoming-section {{
            background: #fffbf0;
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .upcoming-section h2 {{
            color: #ff6b35;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .upcoming-card {{
            background: white;
            border: 2px solid #ffb347;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}

        .upcoming-card:hover {{
            box-shadow: 0 8px 25px rgba(255, 107, 53, 0.15);
            transform: translateY(-2px);
            border-color: #ff6b35;
        }}

        .upcoming-card .product-name {{
            font-size: 1.2em;
            color: #333;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .upcoming-card .date-badge {{
            display: inline-block;
            background: #ff6b35;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .upcoming-card .schedule-info {{
            color: #555;
            margin: 10px 0;
            line-height: 1.5;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            header h1 {{
                font-size: 1.8em;
                margin-bottom: 10px;
            }}

            header .subtitle {{
                font-size: 0.95em;
            }}

            .container {{
                border-radius: 10px;
                padding: 15px;
            }}

            .stats {{
                grid-template-columns: 1fr;
            }}

            .stat-card {{
                padding: 15px;
            }}

            .stat-card .number {{
                font-size: 1.5em;
            }}

            .filter-controls {{
                padding: 15px;
            }}

            .filter-controls input {{
                font-size: 16px;
                padding: 10px 15px;
            }}

            table {{
                font-size: 0.85em;
            }}

            table th, table td {{
                padding: 8px 5px;
            }}

            table th {{
                font-size: 0.75em;
            }}

            table td a {{
                padding: 4px 8px;
                font-size: 0.75em;
            }}

            .lotteries {{
                padding: 15px;
            }}

            .lottery-card {{
                padding: 15px;
                margin-bottom: 15px;
            }}

            .lottery-card .header {{
                flex-direction: column;
                gap: 10px;
            }}

            .lottery-card .product {{
                font-size: 1.1em;
            }}

            .upcoming-card {{
                padding: 15px;
            }}

            .upcoming-card .product-name {{
                font-size: 1em;
            }}

            footer {{
                padding: 15px;
                font-size: 0.85em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎴 ポケモンカード抽選・販売情報</h1>
            <div class="subtitle">最終更新: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}</div>
        </header>

        <div class="summary">
            <h2>📊 サマリー</h2>
            <div class="stats">
"""

    # サマリー統計
    for source in data['sources']:
        status_text = ""
        if source['source'] == 'pokemoncenter-online.com':
            status_text = "✅ 抽選実施中" if source.get('has_active_lottery') else "⚠️ 現在抽選なし"

        lottery_count = len(source.get('lotteries', []))
        html_content += f"""
                <div class="stat-card">
                    <div class="number">{lottery_count}</div>
                    <div class="label">{source['source']}</div>
                    {f'<div style="margin-top: 10px; color: #667eea;">{status_text}</div>' if status_text else ''}
                </div>
"""

    html_content += f"""
            </div>
        </div>

        <div class="filter-controls">
            <div style="display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap;">
                <input type="text" id="searchBox" placeholder="🔍 商品名、店舗名、抽選形式で検索..." onkeyup="filterLotteries()" style="flex: 1; min-width: 200px;">
                <select id="sortSelect" onchange="sortLotteries()" style="padding: 12px 15px; border: 2px solid #ddd; border-radius: 25px; font-size: 1em; cursor: pointer; background: white; color: #333; font-weight: 500;">
                    <option value="deadline">📅 期限順（近い順）</option>
                    <option value="store">🏪 店舗名順</option>
                    <option value="newest">🆕 新着順</option>
                </select>
            </div>
        </div>
"""

    # 今後の発売予定セクション
    if all_upcoming:
        html_content += """
        <div class="upcoming-section">
            <h2>🗓️ 今後の発売予定・抽選予定</h2>
"""
        for upcoming in all_upcoming:
            product_name = upcoming.get('product_name', '')
            release_date = upcoming.get('release_date', '')
            lottery_schedule = upcoming.get('lottery_schedule', '')
            store = upcoming.get('store', '')
            url = upcoming.get('detail_url', '')
            source = upcoming.get('_source', 'unknown')

            # XSS対策
            product_name_escaped = html.escape(product_name)
            release_date_escaped = html.escape(release_date)
            lottery_schedule_escaped = html.escape(lottery_schedule)
            store_escaped = html.escape(store)
            source_escaped = html.escape(source)

            html_content += f"""
            <div class="upcoming-card">
                <div class="product-name">📦 {product_name_escaped}</div>
"""
            if release_date:
                html_content += f"""
                <div class="date-badge">📅 発売予定: {release_date_escaped}</div>
"""
            if lottery_schedule:
                html_content += f"""
                <div class="schedule-info">🎯 抽選予定: {lottery_schedule_escaped}</div>
"""
            if store:
                html_content += f"""
                <div class="schedule-info">🏪 {store_escaped}</div>
"""
            html_content += f"""
                <div class="schedule-info" style="font-size: 0.85em; color: #999;">📌 {source_escaped}</div>
"""
            if url and url.startswith('http'):
                html_content += f"""
                <a href="{html.escape(url)}" target="_blank">🔗 詳細を見る</a>
"""
            html_content += """
            </div>
"""
        html_content += """
        </div>
"""

    html_content += """
        <div class="lotteries" id="lotteriesList">
            <table id="lotteriesTable">
                <thead>
                    <tr>
                        <th class="sortable" data-column="store">🏪 店舗名</th>
                        <th class="sortable" data-column="product">📦 商品名</th>
                        <th class="sortable" data-column="deadline">📅 締切日</th>
                        <th class="sortable" data-column="status">ステータス</th>
                        <th class="sortable" data-column="type">抽選形式</th>
                        <th>詳細</th>
                    </tr>
                </thead>
                <tbody>
"""

    # 締切日でデフォルトソート（昇順）
    def get_sort_key(lottery):
        end_date = lottery.get('end_date', '')
        if isinstance(end_date, str):
            # YYYY-MM-DD 形式で ソート（パース困難な場合は最後に）
            try:
                from datetime import datetime
                return (0, datetime.strptime(end_date[:10], '%Y-%m-%d') if len(end_date) >= 10 else datetime.max)
            except:
                return (1, end_date)
        return (1, '')

    all_lotteries_sorted = sorted(all_lotteries, key=get_sort_key)

    # 各抽選情報をテーブル行として表示
    for i, lottery in enumerate(all_lotteries_sorted, 1):
        store = lottery.get('store', '')
        product = lottery.get('product', '')
        lottery_type = lottery.get('lottery_type', '')
        start_date = lottery.get('start_date', '')
        end_date = lottery.get('end_date', '')
        announcement = lottery.get('announcement_date', '')
        conditions = lottery.get('conditions', '')
        url = lottery.get('detail_url', '')
        source = lottery.get('_source', 'unknown')

        # ステータスバッジを取得
        status = get_lottery_status(lottery)
        status_class_map = {'受付中': 'active', '終了': 'ended', '予定': 'upcoming'}
        status_class = status_class_map.get(status, 'active')

        # 新着判定
        timestamp = lottery.get('timestamp', '')
        is_new = is_new_lottery(timestamp)

        # バッジテキストと多重バッジ
        badge_html = f'<span class="status-badge {status_class}">●{status}</span>'
        if is_new:
            badge_html += '<span class="status-badge new">🆕 新着</span>'
        status_badge = badge_html

        # H5: XSS対策 - html.escape() で ユーザー由来データをエスケープ
        store_escaped = html.escape(store)
        product_escaped = html.escape(product)
        lottery_type_escaped = html.escape(lottery_type)
        source_escaped = html.escape(source)
        announcement_escaped = html.escape(announcement)
        conditions_escaped = html.escape(conditions)

        # テーブル行として出力（timestamp は既に定義済み）
        html_content += f"""
                    <tr data-search="{product.lower()} {store.lower()} {lottery_type.lower()}" data-timestamp="{html.escape(timestamp)}" data-store="{store_escaped}" data-deadline="{html.escape(end_date)}">
                        <td class="store" data-sort-value="{store_escaped}">{store_escaped}</td>
                        <td data-sort-value="{product_escaped}">{product_escaped}</td>
                        <td class="deadline" data-sort-value="{html.escape(end_date)}">{html.escape(end_date)}</td>
                        <td>{status_badge}</td>
                        <td data-sort-value="{lottery_type_escaped}">{lottery_type_escaped if lottery_type else '—'}</td>
                        <td>
"""
        if url and url.startswith('http'):
            html_content += f'<a href="{html.escape(url)}" target="_blank">詳細</a>'
        else:
            html_content += '—'
        html_content += """
                        </td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
"""

    if not all_lotteries:
        html_content += """
            <div class="no-results">
                <div class="emoji">🔍</div>
                <div>現在、抽選・販売情報はありません</div>
            </div>
"""

    html_content += f"""
        </div>

        <footer>
            <p>🤖 自動収集システム | データ件数: {len(all_lotteries)}件</p>
        </footer>
    </div>

    <script>
        let currentSort = {{ column: 'deadline', direction: 'asc' }};

        function filterLotteries() {{
            const searchText = document.getElementById('searchBox').value.toLowerCase();
            const rows = document.querySelectorAll('#lotteriesTable tbody tr');
            let visibleCount = 0;

            rows.forEach(row => {{
                const searchData = row.getAttribute('data-search');
                if (searchData.includes(searchText)) {{
                    row.style.display = '';
                    visibleCount++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}

        function sortLotteries() {{
            const sortSelect = document.getElementById('sortSelect').value;
            const tbody = document.querySelector('#lotteriesTable tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((a, b) => {{
                if (sortSelect === 'deadline') {{
                    // 期限順（近い順）
                    const aDeadline = a.getAttribute('data-deadline') || '';
                    const bDeadline = b.getAttribute('data-deadline') || '';
                    return aDeadline.localeCompare(bDeadline);
                }} else if (sortSelect === 'store') {{
                    // 店舗名順
                    const aStore = a.getAttribute('data-store') || '';
                    const bStore = b.getAttribute('data-store') || '';
                    return aStore.localeCompare(bStore, 'ja');
                }} else if (sortSelect === 'newest') {{
                    // 新着順（新しい順）
                    const aTimestamp = a.getAttribute('data-timestamp') || '0000-00-00';
                    const bTimestamp = b.getAttribute('data-timestamp') || '0000-00-00';
                    return bTimestamp.localeCompare(aTimestamp);  // 逆順（新しい順）
                }}
                return 0;
            }});

            // ソート結果を反映
            rows.forEach(row => tbody.appendChild(row));
        }}

        function sortTable(column) {{
            const table = document.getElementById('lotteriesTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not([style*="display: none"])'));

            // ソート方向の切り替え
            if (currentSort.column === column) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.column = column;
                currentSort.direction = 'asc';
            }}

            // ソート実行
            const columnIndex = {{'store': 0, 'product': 1, 'deadline': 2, 'status': 3, 'type': 4}}[column];
            rows.sort((a, b) => {{
                let aVal = a.children[columnIndex].getAttribute('data-sort-value') || a.children[columnIndex].textContent;
                let bVal = b.children[columnIndex].getAttribute('data-sort-value') || b.children[columnIndex].textContent;

                // 数値ソート試行
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return currentSort.direction === 'asc' ? aNum - bNum : bNum - aNum;
                }}

                // 文字列ソート
                if (currentSort.direction === 'asc') {{
                    return aVal.localeCompare(bVal);
                }} else {{
                    return bVal.localeCompare(aVal);
                }}
            }});

            // ソート結果を反映
            rows.forEach(row => tbody.appendChild(row));

            // ヘッダのソート状態を更新
            document.querySelectorAll('#lotteriesTable th.sortable').forEach(th => {{
                th.classList.remove('sorted-asc', 'sorted-desc');
                if (th.getAttribute('data-column') === column) {{
                    th.classList.add(currentSort.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
                }}
            }});
        }}

        // ヘッダクリック時にソート実行
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('#lotteriesTable th.sortable').forEach(th => {{
                th.addEventListener('click', () => {{
                    sortTable(th.getAttribute('data-column'));
                }});
            }});

            // デフォルトで deadline でソート
            sortTable('deadline');
            // ドロップダウンのデフォルト値を設定
            document.getElementById('sortSelect').value = 'deadline';
        }});
    </script>
</body>
</html>
"""

    # HTMLファイルを出力
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_file


def main() -> None:
    try:
        data = load_data()
        output_file = generate_html_report(data)
        logger.info(f"✅ HTMLレポートを生成しました: {output_file}")
        logger.info(f"\nブラウザで開くには:")
        logger.info(f"  open {output_file}")
    except FileNotFoundError:
        logger.error("❌ データファイルが見つかりません")
        logger.error("まず python main.py を実行してデータを収集してください")


if __name__ == '__main__':
    main()
