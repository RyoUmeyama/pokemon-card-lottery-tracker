#!/usr/bin/env python3
import logging
import json
from scrapers.dragonstar_scraper import DragonstarScraper

# ログレベルを DEBUG に設定
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

print("=" * 80)
print("【デバッグ】DragonstarScraper を実行し、0件になる理由を調査")
print("=" * 80)

try:
    scraper = DragonstarScraper()
    result = scraper.scrape()

    print("\n【実行結果】")
    print(f"  source: {result.get('source')}")
    print(f"  lotteries: {len(result.get('lotteries', []))} 件")
    print(f"  scraped_at: {result.get('scraped_at')}")

    if result.get('error'):
        print(f"  error: {result.get('error')}")

    # 詳細出力
    if result.get('lotteries'):
        print("\n【取得データ】")
        for i, item in enumerate(result['lotteries'][:5]):
            print(f"  {i+1}. {item}")
    else:
        print("\n【取得データ】 0件（データなし）")

    # JSON で保存
    print("\n【フル結果（JSON形式）】")
    print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"スクレイパー実行エラー: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
