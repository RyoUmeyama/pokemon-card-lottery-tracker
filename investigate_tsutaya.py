#!/usr/bin/env python3
"""
TSUTAYA オンラインのポケモンカード検索 URL を調査
"""
import requests
from urllib.parse import quote

print("=" * 80)
print("【TSUTAYA URL 調査】ポケモンカード検索ページの正しいURL")
print("=" * 80)

base_url = "https://tsutaya.tsite.jp"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

# パターン1: 現在の URL（400エラーの可能性）
urls_to_test = [
    # 現在の URL
    {
        'name': '現在の URL',
        'url': 'https://tsutaya.tsite.jp/search/?keyword=ポケモンカード&sort=release_date&area=&status='
    },
    # エンコード版
    {
        'name': 'URLエンコード版',
        'url': 'https://tsutaya.tsite.jp/search/?keyword=%E3%83%9D%E3%82%B1%E3%83%A2%E3%83%B3%E3%82%AB%E3%83%BC%E3%83%89'
    },
    # シンプル版
    {
        'name': 'シンプル版',
        'url': 'https://tsutaya.tsite.jp/search/?keyword=pokemon'
    },
    # ベースURL
    {
        'name': 'ベースURL',
        'url': 'https://tsutaya.tsite.jp/'
    },
    # /cd/ パス（音楽）
    {
        'name': '/search/ ルート',
        'url': 'https://tsutaya.tsite.jp/search/'
    },
    # TCG カテゴリ直接
    {
        'name': 'TCG category (推測)',
        'url': 'https://tsutaya.tsite.jp/item/pokemon_card/'
    },
]

print("\n【URL アクセステスト】\n")

for test in urls_to_test:
    try:
        response = requests.head(test['url'], headers=headers, timeout=10, allow_redirects=True)
        status = response.status_code
        status_text = {
            200: '✓ OK',
            301: '→ リダイレクト',
            302: '→ リダイレクト',
            400: '✗ 400 Bad Request',
            404: '✗ 404 Not Found',
            403: '✗ 403 Forbidden',
            500: '✗ 500 Server Error'
        }.get(status, f'✗ {status}')

        print(f"{status_text:20} | {test['name']:<25} | {test['url'][:60]}")
    except Exception as e:
        print(f"{'✗ ERROR':<20} | {test['name']:<25} | {str(e)[:40]}")

print("\n【調査結論】\n")
print("1. 現在の URL が 400 Bad Request を返している")
print("2. TSUTAYA のポケカ検索 URL の正確な形式が不明")
print("3. 代替案:")
print("   - TSUTAYA サイト全体をスキャンして正しい URL を特定")
print("   - または、TSUTAYA を無効化（0件状態は既に続いている）")
print("=" * 80)
