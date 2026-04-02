"""
統合テスト：全activeスクレイパーの初期化・main.py・notify.py・レポート生成機能
"""
import os
import pytest
import yaml
import importlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestActiveScrapers:
    """config/scrapers.yamlの全activeスクレイパーの初期化テスト"""

    def test_all_active_scrapers_can_initialize(self):
        """全activeスクレイパーがimport+初期化できることを確認"""
        config_path = PROJECT_ROOT / 'config' / 'scrapers.yaml'

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config is not None, "scrapers.yaml is empty"
        assert 'scrapers' in config, "scrapers.yaml has no 'scrapers' key"

        scrapers = config['scrapers']
        assert len(scrapers) > 0, "No scrapers defined in config"

        for scraper in scrapers:
            # skip: true の場合はスキップ
            if scraper.get('skip'):
                continue

            name = scraper.get('name', 'unknown')
            module_name = scraper.get('module')
            class_name = scraper.get('class')
            kwargs = scraper.get('kwargs', {})

            assert module_name, f"{name} has no module defined"
            assert class_name, f"{name} has no class defined"

            # モジュールをインポート
            try:
                mod = importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"{name} ({module_name}) import failed: {e}")

            # クラスを取得
            try:
                cls = getattr(mod, class_name)
            except AttributeError as e:
                pytest.fail(f"{name} class '{class_name}' not found in {module_name}: {e}")

            # インスタンス化
            try:
                instance = cls(**kwargs)
            except Exception as e:
                pytest.fail(f"{name} initialization failed: {e}")

            # インスタンスの確認
            assert instance is not None, f"{name} initialization returned None"

            # scrapeメソッドの確認
            assert callable(getattr(instance, 'scrape', None)), \
                f"{name} has no callable 'scrape' method"


class TestMainModule:
    """main.pyのload_scrapers_from_config()機能テスト"""

    def test_load_scrapers_from_config_no_error(self):
        """load_scrapers_from_config()がエラーなく実行できることを確認"""
        try:
            from main import load_scrapers_from_config
        except ImportError as e:
            pytest.fail(f"Failed to import load_scrapers_from_config: {e}")

        try:
            scrapers = load_scrapers_from_config()
        except Exception as e:
            pytest.fail(f"load_scrapers_from_config() raised exception: {e}")

        assert scrapers is not None, "load_scrapers_from_config returned None"
        assert isinstance(scrapers, list), \
            f"Expected list, got {type(scrapers)}"
        assert len(scrapers) > 0, "No scrapers loaded from config"


class TestNotifyModule:
    """notify.pyのGmailNotifier初期化テスト"""

    @patch.dict('os.environ', {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@gmail.com',
        'SMTP_PASSWORD': 'testpass',
        'RECIPIENT_EMAIL': 'recipient@example.com'
    })
    def test_gmail_notifier_can_initialize(self):
        """GmailNotifierが初期化できることを確認（環境変数ベース）"""
        try:
            from notify import GmailNotifier
        except ImportError as e:
            pytest.fail(f"Failed to import GmailNotifier: {e}")

        try:
            notifier = GmailNotifier()
        except Exception as e:
            pytest.fail(f"GmailNotifier initialization failed: {e}")

        assert notifier is not None, "GmailNotifier initialization returned None"
        assert hasattr(notifier, 'smtp_server'), "GmailNotifier has no smtp_server attribute"
        assert hasattr(notifier, 'recipient'), "GmailNotifier has no recipient attribute"


class TestReportGeneration:
    """レポート生成機能のテスト"""

    def test_generate_html_report_can_import(self):
        """generate_html_report.pyがimportできることを確認"""
        try:
            from generate_html_report import generate_html_report
        except ImportError as e:
            pytest.fail(f"Failed to import generate_html_report: {e}")

        assert callable(generate_html_report), \
            "generate_html_report is not callable"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
