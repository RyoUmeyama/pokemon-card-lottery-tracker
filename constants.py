"""
定数定義ファイル
全scraperで共通して使用する定数を集約
"""

# ポケモンカード関連キーワード
POKEMON_KEYWORDS = [
    'ポケモンカード', 'ポケカ', 'pokemon card', 'pokemon tcg',
    'ポケモン カード', 'ポケモンtcg',
    'スカーレット', 'バイオレット', 'テラスタル',
    'バトルマスター', 'シャイニートレジャー',
    'サイバージャッジ', 'ワイルドフォース',
    'クリムゾンヘイズ', 'ステラミラクル',
    'レイジングサーフ', 'ナイトワンダラー',
    '変幻の仮面', 'プロモカード',
    'ポケセン', 'トレカ',
]

# 除外キーワード（ポケモンカード以外の商品を除外）
EXCLUDE_KEYWORDS = [
    'ぬいぐるみ', 'フィギュア', 'ギフト', 'Tシャツ', 'アパレル',
    'ハイキュー', '一番くじ', 'グッズセット', 'ミスド', 'クッション',
    'タオル', 'バッグ', 'ポーチ', '母の日', 'スリッパ', 'パジャマ',
    'キーホルダー', 'ストラップ', 'マグカップ', 'お菓子', 'お弁当',
]

# User-Agent リスト（Playwright用、2026年版Chrome対応）
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
]

# デフォルトHTTPヘッダー（Playwright context用）
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

# タイムアウト設定（ミリ秒）
DEFAULT_TIMEOUT = 60000  # ページロード: 60秒
DEFAULT_NAVIGATION_TIMEOUT = 45000  # ナビゲーション: 45秒
