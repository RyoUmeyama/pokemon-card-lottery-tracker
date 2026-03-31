#!/usr/bin/env python3
from scrapers.nyuka_now_scraper import NyukaNowScraper

try:
    s = NyukaNowScraper()
    d = s.scrape()

    print(f"件数: {len(d['lotteries'])}")
    print("\n最初の10件:")
    for i, l in enumerate(d['lotteries'][:10]):
        print(f"  {i+1}. store={l['store'][:25]} | product={l['product'][:35]}")
except Exception as e:
    print(f"エラー: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
