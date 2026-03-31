#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

# nyuka-now.com から直接取得
url = "https://nyuka-now.com/archives/2459"
try:
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    html = response.text

    soup = BeautifulSoup(html, 'html.parser')

    # h3タグ（店舗名）を取得
    h3_tags = soup.find_all('h3')

    print(f"=== 手動抽出: nyuka-now.com から h3 タグを取得 ===")
    print(f"Total h3 tags found: {len(h3_tags)}\n")

    # 最初の15個のh3を表示
    count = 0
    for i, h3 in enumerate(h3_tags):
        text = h3.get_text(strip=True)
        if text and len(text) > 3:  # 短すぎるものは除外
            print(f"{count+1}. {text[:60]}")
            count += 1
            if count >= 10:
                break

except Exception as e:
    print(f"エラー: {type(e).__name__}: {str(e)}")
