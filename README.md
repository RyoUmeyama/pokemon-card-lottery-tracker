# ポケモンカード抽選情報トラッカー

ポケモンカードの抽選販売情報を自動収集するシステムです。

## 🎯 機能

- **自動情報収集**: 主要サイトから抽選情報を定期的にスクレイピング
- **変更検出**: 新しい抽選の開始や終了を自動検出
- **GitHub Actions**: 1日3回（9時、12時、18時）自動実行
- **データ保存**: JSON形式で履歴を保存

## 📊 収集元

1. **入荷Now** (https://nyuka-now.com)
   - 最も網羅的な抽選情報集約サイト
   - 複数店舗の情報を一括取得

2. **ポケモンセンターオンライン公式**
   - 公式の抽選販売情報
   - 最も信頼性の高い情報源

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
3. スケジュール実行: 毎日9:00、12:00、18:00 (JST)
4. 手動実行: Actionsタブから「Run workflow」をクリック

## 📁 プロジェクト構造

```
pokemon-card-lottery-tracker/
├── scrapers/
│   ├── __init__.py
│   ├── nyuka_now_scraper.py       # 入荷Nowスクレイパー
│   └── pokemon_center_scraper.py  # ポケモンセンター公式スクレイパー
├── data/
│   ├── nyuka_now_latest.json      # 入荷Now最新データ
│   ├── pokemon_center_latest.json # ポケモンセンター最新データ
│   └── all_lotteries.json         # 統合データ
├── .github/
│   └── workflows/
│       └── scrape.yml             # GitHub Actions設定
├── main.py                        # メインスクリプト
├── requirements.txt               # Python依存関係
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

## 🔔 今後の拡張予定

- [ ] Discord/Slack通知機能
- [ ] LINE通知機能
- [ ] メール通知機能
- [ ] より多くのサイトに対応
- [ ] Webダッシュボード

## ⚠️ 注意事項

- スクレイピング対象サイトの利用規約を遵守してください
- サーバーに負荷をかけないよう、適切な間隔で実行してください
- 収集した情報は個人利用の範囲でご使用ください

## 📜 ライセンス

MIT License

## 👤 作成者

RyoUmeyama
