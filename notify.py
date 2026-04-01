"""
Gmail通知機能
"""
import json
import logging
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class GmailNotifier:
    def __init__(self):
        # 環境変数から認証情報を取得（SMTP設定）
        # 注意: SMTP_PORT 587 の場合は STARTTLS、465 の場合は SMTP_SSL を使用
        # SMTP_USE_SSL の設定を検討する場合は、send_notification メソッドを参照
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '465'))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.recipient = os.environ.get('RECIPIENT_EMAIL')

    def _parse_date(self, date_string):
        """日付文字列をdatetime オブジェクトに変換"""
        if not date_string or not isinstance(date_string, str):
            return None

        from datetime import datetime as dt
        formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']
        for fmt in formats:
            try:
                return dt.strptime(date_string, fmt)
            except ValueError:
                continue
        return None

    def _is_ended(self, end_date_str):
        """抽選が終了しているか判定（end_date < 今日）"""
        if not end_date_str:
            return False
        end_date = self._parse_date(end_date_str)
        if not end_date:
            return False
        return end_date.date() < datetime.now().date()

    def _days_until_deadline(self, end_date_str):
        """期限までの日数を計算（負なら既に終了）"""
        if not end_date_str:
            return None
        end_date = self._parse_date(end_date_str)
        if not end_date:
            return None
        delta = (end_date.date() - datetime.now().date()).days
        return delta

    def _is_deadline_soon(self, end_date_str, days=3):
        """期限が間近か判定（3日以内）"""
        days_left = self._days_until_deadline(end_date_str)
        if days_left is None:
            return False
        return 0 <= days_left <= days

    def send_notification(self, all_lotteries_data):
        """抽選情報をメールで通知"""
        if not self.smtp_username or not self.smtp_password or not self.recipient:
            logger.warning("⚠️ SMTP認証情報が設定されていません")
            logger.warning("環境変数 SMTP_USERNAME, SMTP_PASSWORD, RECIPIENT_EMAIL を設定してください")
            return False

        # 抽選情報を集計（受付終了済みを除外）
        total_lottery_count = 0
        total_reservation_count = 0
        total_first_come_first_served = 0
        total_upcoming = 0
        sources_summary = []
        first_come_first_served_items = []
        deadline_soon_items = []  # 期限間近（3日以内）
        upcoming_products = all_lotteries_data.get('upcoming_products', [])

        for source in all_lotteries_data.get('sources', []):
            # 受付終了済みを除外したロッテリーをフィルタ
            filtered_lotteries = [
                item for item in source.get('lotteries', [])
                if not self._is_ended(item.get('end_date', ''))
            ]

            lottery_count = len(filtered_lotteries)
            reservation_count = len(source.get('reservations', []))
            total_lottery_count += lottery_count
            total_reservation_count += reservation_count

            # 先着販売中の商品を抽出（受付終了済みを除外）
            fcfs_items = [item for item in filtered_lotteries if item.get('first_come_first_served')]
            total_first_come_first_served += len(fcfs_items)
            first_come_first_served_items.extend(fcfs_items)

            # 期限間近（3日以内）を抽出
            deadline_soon = [item for item in filtered_lotteries if self._is_deadline_soon(item.get('end_date', ''))]
            deadline_soon_items.extend(deadline_soon)

            # 各ソースの upcoming_products を集約
            source_upcoming = source.get('upcoming_products', [])
            if source_upcoming:
                upcoming_products.extend(source_upcoming)
                total_upcoming += len(source_upcoming)

            if lottery_count > 0 or reservation_count > 0:
                source_name = source.get('source', 'Unknown')
                sources_summary.append({
                    'name': source_name,
                    'lottery_count': lottery_count,
                    'reservation_count': reservation_count,
                    'lotteries': filtered_lotteries,  # 受付終了済みを除外したもの
                    'reservations': source.get('reservations', [])
                })

        # 抽選も予約もない場合は通知しない
        if total_lottery_count == 0 and total_reservation_count == 0:
            logger.info("📭 抽選・予約情報がないため通知をスキップします")
            return True

        total_upcoming = len(upcoming_products)

        # 新着件数と期限間近件数をカウント
        all_lotteries_flat = []
        for source in sources_summary:
            all_lotteries_flat.extend(source.get('lotteries', []))
        new_items_count = sum(1 for item in all_lotteries_flat if self._is_new(item.get('timestamp', '')))
        deadline_soon_count = len(deadline_soon_items)

        # メール本文を作成（期限間近データを最上部に表示）
        email_body = self._create_email_body(
            sources_summary,
            total_lottery_count,
            total_reservation_count,
            first_come_first_served_items,
            upcoming_products,
            deadline_soon_items,
            zero_alert=zero_alert,
            zero_alert_sources=all_lotteries_data.get('zero_alert_sources', [])
        )

        # メールを送信（リトライ機能付き: exponential backoff 2s, 4s, 8s）
        msg = MIMEMultipart('alternative')
        subject_parts = []

        # 0件アラート判定
        zero_alert = all_lotteries_data.get('zero_alert', False)

        if zero_alert:
            subject_parts.append('⚠️0件')

        # ステータスサマリーを先頭に追加
        if new_items_count > 0:
            subject_parts.append(f'🆕新着{new_items_count}件')
        if deadline_soon_count > 0:
            subject_parts.append(f'🔥期限間近{deadline_soon_count}件')

        if total_lottery_count > 0:
            subject_parts.append(f'抽選{total_lottery_count}件')
        if total_reservation_count > 0:
            subject_parts.append(f'予約{total_reservation_count}件')
        if total_upcoming > 0:
            subject_parts.append(f'{total_upcoming}件予定')

        # 合計件数を計算
        total_count = total_lottery_count + total_reservation_count + total_upcoming
        subject_date = datetime.now().strftime("%Y/%m/%d")
        msg['Subject'] = (
            f'🎴 ポケモンカード情報 (全{total_count}件 / {" / ".join(subject_parts)}) - {subject_date}'
        )
        msg['From'] = self.smtp_username
        msg['To'] = self.recipient

        # HTML版
        html_part = MIMEText(email_body, 'html')
        msg.attach(html_part)

        # リトライ（最大3回）
        max_retries = 3
        backoff_times = [2, 4, 8]  # 秒単位

        for attempt in range(max_retries):
            try:
                # SMTPサーバーに接続して送信
                if self.smtp_port == 465:
                    with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30) as server:
                        server.login(self.smtp_username, self.smtp_password)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                        server.starttls()
                        server.login(self.smtp_username, self.smtp_password)
                        server.send_message(msg)

                logger.info(f"✅ メール通知を送信しました: {self.recipient}")
                return True

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"❌ SMTP認証エラー（試行{attempt+1}/{max_retries}）: {e}")
                # 認証エラーはリトライしない
                return False

            except (smtplib.SMTPException, ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_times[attempt]
                    logger.warning(f"⚠️ メール送信エラー（試行{attempt+1}/{max_retries}）: {e}. {wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ メール送信が{max_retries}回失敗しました: {e}")
                    return False

            except Exception as e:
                logger.error(f"❌ 予期しないメール送信エラー（試行{attempt+1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    wait_time = backoff_times[attempt]
                    logger.info(f"ℹ️ {wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    return False

        return False

    def _is_new(self, item_timestamp):
        """アイテムが24時間以内に追加されたかチェック"""
        if not item_timestamp:
            return False
        try:
            from datetime import timedelta
            item_time = datetime.fromisoformat(item_timestamp)
            current_time = datetime.now()
            return (current_time - item_time) < timedelta(hours=24)
        except (ValueError, TypeError):
            return False

    def _is_active(self, start_date_str, end_date_str):
        """抽選が「受付中」かどうか判定"""
        if not end_date_str:
            return False
        # 受付終了していなければ受付中と判定
        return not self._is_ended(end_date_str)

    def _sort_lotteries_by_status(self, lotteries):
        """抽選を受付中優先でソート"""
        active = []
        inactive = []
        for lottery in lotteries:
            if self._is_active(lottery.get('start_date', ''), lottery.get('end_date', '')):
                active.append(lottery)
            else:
                inactive.append(lottery)
        return active + inactive

    def _create_email_body(self, sources_summary, total_lottery_count, total_reservation_count, first_come_first_served_items=None, upcoming_products=None, deadline_soon_items=None, zero_alert=False, zero_alert_sources=None):
        """メール本文（HTML）を作成"""
        if first_come_first_served_items is None:
            first_come_first_served_items = []
        if upcoming_products is None:
            upcoming_products = []
        if deadline_soon_items is None:
            deadline_soon_items = []
        if zero_alert_sources is None:
            zero_alert_sources = []

        # フィルタ: 各ソースのロッテリーから受付終了済みをさらに除外
        filtered_sources_summary = []
        sources_list = sources_summary.values() if isinstance(sources_summary, dict) else sources_summary
        for source in sources_list:
            filtered_source = {
                'name': source.get('name', 'Unknown'),
                'lottery_count': 0,
                'reservation_count': source.get('reservation_count', 0),
                'lotteries': [item for item in source.get('lotteries', []) if not self._is_ended(item.get('end_date', ''))],
                'reservations': source.get('reservations', [])
            }
            # ロッテリーが1件でもあれば、またはリザベーションがあれば含める
            if filtered_source['lotteries'] or filtered_source['reservations']:
                filtered_source['lottery_count'] = len(filtered_source['lotteries'])
                filtered_sources_summary.append(filtered_source)

        summary_parts = []
        # 合計件数を先頭に追加
        total_upcoming = len(upcoming_products) if upcoming_products else 0
        total_count = total_lottery_count + total_reservation_count + total_upcoming
        summary_parts.append(f'📊 全{total_count}件の情報')
        if len(deadline_soon_items) > 0:
            summary_parts.append(f'🔥期限間近{len(deadline_soon_items)}件')
        if total_lottery_count > 0:
            summary_parts.append(f'{total_lottery_count}件の抽選情報')
        if total_reservation_count > 0:
            summary_parts.append(f'{total_reservation_count}件の予約情報')
        if len(upcoming_products) > 0:
            summary_parts.append(f'{len(upcoming_products)}件の今後の発売予定')

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
        .deadline-highlight {{
            background-color: #fff5e6;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
        }}
        .badge-new {{
            background: #4CAF50;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            margin-left: 5px;
            display: inline-block;
        }}
        .detail-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 12px 24px;
            background: #ff6b6b;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        }}
        .detail-link:hover {{
            background: #ee5a5a;
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

        # 0件アラートセクション（最上部に表示）
        if zero_alert:
            html += """
        <div class="source-section" style="background: #ffe6e6; border-color: #ff0000; border-width: 3px;">
            <div class="section-title" style="color: #d32f2f; font-size: 20px;">⚠️ 警告: 全スクレイパーで0件</div>
            <div style="padding: 15px; background: #fff5f5; border-radius: 5px; margin-top: 10px;">
                <p style="color: #d32f2f; font-weight: bold;">データ取得に重大な問題の可能性があります。</p>
                <p style="color: #666;">スクレイパーのエラーまたはウェブサイトの大幅な変更が考えられます。</p>
            </div>
        </div>
"""
        elif zero_alert_sources:
            html += f"""
        <div class="source-section" style="background: #fff3cd; border-color: #ff9800;">
            <div class="section-title" style="color: #ff9800;">⚠️  以下のスクレイパーで0件</div>
            <div style="padding: 15px; background: #fffacd; border-radius: 5px; margin-top: 10px;">
                <p>{', '.join(zero_alert_sources)}</p>
            </div>
        </div>
"""

        # 期限間近セクション（最上部に表示）
        if deadline_soon_items:
            html += f"""
        <div class="source-section" style="background: #ffe6e6; border-color: #ff4444; border-width: 3px;">
            <div class="section-title" style="color: #d32f2f;">🔥 期限間近（3日以内） - 全{len(deadline_soon_items)}件</div>
"""
            for item in deadline_soon_items:
                product = item.get('product', '')
                store = item.get('store', '')
                end_date = item.get('end_date', '')
                days_left = self._days_until_deadline(end_date)
                days_text = f'あと{days_left}日' if days_left is not None else ''
                url = item.get('detail_url', '#')
                html += f"""
            <div class="lottery-item" style="border-left-color: #ff4444; background: #fff5f5;">
                <div class="store-name">🏪 {store}</div>
                <div class="product-name">📦 {product}</div>
                <div style="margin-top: 5px; color: #d32f2f; font-weight: bold;">⏰ 期限: {end_date} ({days_text})</div>
                <a href="{url}" class="detail-link" target="_blank">🔗 詳細を見る</a>
            </div>
"""
            if len(deadline_soon_items) > 15:
                remaining = len(deadline_soon_items) - 15
                html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""
            html += """
        </div>
"""

        # 先着販売中セクション（上限15件）
        if first_come_first_served_items:
            html += f"""
        <div class="source-section" style="background: #fffacd; border-color: #ffd700;">
            <div class="section-title" style="color: #d4af37;">🔥 先着販売中 - 全{len(first_come_first_served_items)}件</div>
"""
            for item in first_come_first_served_items[:15]:
                product = item.get('product', '')
                store = item.get('store', '')
                url = item.get('detail_url', '#')
                html += f"""
            <div class="lottery-item" style="border-left-color: #ffd700;">
                <div class="store-name">🏪 {store}</div>
                <div class="product-name">⚡ {product}</div>
                <a href="{url}" class="detail-link" target="_blank">🔗 今すぐ購入</a>
            </div>
"""
            if len(first_come_first_served_items) > 15:
                remaining = len(first_come_first_served_items) - 15
                html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""
            html += """
        </div>
"""

        # 各ソースの情報を追加（受付終了済みを除外したフィルタ済みデータを使用）
        for source in filtered_sources_summary:
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

            # 抽選情報を追加（上限15件、受付中優先でソート）
            if source['lottery_count'] > 0:
                html += f"""
            <div class="section-title">🎯 抽選情報 - 全{len(source['lotteries'])}件</div>
"""
                # deadline 情報を追加
                html += """
            <div style="margin-bottom: 15px; font-size: 14px; color: #718096;">
                <p>⏰ <span class="deadline-highlight">期限間近の情報は黄色ハイライト</span>で表示されています</p>
            </div>
"""
                # 受付中の抽選を最上部に配置
                sorted_lotteries = self._sort_lotteries_by_status(source['lotteries'])
                for lottery in sorted_lotteries[:15]:
                    store = lottery.get('store', '')
                    product = lottery.get('product', '')
                    detail_url = lottery.get('detail_url', '#')
                    timestamp = lottery.get('timestamp', '')
                    end_date = lottery.get('end_date', '')
                    is_new = self._is_new(timestamp)
                    new_badge = '<span class="badge-new">🆕 NEW</span>' if is_new else ''

                    # P1: end_date をハイライト
                    deadline_info = ''
                    if end_date:
                        deadline_info = f'<div style="margin-top: 5px;"><span class="deadline-highlight">📅 締切: {end_date}</span></div>'

                    html += f"""
            <div class="lottery-item">
                <div class="store-name">🏪 {store}</div>
                <div class="product-name">📦 {product}{new_badge}</div>
                {deadline_info}
                <a href="{detail_url}" class="detail-link" target="_blank">🔗 詳細を見る</a>
            </div>
"""
                if len(source['lotteries']) > 15:
                    remaining = len(source['lotteries']) - 15
                    html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""

            # 予約情報を追加（上限15件）
            if source['reservation_count'] > 0:
                html += """
            <div class="section-title">📅 予約情報 - 全{0}件</div>
""".format(source['reservation_count'])
                for reservation in source['reservations'][:15]:
                    title = reservation.get('title', '')
                    price = reservation.get('price', '')
                    availability = reservation.get('availability', '')
                    url = reservation.get('url', '#')
                    release_date = reservation.get('release_date', '')
                    timestamp = reservation.get('timestamp', '')
                    is_new = self._is_new(timestamp)
                    new_badge = '<span class="badge-new">🆕 NEW</span>' if is_new else ''

                    # P4: 価格表示
                    price_info = f'<div class="price">💰 {price}</div>' if price else ''

                    html += f"""
            <div class="reservation-item">
                <div class="product-name">📦 {title}{new_badge}</div>
                {price_info}
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
                if len(source['reservations']) > 15:
                    remaining = len(source['reservations']) - 15
                    html += f"""
            <div style="text-align: center; color: #718096; margin-top: 15px;">
                ... 他 {remaining} 件
            </div>
"""

            html += """
        </div>
"""

        # 🗓️ 今後の抽選予定セクション（各ソースの upcoming_products を集約、上限15件）
        if upcoming_products:
            html += f"""
        <div class="source-section" style="background: #f0f8ff; border-color: #4169e1;">
            <div class="section-title" style="color: #4169e1;">🗓️ 今後の抽選予定 - 全{len(upcoming_products)}件</div>
"""
            for product in upcoming_products[:15]:
                # gamepediaスキーマ対応: product_name または name
                name = product.get('product_name', '') or product.get('name', '')
                release_date = product.get('release_date', '')
                description = product.get('description', '')
                url = product.get('detail_url', '') or product.get('url', '')
                store = product.get('store', '')
                # gamepediaの lottery_schedule を lottery_start として扱う
                lottery_start = product.get('lottery_schedule', '') or product.get('lottery_start', '')

                # ポケモンセンターの場合は★マークで目立たせる
                is_pokemon_center = store and 'ポケモンセンター' in store
                star_mark = '★ ' if is_pokemon_center else ''
                store_display = f'🏪 {star_mark}{store}' if store else ''

                html += f"""
            <div class="lottery-item" style="border-left-color: #4169e1;">
                <div class="product-name">📦 {name}</div>
"""
                if store_display:
                    html += f'                <div class="store-name">{store_display}</div>\n'
                if release_date:
                    html += f'                <div class="store-name">📅 発売日: {release_date}</div>\n'
                if lottery_start:
                    html += f'                <div class="store-name">🎯 抽選開始: {lottery_start}</div>\n'
                if description:
                    html += f'                <div class="store-name">{description}</div>\n'
                if url:
                    html += f'                <a href="{url}" class="detail-link" target="_blank">🔗 詳細を見る</a>\n'
                html += """
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
