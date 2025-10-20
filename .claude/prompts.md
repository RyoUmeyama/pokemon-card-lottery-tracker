# Pokemon Card Lottery Tracker - Claude Code Instructions

このプロジェクトは、ポケモンカード抽選情報を自動収集するシステムです。

## 📋 README更新ルール（重要）

**コードに変更を加えた場合、必ずREADME.mdを更新してください。**

### 更新が必要な場合
- 新機能の追加
- 既存機能の変更・削除
- 実行スケジュールの変更
- 収集元サイトの追加・除外
- 設定方法の変更

### 更新すべきセクション
- `## 🎯 機能`: 機能の追加・削除
- `## 📊 収集元`: データソース・除外サイトの変更
- `## 🔔 今後の拡張予定`: 完了した機能にチェックマークを追加

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

## 📧 メール通知設定

GitHub Secretsで以下を設定:
- `SMTP_SERVER`: smtp.gmail.com
- `SMTP_PORT`: 587
- `SMTP_USERNAME`: 完全なGmailアドレス（@gmail.com含む）
- `SMTP_PASSWORD`: Gmailアプリパスワード（16文字、スペースなし）
- `RECIPIENT_EMAIL`: 通知先メールアドレス

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
