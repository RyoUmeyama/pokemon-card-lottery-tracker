#!/usr/bin/env python3
"""
TSUTAYA ホームページから、ポケカ関連リンクを探す
"""
import requests
from bs4 import BeautifulSoup
import re

print("=" * 80)
print("【TSUTAYA ホームページ分析】ポケカ関連リンク探索")
print("=" * 80)

url = "https://tsutaya.tsite.jp/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

try:
    print(f"\n【GET {url}】\n")
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = 'utf-8'

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # ポケモンカード関連のリンクを探す
        print("【ポケモン/カード関連のリンク】\n")

        found_links = False

        # 全 a タグをスキャン
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # ポケモン・カード関連キーワード
            if any(kw in href.lower() or kw in text.lower() for kw in ['pokemon', 'card', 'ポケ', 'カード', 'tcg']):
                print(f"  Text: {text[:40]:<40}")
                print(f"  Href: {href[:70]}")
                print()
                found_links = True

        if not found_links:
            print("  (ポケモンカード関連のリンクが見つかりません)")
            print("\n【代替: 全カテゴリリンク（最初の20件）】\n")

            count = 0
            for link in links:
                if count >= 20:
                    break
                href = link.get('href', '')
                text = link.get_text(strip=True)

                if href and text and len(text) > 2:
                    print(f"  {text[:40]:<40} → {href[:60]}")
                    count += 1

    else:
        print(f"HTTP Error: {response.status_code}")

except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")

print("\n" + "=" * 80)
print("【結論】")
print("TSUTAYA オンラインがポケマンカード抽選・予約情報を掲載していない可能性が高い。")
print("通常は以下で対応:")
print("  1. TSUTAYA 実店舗での抽選→公開情報が限定")
print("  2. 統合抽選情報サイト（nyuka-now等）で TSUTAYA 情報を取得")
print("  3. ポケカ専門店（カードラッシュ等）の方が情報が豊富")
print("=" * 80)
