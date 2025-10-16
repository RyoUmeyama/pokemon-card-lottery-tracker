"""
Gmail通知機能
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime


class GmailNotifier:
    def __init__(self):
        # 環境変数から認証情報を取得（SMTP設定）
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '465'))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.recipient = os.environ.get('RECIPIENT_EMAIL')

    def send_notification(self, all_lotteries_data):
        """抽選情報をメールで通知"""
        if not self.smtp_username or not self.smtp_password or not self.recipient:
            print("⚠️ SMTP認証情報が設定されていません")
            print("環境変数 SMTP_USERNAME, SMTP_PASSWORD, RECIPIENT_EMAIL を設定してください")
            return False

        # 抽選情報を集計
        total_lottery_count = 0
        total_reservation_count = 0
        sources_summary = []

        for source in all_lotteries_data.get('sources', []):
            lottery_count = len(source.get('lotteries', []))
            reservation_count = len(source.get('reservations', []))
            total_lottery_count += lottery_count
            total_reservation_count += reservation_count

            if lottery_count > 0 or reservation_count > 0:
                source_name = source.get('source', 'Unknown')
                sources_summary.append({
                    'name': source_name,
                    'lottery_count': lottery_count,
                    'reservation_count': reservation_count,
                    'lotteries': source.get('lotteries', []),
                    'reservations': source.get('reservations', [])
                })

        # 抽選も予約もない場合は通知しない
        if total_lottery_count == 0 and total_reservation_count == 0:
            print("📭 抽選・予約情報がないため通知をスキップします")
            return True

        # メール本文を作成
        email_body = self._create_email_body(sources_summary, total_lottery_count, total_reservation_count)

        # メールを送信
        try:
            msg = MIMEMultipart('alternative')
            subject_parts = []
            if total_lottery_count > 0:
                subject_parts.append(f'抽選{total_lottery_count}件')
            if total_reservation_count > 0:
                subject_parts.append(f'予約{total_reservation_count}件')
            msg['Subject'] = f'🎴 ポケモンカード情報 ({", ".join(subject_parts)}) - {datetime.now().strftime("%Y/%m/%d")}'
            msg['From'] = self.smtp_username
            msg['To'] = self.recipient

            # HTML版
            html_part = MIMEText(email_body, 'html')
            msg.attach(html_part)

            # SMTPサーバーに接続して送信
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

            print(f"✅ メール通知を送信しました: {self.recipient}")
            return True

        except Exception as e:
            print(f"❌ メール送信エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_email_body(self, sources_summary, total_lottery_count, total_reservation_count):
        """メール本文（HTML）を作成"""
        summary_parts = []
        if total_lottery_count > 0:
            summary_parts.append(f'{total_lottery_count}件の抽選情報')
        if total_reservation_count > 0:
            summary_parts.append(f'{total_reservation_count}件の予約情報')

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }}
        .source-section {{
            margin-bottom: 30px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            background: #f7fafc;
        }}
        .source-header {{
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .lottery-item {{
            background: white;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .reservation-item {{
            background: white;
            border-left: 4px solid #48bb78;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .product-name {{
            font-size: 16px;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }}
        .store-name {{
            color: #718096;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .price {{
            color: #38a169;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .availability {{
            color: #48bb78;
            font-size: 14px;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        .detail-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 15px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
        }}
        .detail-link:hover {{
            background: #5568d3;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #2d3748;
            margin: 20px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
            text-align: center;
            color: #718096;
            font-size: 14px;
        }}
        .view-all-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎴 ポケモンカード情報</h1>

        <div class="summary">
            {'と'.join(summary_parts)}
        </div>
"""

        # 各ソースの情報を追加
        for source in sources_summary:
            source_count_parts = []
            if source['lottery_count'] > 0:
                source_count_parts.append(f'抽選{source["lottery_count"]}件')
            if source['reservation_count'] > 0:
                source_count_parts.append(f'予約{source["reservation_count"]}件')

            html += f"""
        <div class="source-section">
            <div class="source-header">
                <span>📌 {source['name']}</span>
                <span style="color: #667eea;">{', '.join(source_count_parts)}</span>
            </div>
"""

            # 抽選情報を追加（最大5件まで表示）
            if source['lottery_count'] > 0:
                html += """
            <div class="section-title">🎯 抽選情報</div>
"""
                for lottery in source['lotteries'][:5]:
                    store = lottery.get('store', '')
                    product = lottery.get('product', '')
                    detail_url = lottery.get('detail_url', '#')

                    html += f"""
            <div class="lottery-item">
                <div class="store-name">🏪 {store}</div>
                <div class="product-name">📦 {product}</div>
                <a href="{detail_url}" class="detail-link" target="_blank">🔗 詳細を見る</a>
            </div>
"""

                # 5件以上ある場合は省略メッセージ
                if len(source['lotteries']) > 5:
                    remaining = len(source['lotteries']) - 5
                    html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""

            # 予約情報を追加（最大5件まで表示）
            if source['reservation_count'] > 0:
                html += """
            <div class="section-title">📅 予約情報</div>
"""
                for reservation in source['reservations'][:5]:
                    title = reservation.get('title', '')
                    price = reservation.get('price', '')
                    availability = reservation.get('availability', '')
                    url = reservation.get('url', '#')
                    release_date = reservation.get('release_date', '')

                    html += f"""
            <div class="reservation-item">
                <div class="product-name">📦 {title}</div>
                <div class="price">💰 {price}</div>
                <div class="availability">✅ {availability}</div>
"""
                    if release_date:
                        html += f"""
                <div class="store-name">📅 {release_date}</div>
"""
                    html += f"""
                <a href="{url}" class="detail-link" target="_blank">🔗 予約ページを見る</a>
            </div>
"""

                # 5件以上ある場合は省略メッセージ
                if len(source['reservations']) > 5:
                    remaining = len(source['reservations']) - 5
                    html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""

            html += """
        </div>
"""

        # フッター
        html += f"""
        <div class="footer">
            <p>🤖 自動収集システムより</p>
            <p>最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            <a href="https://htmlpreview.github.io/?https://github.com/RyoUmeyama/pokemon-card-lottery-tracker/blob/main/data/lottery_report.html"
               class="view-all-link" target="_blank">
                📊 すべての抽選情報を見る
            </a>
        </div>
    </div>
</body>
</html>
"""

        return html


if __name__ == '__main__':
    # テスト実行
    notifier = GmailNotifier()

    # all_lotteries.jsonを読み込んで通知
    with open('data/all_lotteries.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    notifier.send_notification(data)
