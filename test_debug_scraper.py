#!/usr/bin/env python3
import json
from scrapers.nyuka_now_scraper import NyukaNowScraper

print("=" * 80)
print("【詳細デバッグ】スクレイパーの全37件を確認")
print("=" * 80)

try:
    scraper = NyukaNowScraper()
    result = scraper.scrape()
    lotteries = result['lotteries'] if result else []

    print(f"\n取得総件数: {len(lotteries)}\n")

    # 全件を表示
    for i, item in enumerate(lotteries):
        print(f"{i+1:2}. store={item['store'][:35]:35} | product={item['product'][:40]}")

    # ストア別集計
    print("\n" + "=" * 80)
    print("【ストア別集計】")
    store_counts = {}
    for item in lotteries:
        store = item['store']
        store_counts[store] = store_counts.get(store, 0) + 1

    for store, count in sorted(store_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {store:40} : {count:2} 件")

except Exception as e:
    print(f"エラー: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
