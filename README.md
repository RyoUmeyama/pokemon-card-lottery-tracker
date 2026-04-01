# ポケモンカード抽選情報トラッカー

ポケモンカードの抽選販売情報を自動収集するシステムです。

## 🎯 機能

- **自動情報収集**: 主要サイトから抽選・予約情報を定期的にスクレイピング
- **重複除外**: 同じ商品の重複エントリを自動削除
- **変更検出**: 新しい抽選・予約の開始や終了を自動検出（複合キー比較）
- **予約開始通知**: Amazon・楽天ブックスの予約開始を即座に検知
- **0件アラート**: スクレイパー異常時に警告ログとメール警告を出力
- **GitHub Actions**: 1日4回自動実行（9:00, 12:00, 18:00, 21:00 JST）
- **メール通知**: 新しい抽選・予約情報が見つかった場合に自動通知
- **メール拡張表示**: 期限間近15件、先着販売15件、抽選情報15件を表示
- **データ保存**: JSON形式で履歴を保存
- **ログ出力**: logs/ に日付別ログを出力（5MB rotate, 最大3世代）

## 📊 収集元

**稼働中スクレイパー**: 12ソース（詳細は config/scrapers.yaml 参照）
**skip設定**: 13ソース（WAF/接続失敗/ログイン認証必須）
**テスト**: 106テスト全て成功（cmd_250時点）

### アクティブスクレイパー（12ソース）

| # | スクレイパー | URL | タイプ | 状態 |
|----|-------------|-----|--------|------|
| 1 | 楽天ブックス | books.rakuten.co.jp | 抽選 | ✅ |
| 5 | Amazon | amazon.co.jp | 予約 | ✅ |
| 6 | 楽天ブックス予約 | books.rakuten.co.jp | 予約 | ✅ |
| 9 | X (Twitter) | twitter.com | 情報源 | ✅ |
| 13 | ノジマ | nojima.co.jp | 予約 | ✅ |
| 15 | イエローサブマリン | yellowsubmarine.co.jp | 予約 | ✅ |
| 16 | カードショップセラ | cardshopserra.jp | 予約 | ✅ |
| 17 | セブンネットショッピング | 7net.omni7.jp | 予約 | ✅ |
| 19 | ローソンHMV | hmv.co.jp | 予約 | ✅ |
| 21 | ファミリーマート | family.co.jp | 情報源 | ✅ |
| 22 | 駿河屋 | surugaya.co.jp | 予約 | ✅ |
| 23 | GEO | geo-online.co.jp | 予約 | ✅ |

### skip設定のスクレイパー（13ソース）

以下のスクレイパーは `config/scrapers.yaml` で `skip: true` に設定されており、実行時にスキップされます。修復困難なため、アクティブな12ソースで主要な情報をカバーしています。

| # | スクレイパー | 理由 |
|---|-------------|------|
| 3 | ポケモンセンター公式 | ログイン認証 + SPA（API非公開） |
| 4 | ポケモンセンター公式(Playwright) | WAF完全ブロック（403） |
| 7 | ヨドバシカメラ | サイト受付終了（最新抽選なし） |
| 8 | ビックカメラ | Timeout（接続不安定） |
| 10 | ジョーシン | Timeout（接続不安定） |
| 11 | エディオン | JavaScript実行環境必須 |
| 12 | ケーズデンキ | URL無効（サイト構造変更） |
| 14 | あみあみ | スコープ外（サプライ品中心） |
| 18 | セブンネット抽選(Playwright) | WAF完全ブロック |
| 20 | イオン | ポケモンカード関連コンテンツなし |
| 24 | TSUTAYA | 404エラー（提供終了） |
| 25 | Google Forms抽選 | フォーム作成者確認必要 |
| 26 | ドラゴンスター | データ精度問題 |

## 🚀 使い方

### ローカルで実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# スクレイピング実行（タイムアウト推奨値: 15分）
python main.py

# テスト実行（cmd_248で46テスト全て成功）
python3 -m pytest tests/          # 全テスト実行（46テスト）
python3 -m pytest tests/ -v       # 詳細表示
python3 -m pytest tests/test_main.py::TestDetectChanges -v  # 特定テストのみ実行
```

### ログ出力

実行ログは `logs/` ディレクトリに日付別に保存されます：

```bash
logs/
├── scraping_20260101.log     # 2026-01-01のログ
├── scraping_20260102.log     # 2026-01-02のログ
└── ...

