"""
test_utils.py - ユーティリティ関数のテスト

テスト対象：
- _parse_date_flexible: 日付パース関数（曜日パターン対応）
"""
import unittest
from datetime import date
from pathlib import Path
import sys

# tests/の外からimportするため、親ディレクトリをsys.pathに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import _parse_date_flexible, _extract_year_from_string


class TestParseDateFlexible(unittest.TestCase):
    """_parse_date_flexible関数のテスト"""

    def setUp(self):
        """テスト用の基準日を設定"""
        self.today = date(2026, 4, 1)

    def test_parse_full_year_month_day(self):
        """4桁年 + 月 + 日を解析"""
        result = _parse_date_flexible('2026/4/15', self.today)
        expected = date(2026, 4, 15)
        self.assertEqual(result, expected)

    def test_parse_full_date_with_hyphens(self):
        """4桁年 + 月 + 日（ハイフン区切り）を解析"""
        result = _parse_date_flexible('2026-4-20', self.today)
        expected = date(2026, 4, 20)
        self.assertEqual(result, expected)

    def test_parse_full_date_with_japanese_format(self):
        """4桁年 + 月 + 日（日本語形式）を解析"""
        result = _parse_date_flexible('2026年4月25日', self.today)
        expected = date(2026, 4, 25)
        self.assertEqual(result, expected)

    def test_parse_month_day_only(self):
        """月 + 日のみ（年は現在年を使用）"""
        result = _parse_date_flexible('5/10', self.today)
        expected = date(2026, 5, 10)
        self.assertEqual(result, expected)

    def test_parse_month_day_with_japanese(self):
        """月 + 日（日本語形式）"""
        result = _parse_date_flexible('5月10日', self.today)
        expected = date(2026, 5, 10)
        self.assertEqual(result, expected)

    def test_parse_month_day_with_zenkaku_parentheses(self):
        """月 + 日 with 曜日（全角括弧）"""
        result = _parse_date_flexible('3/31（火）', self.today)
        expected = date(2026, 3, 31)
        self.assertEqual(result, expected)

    def test_parse_month_day_with_hankaku_parentheses(self):
        """月 + 日 with 曜日（半角括弧）"""
        result = _parse_date_flexible('4/5(土)', self.today)
        expected = date(2026, 4, 5)
        self.assertEqual(result, expected)

    def test_parse_full_date_with_zenkaku_weekday(self):
        """4桁年 + 月 + 日 with 曜日（全角括弧）"""
        result = _parse_date_flexible('2026/4/15（水）', self.today)
        expected = date(2026, 4, 15)
        self.assertEqual(result, expected)

    def test_parse_full_date_with_hankaku_weekday(self):
        """4桁年 + 月 + 日 with 曜日（半角括弧）"""
        result = _parse_date_flexible('2026/4/20(月)', self.today)
        expected = date(2026, 4, 20)
        self.assertEqual(result, expected)

    def test_parse_invalid_date(self):
        """不正な日付はNoneを返す"""
        result = _parse_date_flexible('13/32', self.today)
        self.assertIsNone(result)

    def test_parse_garbage_input(self):
        """解析できない文字列はNoneを返す"""
        result = _parse_date_flexible('abcdef', self.today)
        self.assertIsNone(result)

    def test_parse_with_extra_whitespace(self):
        """前後のスペースは削除"""
        result = _parse_date_flexible('  4/15  ', self.today)
        expected = date(2026, 4, 15)
        self.assertEqual(result, expected)


class TestExtractYearFromString(unittest.TestCase):
    """_extract_year_from_string関数のテスト"""

    def test_extract_year_simple(self):
        """単純な年号抽出"""
        result = _extract_year_from_string('2026/4/15')
        self.assertEqual(result, 2026)

    def test_extract_year_with_japanese(self):
        """日本語形式から年号抽出"""
        result = _extract_year_from_string('2026年4月15日')
        self.assertEqual(result, 2026)

    def test_extract_year_2025(self):
        """2025年抽出"""
        result = _extract_year_from_string('2025年度')
        self.assertEqual(result, 2025)

    def test_extract_year_not_found(self):
        """年号が見つからない場合はNoneを返す"""
        result = _extract_year_from_string('no year here')
        self.assertIsNone(result)

    def test_extract_year_only_last_four_digits(self):
        """最初の4桁の年号のみを抽出"""
        result = _extract_year_from_string('2026年度2027年の予定')
        self.assertEqual(result, 2026)


if __name__ == '__main__':
    unittest.main()
