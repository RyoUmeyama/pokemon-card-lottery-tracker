"""
RequestsBaseScraper の詳細テスト
リトライロジック、ヘッダ設定、タイムアウト設定
"""
import pytest
from unittest.mock import patch, MagicMock, call
import requests
from scrapers.requests_base import RequestsBaseScraper


class TestRequestsBaseScraperHeaders:
    """ヘッダ設定のテスト"""

    @pytest.fixture
    def scraper(self):
        return RequestsBaseScraper()

    def test_default_user_agent(self, scraper):
        """デフォルト User-Agent テスト"""
        headers = scraper.get_headers()
        assert headers['User-Agent'] == scraper.DEFAULT_USER_AGENT

    def test_user_agent_in_request(self, scraper):
        """リクエストに User-Agent が含まれるテスト"""
        # Session のヘッダに User-Agent が設定されているか確認
        assert 'User-Agent' in scraper.session.headers
        assert scraper.session.headers['User-Agent'] == scraper.DEFAULT_USER_AGENT


class TestRequestsBaseScraperTimeout:
    """タイムアウト設定のテスト"""

    def test_custom_timeout(self):
        """カスタムタイムアウト設定テスト"""
        scraper = RequestsBaseScraper(timeout=60)
        assert scraper.timeout == 60

    def test_timeout_in_request(self):
        """リクエストにタイムアウトが反映されるテスト"""
        scraper = RequestsBaseScraper(timeout=45)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b'<html></html>'
            mock_get.return_value = mock_response

            scraper.fetch_html('http://example.com')

            # 呼び出されたときのタイムアウトを確認
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == 45

    def test_timeout_exception(self):
        """タイムアウト例外のハンドリング"""
        scraper = RequestsBaseScraper(timeout=5)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = requests.Timeout("Request timed out")

            result = scraper.fetch_html('http://example.com')
            assert result is None


class TestRequestsBaseScraperWaitTime:
    """待機時間のテスト"""

    def test_custom_wait_time(self):
        """カスタム待機時間設定テスト"""
        scraper = RequestsBaseScraper(wait_time=2.5)
        assert scraper.wait_time == 2.5

    @patch('time.sleep')
    def test_wait_time_before_request(self, mock_sleep):
        """リクエスト前に待機時間が実行されるテスト"""
        scraper = RequestsBaseScraper(wait_time=1.5)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b'<html></html>'
            mock_get.return_value = mock_response

            scraper.fetch_html('http://example.com')

            # sleep が呼び出されたかを確認
            mock_sleep.assert_called_once_with(1.5)
            # その後にリクエストが実行された
            mock_get.assert_called_once()


class TestRequestsBaseScraperErrorHandling:
    """エラーハンドリングのテスト"""

    @pytest.fixture
    def scraper(self):
        return RequestsBaseScraper()

    def test_connection_error(self, scraper):
        """接続エラーのハンドリング"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")
            result = scraper.fetch_html('http://example.com')
            assert result is None

    def test_http_error_404(self, scraper):
        """HTTP 404 エラーのハンドリング"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_get.return_value = mock_response

            result = scraper.fetch_html('http://example.com')
            assert result is None

    def test_http_error_500(self, scraper):
        """HTTP 500 エラーのハンドリング"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
            mock_get.return_value = mock_response

            result = scraper.fetch_html('http://example.com')
            assert result is None

    def test_handle_error_includes_source_name(self, scraper):
        """エラーハンドリング - source_name を含む"""
        scraper.source_name = 'test_source'
        error = ValueError("Test error")
        result = scraper.handle_error(error, "Test context")

        assert result['source'] == 'test_source'
        assert result['lotteries'] == []
        assert 'scraped_at' in result
        assert 'error' in result

    def test_handle_error_default_source(self, scraper):
        """エラーハンドリング - source_name なし"""
        error = RuntimeError("Test error")
        result = scraper.handle_error(error)

        assert result['source'] == 'unknown'
        assert result['lotteries'] == []


class TestRequestsBaseScraperHTMLParsing:
    """HTML パースのテスト"""

    @pytest.fixture
    def scraper(self):
        return RequestsBaseScraper()

    def test_parse_soup_with_special_characters(self, scraper):
        """特殊文字を含む HTML のパース"""
        html = '<html><body><p>テスト &amp; テスト</p></body></html>'
        soup = scraper.parse_soup(html)
        assert soup is not None
        p_tag = soup.find('p')
        assert 'テスト' in p_tag.text

    def test_parse_soup_with_nested_elements(self, scraper):
        """ネストされた要素のパース"""
        html = '<div><ul><li>Item 1</li><li>Item 2</li></ul></div>'
        soup = scraper.parse_soup(html)
        assert soup is not None
        items = soup.find_all('li')
        assert len(items) == 2

    def test_parse_soup_with_attributes(self, scraper):
        """属性を持つ要素のパース"""
        html = '<a href="http://example.com" class="link">Link</a>'
        soup = scraper.parse_soup(html)
        a_tag = soup.find('a')
        assert a_tag['href'] == 'http://example.com'
        assert a_tag['class'] == ['link']


class TestRequestsBaseScraperIntegration:
    """統合テスト"""

    @pytest.fixture
    def scraper(self):
        return RequestsBaseScraper(timeout=30, wait_time=0.5)

    def test_fetch_and_parse_success(self, scraper):
        """取得とパースの統合テスト"""
        html_content = '<html><body><h1>Test</h1></body></html>'

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = html_content.encode('utf-8')
            mock_get.return_value = mock_response

            # fetch
            html = scraper.fetch_html('http://example.com')
            assert html is not None

            # parse
            soup = scraper.parse_soup(html)
            assert soup is not None
            h1_tag = soup.find('h1')
            assert h1_tag.text == 'Test'

    def test_fetch_and_parse_error_recovery(self, scraper):
        """エラー時の回復テスト"""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = requests.Timeout("Timeout")

            html = scraper.fetch_html('http://example.com')
            assert html is None

            # エラーをハンドリング
            error = requests.Timeout("Timeout")
            result = scraper.handle_error(error, "Fetch failed")
            assert result['lotteries'] == []
            assert 'error' in result
