#!/usr/bin/env python3
import json
from scrapers.nyuka_now_scraper import NyukaNowScraper
import requests
from bs4 import BeautifulSoup

print("=" * 80)
print("【cmd_235 最終ラウンド】nyuka-now.com スクレイパー vs 手動抽出 比較")
print("=" * 80)

# (1) スクレイパーで実行
print("\n(1) スクレイパー実行結果:")
try:
    scraper = NyukaNowScraper()
    result = scraper.scrape()
    lotteries = result['lotteries'] if result else []
    print(f"  スクレイパー取得件数: {len(lotteries)}")

    if lotteries:
        print("\n  最初の5件:")
        for i, item in enumerate(lotteries[:5]):
            print(f"    {i+1}. store={item['store'][:30]:30} | product={item['product'][:40]}")
except Exception as e:
    print(f"  スクレイパーエラー: {type(e).__name__}: {str(e)}")
    lotteries = []

# (2) curl + 手動解析
print("\n(2) nyuka-now.com 直接アクセス（手動抽出）:")
try:
    url = "https://nyuka-now.com/archives/2459"
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'

    soup = BeautifulSoup(response.text, 'html.parser')

    # h3（店舗セクション）とその直後のテーブルを抽出
    h3_tags = soup.find_all('h3')
    manual_items = []

    for h3 in h3_tags:
        store_text = h3.get_text(strip=True)
        # ポケカ関連のみ抽出
        if 'ポケモンカード' in store_text or 'ポケカ' in store_text:
            # h3の直後のテーブルを探す
            next_table = h3.find_next('table')
            if next_table:
                rows = next_table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells and len(cells) >= 2:
                        # 店舗名と商品名を抽出
                        cell_text = cells[0].get_text(strip=True)
                        if cell_text and cell_text not in ['店舗', 'Store']:
                            manual_items.append({
                                'store': cell_text[:30],
                                'product': store_text[:40]
                            })

    print(f"  手動抽出件数: {len(manual_items)}")
    if manual_items:
        print("\n  最初の5件:")
        for i, item in enumerate(manual_items[:5]):
            print(f"    {i+1}. store={item['store']:30} | product={item['product']}")

except Exception as e:
    print(f"  手動抽出エラー: {type(e).__name__}: {str(e)}")
    manual_items = []

# (3) 比較結果
print("\n(3) 比較結果:")
print(f"  スクレイパー: {len(lotteries)} 件")
print(f"  手動抽出:     {len(manual_items)} 件")
print(f"  差分:        {abs(len(lotteries) - len(manual_items))} 件")

if len(lotteries) > 0 and len(manual_items) > 0:
    # サンプル比較（最初の3件）
    print("\n(4) 詳細比較（最初の3件）:")
    for i in range(min(3, len(lotteries), len(manual_items))):
        print(f"\n  [{i+1}番目]")
        print(f"    スクレイパー: store={lotteries[i]['store'][:40]} | product={lotteries[i]['product'][:40]}")
        print(f"    手動抽出:     store={manual_items[i]['store'][:40]} | product={manual_items[i]['product'][:40]}")

        # 一致判定
        store_match = lotteries[i]['store'] == manual_items[i]['store']
        product_match = lotteries[i]['product'] == manual_items[i]['product']
        match = "✓ 一致" if (store_match and product_match) else "✗ 不一致"
        print(f"    判定: {match}")

print("\n" + "=" * 80)