# ログサイズが5MBに達すると自動的にローテーション（最大3世代保持）
```

ログレベル：INFO（デフォルト）、WARNING（異常検出時）、CRITICAL（全スクレイパー0件時）

### GitHub Actionsで自動実行

1. このリポジトリをGitHubにプッシュ
2. GitHub Actionsが自動的に有効化されます
3. スケジュール実行: 1日4回（9:00, 12:00, 18:00, 21:00 JST）
4. 手動実行: Actionsタブから「Run workflow」をクリック

## 📁 プロジェクト構造

```
pokemon-card-lottery-tracker/
├── scrapers/
│   ├── __init__.py
│   ├── nyuka_now_scraper.py              # 入荷Nowスクレイパー
│   ├── pokemon_center_scraper.py         # ポケモンセンター公式スクレイパー
│   ├── rakuten_books_scraper.py          # 楽天ブックス抽選スクレイパー
│   ├── amazon_reservation_scraper.py     # Amazon予約スクレイパー
│   ├── rakuten_reservation_scraper.py    # 楽天ブックス予約スクレイパー
│   ├── yodobashi_scraper.py              # ヨドバシカメラスクレイパー
│   ├── biccamera_scraper.py              # ビックカメラスクレイパー
│   ├── x_lottery_scraper.py              # X(Twitter)公式アカウントスクレイパー
│   ├── joshin_scraper.py                 # ジョーシンスクレイパー
│   ├── edion_scraper.py                  # エディオンスクレイパー
│   ├── ksdenki_scraper.py                # ケーズデンキスクレイパー
│   ├── nojima_scraper.py                 # ノジマスクレイパー
│   ├── amiami_scraper.py                 # あみあみスクレイパー
│   ├── yellow_submarine_scraper.py       # イエローサブマリンスクレイパー
│   ├── cardshop_serra_scraper.py         # カードショップセラスクレイパー
│   ├── seven_eleven_scraper.py           # セブンネットスクレイパー
│   ├── lawson_scraper.py                 # ローソンHMVスクレイパー
│   ├── aeon_scraper.py                   # イオンスクレイパー
│   └── familymart_scraper.py             # ファミリーマートスクレイパー
├── data/
│   ├── nyuka_now_latest.json             # 入荷Now最新データ
│   ├── pokemon_center_latest.json        # ポケモンセンター最新データ
│   ├── rakuten_books_latest.json         # 楽天ブックス抽選最新データ
│   ├── amazon_reservation_latest.json    # Amazon予約最新データ
│   ├── rakuten_reservation_latest.json   # 楽天ブックス予約最新データ
│   ├── yodobashi_latest.json             # ヨドバシカメラ最新データ
│   ├── biccamera_latest.json             # ビックカメラ最新データ
│   ├── x_lottery_latest.json             # X(Twitter)最新データ
│   ├── joshin_latest.json                # ジョーシン最新データ
│   ├── edion_latest.json                 # エディオン最新データ
│   ├── ksdenki_latest.json               # ケーズデンキ最新データ
│   ├── nojima_latest.json                # ノジマ最新データ
│   ├── amiami_latest.json                # あみあみ最新データ
│   ├── yellow_submarine_latest.json      # イエローサブマリン最新データ
│   ├── cardshop_serra_latest.json        # カードショップセラ最新データ
│   ├── seven_eleven_latest.json          # セブンネット最新データ
│   ├── lawson_latest.json                # ローソンHMV最新データ
│   ├── aeon_latest.json                  # イオン最新データ
│   ├── familymart_latest.json            # ファミリーマート最新データ
│   └── all_lotteries.json                # 統合データ
├── .github/
│   └── workflows/
│       └── scrape.yml                    # GitHub Actions設定
├── logs/
│   └── scraping_YYYYMMDD.log            # 日付別実行ログ
├── config/
│   └── scrapers.yaml                     # スクレイパー設定
├── scripts/
│   └── verify_urls.py                    # URL検証スクリプト
├── tests/
│   ├── test_main.py                      # メイン処理テスト
│   ├── test_utils.py                     # ユーティリティテスト
│   └── test_scrapers.py                  # スクレイパーテスト
├── main.py                               # メインスクリプト（スクレイピング統合処理）
├── notify.py                             # メール通知機能
├── constants.py                          # 定数定義（キーワード、User-Agent等）【cmd_247新規追加】
├── utils.py                              # ユーティリティ関数【cmd_247新規追加】
│   ├── _parse_date_flexible()            # 日付パース（多様な形式対応）
│   ├── _extract_year_from_string()       # 年号抽出
│   └── build_composite_key()             # 複合キー生成
├── generate_html_report.py               # HTMLレポート生成【cmd_247p2: テーブル+ソート機能追加】
├── requirements.txt                      # Python依存関係
└── README.md
```

## 📝 データ形式

### all_lotteries.json

```json
{
  "timestamp": "2025-10-08T10:00:00",
  "sources": [
    {
      "source": "nyuka-now.com",
      "scraped_at": "2025-10-08T10:00:00",
      "lotteries": [
        {
          "store": "イエローサブマリン",
          "product": "インフェルノX",
          "period": "10/6～10/13",
          "status": "active"
        }
      ]
    }
  ]
}
```

## 📧 メール通知設定

抽選情報が見つかったときにメールで通知を受け取ることができます。

### GitHub Secretsの設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定：

- `SMTP_SERVER`: SMTPサーバー（例: smtp.gmail.com）
- `SMTP_PORT`: SMTPポート（例: 587）
- `SMTP_USERNAME`: SMTPユーザー名（メールアドレス）
- `SMTP_PASSWORD`: SMTPパスワード（Gmailの場合はアプリパスワード）
- `RECIPIENT_EMAIL`: 通知先メールアドレス

### X (Twitter) API認証（オプション）

X(Twitter)からの情報収集を有効にする場合は追加で設定：

**推奨方法（Bearer Token）：**
- `X_BEARER_TOKEN`: X API Bearer Token（推奨）

**代替方法（OAuth1.0a）：**
- `X_API_KEY`: API Key
- `X_API_SECRET`: API Secret
- `X_ACCESS_TOKEN`: Access Token
- `X_ACCESS_TOKEN_SECRET`: Access Token Secret

**注：** X API認証情報がない場合でも、他のスクレイパー（19ソース）は正常に動作します

### Gmailの場合のアプリパスワード取得

1. Googleアカウントにログイン
2. https://myaccount.google.com/apppasswords にアクセス
3. アプリパスワードを生成（「メール」「その他」を選択）
4. 生成された16桁のパスワードを `SMTP_PASSWORD` に設定

### ローカルでテスト

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="recipient@gmail.com"
python main.py
```

