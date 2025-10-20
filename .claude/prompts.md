# Pokemon Card Lottery Tracker - Claude Code Instructions

⚠️ **重要**: このプロジェクトは `/Users/r.umeyama/work/.claude/CLAUDE.md` の共通ルールに従います。
特に **README更新ルール** を必ず確認してください。

このプロジェクトは、ポケモンカード抽選情報を自動収集するシステムです。

## 🔧 技術的な注意事項

### GitHub Actions
- タイムアウト: 15分以内に完了する必要がある
- スケジュール: 毎日9:00 JST (0:00 UTC)
- メール通知: SMTP設定が必要（詳細は親ディレクトリの.claude/CLAUDE.md参照）

### スクレイピング
- **在庫チェック機能**: 現在は無効化（処理時間の問題）
- **除外サイト**: Amazon, Yahoo, 駿河屋, エディオン
- **タイムアウト設定**: 全HTTPリクエストは30秒

### データフォーマット
- JSON形式で保存
- `data/all_lotteries.json`: 統合データ
- `data/lottery_report.html`: HTMLレポート


## ⚠️ よくある問題と対処法

### GitHub Actions タイムアウト
- 原因: 在庫チェックによる処理時間増加
- 対処: `check_availability=False`に設定

### HTMLレポート生成エラー
- 原因: `lotteries`キーがないデータソース
- 対処: `.get('lotteries', [])`を使用

### エディオン 403エラー
- 原因: Bot protection
- 対処: 除外リストに追加済み
