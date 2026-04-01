"""
Gmail通知機能のユニットテスト（SMTP接続なし）
"""
import pytest
from datetime import datetime, timedelta
from notify import GmailNotifier


class TestGmailNotifier:
    """GmailNotifier のテスト"""

    @pytest.fixture
    def notifier(self):
        """通知機のインスタンス作成"""
        return GmailNotifier()

    def test_parse_date_valid_formats(self, notifier):
        """日付パース - 複数フォーマット対応"""
        assert notifier._parse_date('2026-04-01') is not None
        assert notifier._parse_date('2026/04/01') is not None
        assert notifier._parse_date('2026年04月01日') is not None

    def test_parse_date_invalid(self, notifier):
        """日付パース - 無効な入力"""
        assert notifier._parse_date('invalid-date') is None
        assert notifier._parse_date('') is None
        assert notifier._parse_date(None) is None

    def test_is_ended_true(self, notifier):
        """抽選終了判定 - 終了済み"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        assert notifier._is_ended(yesterday) is True

    def test_is_ended_false(self, notifier):
        """抽選終了判定 - 進行中"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert notifier._is_ended(tomorrow) is False

    def test_is_ended_invalid(self, notifier):
        """抽選終了判定 - 無効な日付"""
        assert notifier._is_ended('') is False
        assert notifier._is_ended(None) is False
        assert notifier._is_ended('invalid') is False

    def test_days_until_deadline(self, notifier):
        """期限までの日数計算"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        days = notifier._days_until_deadline(tomorrow)
        assert days == 1

        in_3_days = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        assert notifier._days_until_deadline(in_3_days) == 3

    def test_days_until_deadline_invalid(self, notifier):
        """期限までの日数計算 - 無効な入力"""
        assert notifier._days_until_deadline('') is None
        assert notifier._days_until_deadline(None) is None
        assert notifier._days_until_deadline('invalid') is None

    def test_is_deadline_soon_true(self, notifier):
        """期限間近判定 - 間近"""
        in_2_days = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        assert notifier._is_deadline_soon(in_2_days, days=3) is True

    def test_is_deadline_soon_false(self, notifier):
        """期限間近判定 - 余裕あり"""
        in_10_days = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        assert notifier._is_deadline_soon(in_10_days, days=3) is False

    def test_is_deadline_soon_invalid(self, notifier):
        """期限間近判定 - 無効な入力"""
        assert notifier._is_deadline_soon('', days=3) is False
        assert notifier._is_deadline_soon(None, days=3) is False

    def test_notifier_initialization(self, notifier):
        """通知機初期化テスト"""
        assert notifier.smtp_server == 'smtp.gmail.com'
        assert notifier.smtp_port == 465
        # 環境変数がない場合はNone
        assert notifier.smtp_username is None or isinstance(notifier.smtp_username, str)
        assert notifier.smtp_password is None or isinstance(notifier.smtp_password, str)
        assert notifier.recipient is None or isinstance(notifier.recipient, str)

    def test_is_new_true(self, notifier):
        """新着判定 - 24時間以内"""
        recent_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
        assert notifier._is_new(recent_timestamp) is True

    def test_is_new_false(self, notifier):
        """新着判定 - 24時間以上前"""
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        assert notifier._is_new(old_timestamp) is False

    def test_is_new_invalid(self, notifier):
        """新着判定 - 無効なタイムスタンプ"""
        assert notifier._is_new('') is False
        assert notifier._is_new(None) is False

    def test_create_email_body_basic(self, notifier):
        """メール本文生成 - 基本形式"""
        sources_summary = [
            {
                'name': 'source1',
                'lotteries': [
                    {'product': 'テスト', 'end_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')}
                ],
                'reservations': [],
                'lottery_count': 1,
                'reservation_count': 0
            }
        ]
        body = notifier._create_email_body(sources_summary, 1, 0)
        assert body is not None
        assert isinstance(body, str)

    def test_create_email_body_with_deadline_soon(self, notifier):
        """メール本文生成 - 期限間近アイテム含む"""
        sources_summary = []
        deadline_soon = [
            {
                'product': '期限間近商品',
                'store': 'テスト店舗',
                'end_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'detail_url': 'https://example.com',
            }
        ]
        body = notifier._create_email_body(sources_summary, 0, 0, deadline_soon_items=deadline_soon)
        assert body is not None
        assert isinstance(body, str)

    def test_create_email_body_with_zero_alert(self, notifier):
        """メール本文生成 - 0件アラート"""
        sources_summary = []
        body = notifier._create_email_body(
            sources_summary, 0, 0,
            zero_alert=True,
            zero_alert_sources=['source1', 'source2']
        )
        assert body is not None
        assert isinstance(body, str)
