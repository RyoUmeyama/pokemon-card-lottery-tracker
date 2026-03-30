"""
Scrapers package

ポケモンカード抽選・予約情報を収集するスクレイパーの集約モジュール。
各スクレイパーは、特定のサイトから以下の情報を取得します：

- 抽選情報（product, store, lottery_type, start_date, end_date, conditions等）
- 予約情報（title, price, availability_date等）

各スクレイパーの種類：
- HTML/CSS系: BeautifulSoup、requests等を使用した静的スクレイピング
- Playwright系: ブラウザ自動化によるJavaScript実行後のデータ取得
- API系: サイトのAPI directly呼び出し

スクレイパーの実装パターン：
1. 基本クラス（PlaywrightBase等）を継承
2. __init__で初期化（URLs等）
3. scrapeメソッドで情報取得
4. 返り値: Dict[str, Any]形式（timestamp, lotteries/reservations リスト等）
"""
