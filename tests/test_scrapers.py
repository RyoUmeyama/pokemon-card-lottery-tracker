"""
Scraper基底クラスのユニットテスト
"""
import pytest
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