## 🔔 今後の拡張予定

### 実装済み
- [x] メール通知機能
- [x] 重複除外機能（複合キー対応）
- [x] Amazon予約情報の収集（修復済み）
- [x] 楽天ブックス予約情報の収集
- [x] HTMLレポート生成機能
- [x] 変更検出機能（複合キー比較）
- [x] 0件アラート機能
- [x] メール拡張表示（期限間近15件、先着販売15件等）
- [x] ログ出力機能（logs/, RotatingFileHandler対応）
- [x] テストスイート（46テスト）
- [x] ヨドバシカメラ対応
- [x] ビックカメラ対応
- [x] X(Twitter)公式アカウント監視
- [x] 家電量販店対応（ジョーシン、エディオン、ケーズデンキ、ノジマ）
- [x] ホビーショップ対応（あみあみ、イエローサブマリン、カードショップセラ）
- [x] コンビニ・小売対応（セブン、ローソンHMV、イオン、ファミマ）
- [x] コード品質改善（PEP8準拠 import、DeprecationWarning対応）【cmd_247】
- [x] utils.py作成（共通ユーティリティ関数集約）【cmd_247】
- [x] constants.py作成（キーワード・User-Agent定義）【cmd_247】
- [x] async並列化スクレイピング（asyncio.gather()）【cmd_247】
- [x] ログレベル・出力機能強化（WARNING/CRITICAL対応）【cmd_247】
- [x] メール件名ステータスサマリー追加（「🆕新着X件 / 🔥期限間近Y件」）【cmd_247】
- [x] メール表示件数引き上げ（期限15件, 先着10件, 抽選8件, 予約8件, 予定15件）【cmd_247】
- [x] 受付終了ロッテリー自動除外フィルタ（_create_email_body()）【cmd_247】
- [x] HTMLレポートにテーブル＋ソート機能追加【cmd_247】
  - テーブル形式での表示（店舗名/商品名/締切日/ステータス/抽選形式）
  - ヘッダクリックでソート切り替え（昇順/降順）
  - ドロップダウンセレクタでソート切り替え（期限順/店舗名順/新着順）
  - デフォルト: 締切日昇順（近い順）
  - 新着バッジ機能（24時間以内の新規追加を表示）
- [x] ステータスバッジ実装（「受付中」「受付終了」「予定」「新着」）【cmd_247】
  - CSS パルスアニメーション（新着表示）
  - ステータス別色分け（アクティブ/終了/予定）
- [x] モバイル対応改善（CSS media queries）【cmd_247】

### 今後の実装予定
- [ ] 在庫チェック機能の再実装（高速化・並列処理）
- [ ] 実店舗抽選情報の収集（東京・神奈川・千葉・埼玉）
- [ ] 再入荷アラート機能
- [ ] 地域フィルタリング機能（関東圏のみ）
- [ ] 通知の優先度設定（定価 > 抽選 > 予約）
- [ ] Discord/Slack通知機能
- [ ] LINE通知機能
- [ ] Webダッシュボード
- [ ] Playwright版スクレイパーの復活

## ⚠️ 注意事項

- スクレイピング対象サイトの利用規約を遵守してください
- サーバーに負荷をかけないよう、適切な間隔で実行してください
- 収集した情報は個人利用の範囲でご使用ください

## 📜 ライセンス

MIT License

## 👤 作成者

RyoUmeyama
