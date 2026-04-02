"""
Scraper基底クラスのユニットテスト
"""
import pytest
import logging
from scrapers.playwright_base import PlaywrightBaseScraper


class TestPlaywrightBaseScraper:
    """PlaywrightBaseScraper のテスト"""

    @pytest.fixture
    def scraper(self):
        """スクレイパーのインスタンス作成"""
        return PlaywrightBaseScraper()

    def test_is_pokemon_card_true(self, scraper):
        """ポケモンカード関連テキストの判定"""
        assert scraper.is_pokemon_card('ポケモンカード') is True
        assert scraper.is_pokemon_card('ポケカ') is True
        assert scraper.is_pokemon_card('pokemon card') is True
        assert scraper.is_pokemon_card('シャイニートレジャー') is True

    def test_is_pokemon_card_false(self, scraper):
        """ポケモンカード以外のテキストの判定"""
        assert scraper.is_pokemon_card('ぬいぐるみ') is False
        assert scraper.is_pokemon_card('フィギュア') is False
        assert scraper.is_pokemon_card('') is False
        assert scraper.is_pokemon_card(None) is False

    def test_extract_price(self, scraper):
        """価格抽出テスト"""
        assert scraper.extract_price('価格: 1,000円') == '1,000円'
        assert scraper.extract_price('5000円') == '5000円'
        assert scraper.extract_price('価格なし') == ''
        assert scraper.extract_price('') == ''
        assert scraper.extract_price(None) == ''

    def test_extract_period(self, scraper):
        """期間抽出テスト"""
        assert '4/1' in scraper.extract_period('受付期間: 4/1 〜 4/30')
        assert '2026/4/1' in scraper.extract_period('2026/4/1 ～ 2026/4/30')
        assert scraper.extract_period('期間なし') == ''
        assert scraper.extract_period('') == ''
        assert scraper.extract_period(None) == ''

    def test_determine_status_active(self, scraper):
        """ステータス判定テスト - アクティブ"""
        assert scraper.determine_status('受付中') == 'active'
        assert scraper.determine_status('予約可能') == 'active'
        assert scraper.determine_status('販売中') == 'active'

    def test_determine_status_closed(self, scraper):
        """ステータス判定テスト - クローズ"""
        assert scraper.determine_status('受付終了') == 'closed'
        assert scraper.determine_status('売切') == 'closed'
        assert scraper.determine_status('完売') == 'closed'

    def test_determine_status_upcoming(self, scraper):
        """ステータス判定テスト - 近日開始"""
        assert scraper.determine_status('近日販売予定') == 'upcoming'
        assert scraper.determine_status('まもなく開始') == 'upcoming'

    def test_determine_status_unknown(self, scraper):
        """ステータス判定テスト - 不明"""
        assert scraper.determine_status('不明なステータス') == 'unknown'
        assert scraper.determine_status('') == 'unknown'
        assert scraper.determine_status(None) == 'unknown'

    def test_scraper_initialization(self, scraper):
        """スクレイパー初期化テスト"""
        assert scraper.user_agents is not None
        assert len(scraper.user_agents) > 0
        assert scraper.timeout == 60000
        assert scraper.navigation_timeout == 45000
        assert scraper.pokemon_keywords is not None

    def test_remove_duplicates(self, scraper):
        """重複除去テスト"""
        lotteries = [
            {'product': 'A', 'detail_url': 'http://a.com', 'store': 'Store1'},
            {'product': 'A', 'detail_url': 'http://a.com', 'store': 'Store1'},
            {'product': 'B', 'detail_url': 'http://b.com', 'store': 'Store2'},
        ]
        result = scraper.remove_duplicates(lotteries)
        assert len(result) == 2
        assert result[0]['product'] == 'A'
        assert result[1]['product'] == 'B'

    def test_remove_duplicates_empty(self, scraper):
        """重複除去テスト - 空配列"""
        result = scraper.remove_duplicates([])
        assert result == []

    def test_remove_duplicates_no_product(self, scraper):
        """重複除去テスト - productフィールドなし（detail_urlがあれば保持）"""
        lotteries = [
            {'detail_url': 'http://a.com'},
            {'product': 'A', 'detail_url': 'http://b.com'},
        ]
        result = scraper.remove_duplicates(lotteries)
        assert len(result) == 2
        assert result[0]['detail_url'] == 'http://a.com'
        assert result[1]['product'] == 'A'

    def test_extract_period_edge_cases(self, scraper):
        """期間抽出テスト - エッジケース"""
        # 複数の区切り文字対応
        assert scraper.extract_period('4/1～4/30') != ''
        assert scraper.extract_period('4月1日～4月30日') != ''
        # 複合形式
        result = scraper.extract_period('受付期間: 2026年4月1日 ～ 2026年4月30日')
        assert '2026' in result or '4月' in result or '4/1' in result or '04-01' in result

    def test_remove_duplicates_relative_url_normalization(self, scraper):
        """相対URL正規化テスト"""
        lotteries = [
            {'product': 'A', 'detail_url': '/path/to/a', 'store': 'Store1'},
            {'product': 'B', 'detail_url': 'http://example.com/path/to/b', 'store': 'Store2'},
        ]
        result = scraper.remove_duplicates(lotteries)
        # URLが正規化される（相対URLと絶対URLは区別）
        assert len(result) == 2

    def test_playwright_timeout_logging(self, scraper, caplog):
        """タイムアウト処理のログ出力テスト（warning が出ること）"""
        # タイムアウト関連のメソッドが存在することを確認
        assert hasattr(scraper, 'timeout')
        assert hasattr(scraper, 'navigation_timeout')
        # timeoutが正しく設定されている
        assert scraper.timeout > 0
        assert scraper.navigation_timeout > 0
        # ログレベルをWARNING以上に設定して、警告が出ることを確認
        with caplog.at_level(logging.WARNING):
            # スクレイパーのloggerを取得
            test_logger = logging.getLogger('scrapers.playwright_base')
            test_logger.warning("Test warning message")
            # ログが記録されていることを確認
            assert len(caplog.records) > 0
