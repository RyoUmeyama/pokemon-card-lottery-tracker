"""
共通ユーティリティ関数集
"""
import re
from datetime import date, datetime
from typing import Optional


def _parse_date_flexible(date_str: str, today) -> Optional:
    """日付文字列を柔軟にパース（多様な形式対応、曜日対応）"""
    date_str = date_str.strip()

    # パターン1: 4桁年 + 月 + 日（複数区切り対応）
    m = re.match(r'^(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})日?$', date_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # パターン2: 月 + 日のみ（曜日など末尾括弧は削除）
    # 全角括弧（）と半角括弧()両対応
    date_str_clean = re.sub(r'[（\(][^）\)]*[）\)]', '', date_str)
    m = re.match(r'^(\d{1,2})[/月](\d{1,2})日?$', date_str_clean)
    if m:
        try:
            return date(today.year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    # パターン3: 4桁年 + 月 + 日 with 曜日（括弧は削除）
    date_str_clean = re.sub(r'[（\(][^）\)]*[）\)]', '', date_str)
    m = re.match(r'^(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})日?$', date_str_clean)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # パターン4: strptime での形式試行（年なし日付は明示的に年を付与）
    year_formats = ['%m月%d日', '%m/%d']
    for fmt in ['%Y/%m/%d', '%Y-%m-%d', '%Y年%m月%d日', '%m月%d日', '%m/%d']:
        try:
            if fmt in year_formats:
                # 年なし形式は明示的に現在年を付与してからパース
                if fmt == '%m月%d日':
                    parsed = datetime.strptime(f"{today.year}年{date_str}", '%Y年%m月%d日').date()
                else:  # '%m/%d'
                    parsed = datetime.strptime(f"{today.year}/{date_str}", '%Y/%m/%d').date()
            else:
                parsed = datetime.strptime(date_str, fmt).date()
            return parsed
        except ValueError:
            continue

    return None


def _extract_year_from_string(text: str) -> Optional:
    """文字列から年号を抽出（2025, 2026等）"""
    m = re.search(r'(20\d{2})(?:年)?', text)
    if m:
        return int(m.group(1))
    return None


def build_composite_key(item: dict, data_type: str) -> str:
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
