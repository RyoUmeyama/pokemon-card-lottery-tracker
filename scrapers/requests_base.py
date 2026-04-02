"""
requests系スクレイパーの共通基底クラス

共通処理を集約：
- HTTPリクエスト送信
- HTMLパース
- User-Agent設定
- タイムアウト処理
- エラーハンドリング
"""
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RequestsBaseScraper:
    """requests系スクレイパーの基底クラス"""

    # デフォルト設定（サブクラスでオーバーライド可能）
    DEFAULT_TIMEOUT = 30
    DEFAULT_WAIT_TIME = 1
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

    def __init__(self, timeout: int = None, wait_time: float = None):
        """
        初期化

        Args:
            timeout: リクエストタイムアウト（秒）
            wait_time: リクエスト間隔（秒）
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.wait_time = wait_time or self.DEFAULT_WAIT_TIME
        self.session = requests.Session()
        self.headers = self.get_headers()
        # Sessionにヘッダを設定
        self.session.headers.update(self.headers)

    def get_headers(self) -> Dict[str, str]:
        """
        HTTPリクエストヘッダを取得

        Returns:
            ヘッダ辞書
        """
        return {
            'User-Agent': self.DEFAULT_USER_AGENT,
        }

    def fetch_html(self, url: str) -> Optional[str]:
        """
        URLからHTMLを取得

        Args:
            url: 対象URL

        Returns:
            HTMLコンテンツ（取得失敗時はNone）
        """
        try:
            time.sleep(self.wait_time)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def parse_soup(self, html_content: str) -> Optional[BeautifulSoup]:
        """
        HTMLをBeautifulSoupで解析

        Args:
            html_content: HTMLコンテンツ

        Returns:
            BeautifulSoupオブジェクト（解析失敗時はNone）
        """
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            return None

    def handle_error(self, e: Exception, context: str = "") -> Dict[str, Any]:
        """
        エラーをハンドリング

        Args:
            e: 発生した例外
            context: エラーコンテキスト

        Returns:
            エラー情報を含む結果辞書
        """
        error_msg = f"{context}: {e}" if context else str(e)
        logger.error(error_msg, exc_info=True)
        return {
            'source': getattr(self, 'source_name', 'unknown'),
            'scraped_at': datetime.now().isoformat(),
            'lotteries': [],
            'error': error_msg
        }

    def scrape(self) -> Optional[Dict[str, Any]]:
        """
        スクレイピング実行（サブクラスで実装）

        Returns:
            スクレイピング結果
        """
        raise NotImplementedError("Subclasses must implement scrape()")
