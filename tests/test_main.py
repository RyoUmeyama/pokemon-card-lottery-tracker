"""
test_main.py - メインモジュール（main.py）の基本テスト

テスト対象：
- build_composite_key: 複合キー生成の正確性
- detect_changes: 変更検出ロジック
"""
import json
import unittest
import tempfile
import os
from pathlib import Path

# tests/の外からimportするため、親ディレクトリをsys.pathに追加
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import build_composite_key, detect_changes, save_data, load_previous_data


class TestBuildCompositeKey(unittest.TestCase):
    """build_composite_key関数のテスト"""

    def test_lottery_type(self):
        """lottery タイプで product フィールドを使用"""
        item = {'url': 'http://example.com', 'product': 'ボッチャン'}
        result = build_composite_key(item, 'lottery')
        expected = 'http://example.com|ボッチャン'
        self.assertEqual(result, expected)

    def test_reservation_type(self):
        """reservation タイプで title フィールドを使用"""
        item = {'url': 'http://amazon.com', 'title': 'ポケモン BOX'}
        result = build_composite_key(item, 'reservation')
        expected = 'http://amazon.com|ポケモン BOX'
        self.assertEqual(result, expected)

    def test_missing_fields(self):
        """フィールドが存在しない場合は空文字列を使用"""
        item = {'product': 'ボッチャン'}  # url なし
        result = build_composite_key(item, 'lottery')
        expected = '|ボッチャン'
        self.assertEqual(result, expected)


class TestDetectChanges(unittest.TestCase):
    """detect_changes関数のテスト"""

    def test_first_run(self):
        """初回実行（old_dataがNone）"""
        new_data = {'lotteries': [{'product': 'A', 'url': 'http://a.com'}]}
        has_changes, message = detect_changes(None, new_data, 'lottery')
        self.assertTrue(has_changes)
        self.assertEqual(message, ["初回実行"])

    def test_no_changes(self):
        """データに変更がない場合"""
        old_data = {'lotteries': [{'product': 'A', 'url': 'http://a.com'}]}
        new_data = {'lotteries': [{'product': 'A', 'url': 'http://a.com'}]}
        has_changes, changes = detect_changes(old_data, new_data, 'lottery')
        self.assertFalse(has_changes)

    def test_added_items(self):
        """新規アイテムが追加された場合"""
        old_data = {'lotteries': [{'product': 'A', 'url': 'http://a.com'}]}
        new_data = {
            'lotteries': [
                {'product': 'A', 'url': 'http://a.com'},
                {'product': 'B', 'url': 'http://b.com'}
            ]
        }
        has_changes, changes = detect_changes(old_data, new_data, 'lottery')
        self.assertTrue(has_changes)
        self.assertTrue(any('新規' in str(c) for c in changes))

    def test_removed_items(self):
        """アイテムが削除された場合"""
        old_data = {
            'lotteries': [
                {'product': 'A', 'url': 'http://a.com'},
                {'product': 'B', 'url': 'http://b.com'}
            ]
        }
        new_data = {'lotteries': [{'product': 'A', 'url': 'http://a.com'}]}
        has_changes, changes = detect_changes(old_data, new_data, 'lottery')
        self.assertTrue(has_changes)
        self.assertTrue(any('終了' in str(c) for c in changes))


class TestLoadSaveData(unittest.TestCase):
    """load_previous_data と save_data のテスト"""

    def setUp(self):
        """テスト用一時ファイルを作成"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_data.json')

    def tearDown(self):
        """テスト用ファイルをクリーンアップ"""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)

    def test_save_and_load(self):
        """データ保存と読み込みの一貫性"""
        original_data = {
            'timestamp': '2026-01-01T00:00:00',
            'lotteries': [{'product': 'A', 'url': 'http://a.com'}]
        }
        save_data(original_data, self.test_file)
        loaded_data = load_previous_data(self.test_file)
        self.assertEqual(original_data, loaded_data)

    def test_load_nonexistent_file(self):
        """存在しないファイルの読み込みはNoneを返す"""
        result = load_previous_data(self.test_file)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
