#!/usr/bin/env python3
import json
import glob
import os

print("=" * 80)
print("【cmd_235 品質改善ラウンド】各スクレイパーの結果品質確認")
print("=" * 80)

# data/*_latest.json を一覧取得
files = sorted(glob.glob('data/*_latest.json'))

print(f"\n対象ファイル数: {len(files)} 個\n")
print(f"{'ファイル名':<50} {'件数':>8} {'形式':>10}")
print("-" * 70)

zero_count_files = []
total_items = 0

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)

        # lotteries または results または items キーを探す
        if isinstance(data, dict):
            if 'lotteries' in data:
                count = len(data.get('lotteries', []))
                key_type = 'lotteries'
            elif 'results' in data:
                count = len(data.get('results', []))
                key_type = 'results'
            elif 'items' in data:
                count = len(data.get('items', []))
                key_type = 'items'
            else:
                # キーを調べる
                keys = list(data.keys())
                if keys:
                    count = len(data.get(keys[0], []))
                    key_type = keys[0]
                else:
                    count = 0
                    key_type = 'empty'
        else:
            count = len(data) if isinstance(data, list) else 0
            key_type = 'list'

        filename = os.path.basename(f)
        print(f"{filename:<50} {count:>8} {key_type:>10}")

        if count == 0:
            zero_count_files.append(filename)

        total_items += count

    except Exception as e:
        filename = os.path.basename(f)
        print(f"{filename:<50} {'ERROR':<8} {str(e)[:10]}")

print("-" * 70)
print(f"{'合計':<50} {total_items:>8}")
print(f"\n【0件スクレイパー】")
if zero_count_files:
    for fname in zero_count_files:
        print(f"  - {fname}")
else:
    print("  なし（全スクレイパーが1件以上のデータを取得）")
