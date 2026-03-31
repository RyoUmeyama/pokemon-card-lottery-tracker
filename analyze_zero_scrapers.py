#!/usr/bin/env python3
"""
20個の0件スクレイパーの原因を推測し分類する
"""
import json
import os

print("=" * 80)
print("【分析】0件スクレイパーの原因推測")
print("=" * 80)

zero_scrapers = {
    'aeon_latest.json': {'type': 'Playwright', 'reason': 'JS動的生成 vs skip=True'},
    'biccamera_latest.json': {'type': 'Playwright', 'reason': 'JS動的生成 vs skip=True'},
    'cardshop_serra_latest.json': {'type': 'Requests', 'reason': 'サイトに情報がない可能性'},
    'dragonstar_latest.json': {'type': 'Playwright', 'reason': 'バグ: 実行時は1件取得できる'},
    'edion_latest.json': {'type': 'Requests', 'reason': 'サイト構造変更 or フィルタリング除外'},
    'familymart_latest.json': {'type': 'Playwright', 'reason': 'JS動的生成 vs skip=True'},
    'geo_latest.json': {'type': 'Requests', 'reason': 'サイトに情報がない可能性'},
    'joshin_latest.json': {'type': 'Playwright', 'reason': 'JS動的生成 vs skip=True'},
    'ksdenki_latest.json': {'type': 'Requests', 'reason': '404エラー or サイト構造変更'},
    'lawson_latest.json': {'type': 'Requests', 'reason': 'サイト構造変更 or フィルタリング除外'},
    'nojima_latest.json': {'type': 'Requests', 'reason': 'サイトに情報がない可能性'},
    'pokemon_center_latest.json': {'type': 'Playwright', 'reason': 'JS動的生成 vs skip=True'},
    'rakuten_books_latest.json': {'type': 'Requests', 'reason': 'フィルタリング除外（game混在）'},
    'seven_eleven_latest.json': {'type': 'Requests', 'reason': 'サイト構造変更 or フィルタリング除外'},
    'sevennet_lottery_latest.json': {'type': 'Playwright', 'reason': 'Incapsulaブロック'},
    'surugaya_latest.json': {'type': 'Requests', 'reason': 'フィルタリング除外（main.py L233）'},
    'tsutaya_latest.json': {'type': 'Requests', 'reason': 'HTTP 404エラー'},
    'x_lottery_latest.json': {'type': 'Requests', 'reason': 'X API不通 or Xに情報がない'},
    'yellow_submarine_latest.json': {'type': 'Requests', 'reason': 'サイト構造未対応'},
    'yodobashi_latest.json': {'type': 'Requests', 'reason': 'サイト構造変更 or 期限切れ除外'},
}

# カテゴリ別に分類
categories = {
    'Playwright スキップ': [],
    'Playwright バグ': [],
    'Requests: フィルタリング除外': [],
    'Requests: サイト技術的問題': [],
    'Requests: サイトに情報がない': [],
    'Requests: その他': [],
}

for fname, info in zero_scrapers.items():
    if info['type'] == 'Playwright':
        if 'skip=True' in info['reason']:
            categories['Playwright スキップ'].append(fname)
        else:
            categories['Playwright バグ'].append(fname)
    else:
        if 'フィルタリング' in info['reason']:
            categories['Requests: フィルタリング除外'].append(fname)
        elif '404' in info['reason'] or 'Incapsula' in info['reason'] or '不通' in info['reason']:
            categories['Requests: サイト技術的問題'].append(fname)
        elif 'サイトに情報がない' in info['reason']:
            categories['Requests: サイトに情報がない'].append(fname)
        else:
            categories['Requests: その他'].append(fname)

print("\n【カテゴリ別分類】\n")

for category, files in categories.items():
    if files:
        print(f"{category}: {len(files)} 個")
        for f in files:
            reason = zero_scrapers[f]['reason']
            print(f"  - {f:<40} | {reason}")

print("\n【重要度別対応】\n")

print("【優先度 P0: 即座に調査・修正】")
print("  ドラゴンスター (dragonstar_latest.json)")
print("    └ 実行時は1件取得可能だが、ファイルは0件")
print("    └ 原因: 保存時のエラー or main.py のバグ")
print("    └ 対応: main.py と scraper 統合テストで確認")

print("\n【優先度 P1: 設定確認・テスト】")
print("  Playwright スキップ系: 3個")
print("    - pokemon_center_latest.json")
print("    - biccamera_latest.json")
print("    - familymart_latest.json, joshin_latest.json, aeon_latest.json")
print("    └ 原因: main.py で skip=True 設定されている")
print("    └ 対応: skip=False に変更して実行するか、スキップ理由を確認")

print("\n【優先度 P2: 技術的問題を調査】")
print("  サイト技術的問題: 2個")
print("    - sevennet_lottery_latest.json (Incapsulaブロック)")
print("    - tsutaya_latest.json (HTTP 404)")
print("    - ksdenki_latest.json (404 or 構造変更)")
print("    - x_lottery_latest.json (X API不通)")
print("    └ 対応: Playwright への切り替え or 別スクレイパー実装")

print("\n【優先度 P3: フィルタリング確認】")
print("  フィルタリング除外: 3個")
print("    - rakuten_books_latest.json (game混在)")
print("    - surugaya_latest.json (除外リスト)")
print("    - lawson_latest.json, seven_eleven_latest.json, yodobashi_latest.json")
print("    └ 対応: フィルタリングルール見直し")

print("\n" + "=" * 80)
