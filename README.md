# ポケモンカード抽選情報トラッカー

ポケモンカードの抽選販売情報を自動収集するシステムです。

## 🎯 機能

- **自動情報収集**: 主要サイトから抽選・予約情報を定期的にスクレイピング
- **重複除外**: 同じ商品の重複エントリを自動削除
- **変更検出**: 新しい抽選・予約の開始や終了を自動検出
- **予約開始通知**: Amazon・楽天ブックスの予約開始を即座に検知
- **GitHub Actions**: 1日4回自動実行（9:00, 12:00, 18:00, 21:00 JST）
- **メール通知**: 新しい抽選・予約情報が見つかった場合に自動通知
- **データ保存**: JSON形式で履歴を保存

## 📊 収集元

### 抽選情報

1. **入荷Now** (https://nyuka-now.com)
   - 最も網羅的な抽選情報集約サイト
   - 複数店舗の情報を一括取得
   - ⚠️ Amazon、Yahoo!ショッピング、駿河屋、エディオンは除外（在庫管理の都合）

2. **楽天ブックス** (https://books.rakuten.co.jp)
   - 抽選販売ページから直接取得
   - 信頼性の高いオンライン抽選情報

3. **ポケモンセンターオンライン公式**
   - 公式の抽選販売情報
   - 最も信頼性の高い情報源

### 予約情報

4. **Amazon.co.jp**
   - ポケモンカード予約商品を検索
   - 予約受付中の商品を自動検知
   - ASIN（商品ID）による重複除外

5. **楽天ブックス（予約）**
   - ポケモンカード予約商品を検索
   - 発売日情報と予約状態を取得
   - 在庫状況をリアルタイムチェック

6. **ヨドバシカメラ** (https://limited.yodobashi.com)
   - 抽選販売ページからポケモンカード関連情報を取得
   - 受付中・終了・予定などのステータスを検出

7. **ビックカメラ** (https://www.biccamera.com)
   - 抽選販売ページからポケモンカード関連情報を取得
   - 複数の抽選関連ページを監視

8. **X (Twitter) 公式アカウント**
   - ゲオ、TSUTAYA、ヨドバシカメラ等の公式アカウントを監視
   - 抽選・予約関連のツイートを自動検出
   - ※X API認証情報が必要

### 家電量販店

9. **ジョーシン** (https://joshinweb.jp)
   - 抽選・予約販売ページを監視
   - ポケモンカード関連商品を自動検出

10. **エディオン** (https://www.edion.com)
    - 抽選販売・イベントページを監視

11. **ケーズデンキ** (https://www.ksdenki.co.jp)
    - オンラインショップの抽選・予約情報を取得

12. **ノジマオンライン** (https://online.nojima.co.jp)
    - 予約・抽選販売情報を監視

### ホビーショップ

13. **あみあみ** (https://www.amiami.jp)
    - ポケモンカード予約商品を検索
    - 予約状態・価格情報を取得

14. **イエローサブマリン** (https://www.yellowsubmarine.co.jp)
    - トレカ新入荷・予約情報ページを監視

15. **カードショップセラ** (https://www.cardshopserra.jp)
    - トレカ専門店の予約情報を取得

### コンビニ・小売

16. **セブンネットショッピング** (https://7net.omni7.jp)
    - ポケモンカード予約・新発売商品を検索

17. **ローソン HMV** (https://www.hmv.co.jp)
    - HMV&BOOKS onlineの予約情報を取得

18. **イオンスタイルオンライン** (https://www.aeonnetshop.com)
    - ポケモンカード予約・販売情報を取得

19. **ファミリーマート** (https://www.family.co.jp)
    - キャンペーン・ホビー情報ページを監視

## 🚀 使い方

### ローカルで実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# スクレイピング実行
python main.py
```

### GitHub Actionsで自動実行

1. このリポジトリをGitHubにプッシュ
2. GitHub Actionsが自動的に有効化されます
3. スケジュール実行: 毎日9:00 JST
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
├── main.py                               # メインスクリプト
├── notify.py                             # メール通知機能
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

- `X_BEARER_TOKEN`: X API Bearer Token（推奨）
- または以下の組み合わせ：
  - `X_API_KEY`: API Key
  - `X_API_SECRET`: API Secret
  - `X_ACCESS_TOKEN`: Access Token
  - `X_ACCESS_TOKEN_SECRET`: Access Token Secret

※X API認証情報がない場合でも、他のスクレイパーは正常に動作します

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

- [x] メール通知機能
- [x] 重複除外機能
- [x] Amazon予約情報の収集
- [x] 楽天ブックス予約情報の収集
- [x] HTMLレポート生成機能
- [ ] 在庫チェック機能の再実装（高速化・並列処理）
- [ ] 実店舗抽選情報の収集（東京・神奈川・千葉・埼玉）
- [ ] 再入荷アラート機能
- [ ] 地域フィルタリング機能（関東圏のみ）
- [ ] 通知の優先度設定（定価 > 抽選 > 予約）
- [ ] Discord/Slack通知機能
- [ ] LINE通知機能
- [x] ヨドバシカメラ対応
- [x] ビックカメラ対応
- [x] X(Twitter)公式アカウント監視
- [x] 家電量販店対応（ジョーシン、エディオン、ケーズデンキ、ノジマ）
- [x] ホビーショップ対応（あみあみ、イエローサブマリン、カードショップセラ）
- [x] コンビニ・小売対応（セブン、ローソンHMV、イオン、ファミマ）
- [ ] Webダッシュボード

## ⚠️ 注意事項

- スクレイピング対象サイトの利用規約を遵守してください
- サーバーに負荷をかけないよう、適切な間隔で実行してください
- 収集した情報は個人利用の範囲でご使用ください

## 📜 ライセンス

MIT License

## 👤 作成者

RyoUmeyama
