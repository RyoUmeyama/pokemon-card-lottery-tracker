"""
HTMLレポート生成機能のユニットテスト
"""
import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from generate_html_report import (
    load_data, normalize_schema, parse_date, get_lottery_status,
    cleanup_old_data, is_new_lottery, generate_html_report
)


class TestParseDate:
    """日付パース機能のテスト"""

    def test_parse_date_iso_format(self):
        """ISO形式の日付パース"""
        result = parse_date('2026-04-01')
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 1

    def test_parse_date_slash_format(self):
        """スラッシュ区切り形式の日付パース"""
        result = parse_date('2026/04/01')
        assert result is not None
        assert result.year == 2026

    def test_parse_date_japanese_format(self):
        """日本語形式の日付パース"""
        result = parse_date('2026年04月01日')
        assert result is not None
        assert result.year == 2026

    def test_parse_date_invalid(self):
        """無効な日付文字列"""
        result = parse_date('invalid-date')
        assert result == 'invalid-date'

    def test_parse_date_none(self):
        """None入力"""
        result = parse_date(None)
        assert result is None


class TestGetLotteryStatus:
    """抽選ステータス判定のテスト"""

    def test_status_active(self):
        """受付中のステータス"""
        lottery = {
            'start_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        }
        status = get_lottery_status(lottery)
        assert status == '受付中'

    def test_status_ended(self):
        """終了したステータス"""
        lottery = {
            'start_date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        }
        status = get_lottery_status(lottery)
        assert status == '終了'

    def test_status_upcoming(self):
        """予定のステータス"""
        lottery = {
            'start_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        }
        status = get_lottery_status(lottery)
        assert status == '予定'

    def test_status_missing_dates(self):
        """日付がない場合のステータス"""
        lottery = {'start_date': '', 'end_date': ''}
        status = get_lottery_status(lottery)
        assert status == '受付中'


class TestIsNewLottery:
    """新着判定機能のテスト"""

    def test_is_new_true(self):
        """24時間以内の新規追加"""
        recent_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
        assert is_new_lottery(recent_timestamp) is True

    def test_is_new_false(self):
        """24時間以上前のデータ"""
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        assert is_new_lottery(old_timestamp) is False

    def test_is_new_invalid(self):
        """無効なタイムスタンプ"""
        assert is_new_lottery('') is False
        assert is_new_lottery(None) is False
        assert is_new_lottery('invalid') is False


class TestNormalizeSchema:
    """スキーマ正規化機能のテスト"""

    def test_normalize_schema_basic(self):
        """基本的なスキーマ正規化"""
        data = {
            'timestamp': '2026-04-01T10:00:00',
            'sources': [
                {
                    'source': 'test-source',
                    'lotteries': [
                        {
                            'product': 'テスト商品',
                            'store': 'テスト店舗',
                            'lottery_type': '抽選',
                            'start_date': '2026-04-01',
                            'end_date': '2026-04-10',
                            'announcement_date': '2026-04-15',
                            'conditions': '条件',
                            'detail_url': 'https://example.com',
                        }
                    ],
                    'upcoming_products': []
                }
            ]
        }
        normalized = normalize_schema(data)
        assert normalized['timestamp'] == data['timestamp']
        assert len(normalized['sources']) == 1
        assert normalized['sources'][0]['source'] == 'test-source'
        assert len(normalized['sources'][0]['lotteries']) == 1

    def test_normalize_schema_removes_extra_fields(self):
        """余分なフィールドの削除"""
        data = {
            'timestamp': '2026-04-01T10:00:00',
            'sources': [
                {
                    'source': 'test-source',
                    'lotteries': [
                        {
                            'product': 'テスト商品',
                            'store': 'テスト店舗',
                            'status': 'active',  # 削除される
                            '_source': 'internal',  # 削除される
                            'detail_url': 'https://example.com',
                        }
                    ],
                    'upcoming_products': []
                }
            ]
        }
        normalized = normalize_schema(data)
        lottery = normalized['sources'][0]['lotteries'][0]
        assert 'status' not in lottery or lottery.get('status') is None
        assert '_source' not in lottery or lottery.get('_source') is None


class TestCleanupOldData:
    """期限切れデータ削除のテスト"""

    def test_cleanup_removes_old_data(self):
        """30日以上前のデータ削除"""
        base_time = datetime.now()
        old_start = (base_time - timedelta(days=40)).isoformat()
        recent_start = (base_time - timedelta(days=10)).isoformat()

        data = {
            'timestamp': base_time.isoformat(),
            'sources': [
                {
                    'source': 'test-source',
                    'lotteries': [
                        {
                            'product': '古い商品',
                            'store': 'テスト店舗',
                            'start_date': old_start,
                            'end_date': (base_time - timedelta(days=35)).isoformat(),
                        },
                        {
                            'product': '最近の商品',
                            'store': 'テスト店舗',
                            'start_date': recent_start,
                            'end_date': (base_time + timedelta(days=5)).isoformat(),
                        }
                    ],
                    'upcoming_products': []
                }
            ]
        }

        cleaned = cleanup_old_data(data, days=30)
        assert len(cleaned['sources'][0]['lotteries']) == 1
        assert cleaned['sources'][0]['lotteries'][0]['product'] == '最近の商品'

    def test_cleanup_removes_2025_and_earlier(self):
        """2025年以前のデータ削除"""
        base_time = datetime.now()
        data = {
            'timestamp': base_time.isoformat(),
            'sources': [
                {
                    'source': 'test-source',
                    'lotteries': [
                        {
                            'product': '2025年商品',
                            'store': 'テスト店舗',
                            'start_date': '2025-12-01',
                            'end_date': '2025-12-10',
                        },
                        {
                            'product': '2026年商品',
                            'store': 'テスト店舗',
                            'start_date': '2026-04-01',
                            'end_date': '2026-04-10',
                        }
                    ],
                    'upcoming_products': []
                }
            ]
        }

        cleaned = cleanup_old_data(data, days=30)
        assert len(cleaned['sources'][0]['lotteries']) == 1
        assert cleaned['sources'][0]['lotteries'][0]['product'] == '2026年商品'


class TestGenerateHtmlReport:
    """HTMLレポート生成機能のテスト"""

    @pytest.fixture
    def sample_data(self):
        """サンプルデータ"""
        return {
            'timestamp': datetime.now().isoformat(),
            'sources': [
                {
                    'source': 'test-source',
                    'lotteries': [
                        {
                            'product': 'テスト商品1',
                            'store': 'テスト店舗A',
                            'lottery_type': '先着順',
                            'start_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                            'end_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                            'announcement_date': '2026-04-20',
                            'conditions': 'テスト条件',
                            'detail_url': 'https://example.com/test1',
                        },
                        {
                            'product': 'テスト商品2',
                            'store': 'テスト店舗B',
                            'lottery_type': '抽選',
                            'start_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                            'end_date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
                            'announcement_date': '2026-04-25',
                            'conditions': '',
                            'detail_url': 'https://example.com/test2',
                        }
                    ],
                    'upcoming_products': []
                }
            ]
        }

    def test_generate_html_creates_file(self, sample_data, tmp_path):
        """HTMLレポート生成とファイル作成"""
        output_file = str(tmp_path / 'test_report.html')
        result = generate_html_report(sample_data, output_file)

        assert Path(output_file).exists()
        assert result == output_file

    def test_generate_html_contains_table(self, sample_data, tmp_path):
        """HTMLレポートがテーブルを含む"""
        output_file = str(tmp_path / 'test_report.html')
        generate_html_report(sample_data, output_file)

        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '<table' in content
        assert '<thead>' in content
        assert '<tbody' in content

    def test_generate_html_contains_products(self, sample_data, tmp_path):
        """HTMLレポートが商品情報を含む"""
        output_file = str(tmp_path / 'test_report.html')
        generate_html_report(sample_data, output_file)

        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'テスト商品1' in content
        assert 'テスト商品2' in content
        assert 'テスト店舗A' in content

    def test_generate_html_contains_sort_script(self, sample_data, tmp_path):
        """HTMLレポートがソート機能を含む"""
        output_file = str(tmp_path / 'test_report.html')
        generate_html_report(sample_data, output_file)

        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'sortLotteries' in content
        assert 'filterLotteries' in content
        assert 'sortSelect' in content

    def test_generate_html_status_badges(self, sample_data, tmp_path):
        """HTMLレポートがステータスバッジを含む"""
        output_file = str(tmp_path / 'test_report.html')
        generate_html_report(sample_data, output_file)

        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'status-badge' in content
        assert 'active' in content or '受付中' in content
