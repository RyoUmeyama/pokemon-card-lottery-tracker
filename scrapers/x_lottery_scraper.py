"""
X(Twitter)公式アカウントからポケモンカード抽選情報を収集
GEO、TSUTAYA、ヨドバシなどの公式アカウントを監視
"""
import os
import re
from datetime import datetime, timedelta
import json

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False


class XLotteryScraper:
    def __init__(self):
        # 監視対象の公式アカウント（ユーザー名のみ）
        self.target_accounts = [
            # 小売店公式アカウント
            'GEO_official',      # ゲオ公式
            'TSUTAYA_PR',        # TSUTAYA公式
            'yikiikimobile',     # ヨドバシゴールドポイントカード
            'YodobashiCamera',   # ヨドバシカメラ
            'biaboratory',       # ビックカメラ
            # ポケモン関連公式
            'paboratory',        # ポケモン情報
        ]

        # 抽選関連キーワード
        self.lottery_keywords = [
            '抽選', '予約', 'ポケモンカード', 'ポケカ', 'TCG',
            '応募', '当選', '販売', '受付', '申込',
            'ボックス', 'BOX', 'パック', '拡張パック'
        ]

        # X API認証情報（環境変数から取得）
        self.bearer_token = os.environ.get('X_BEARER_TOKEN')
        self.api_key = os.environ.get('X_API_KEY')
        self.api_secret = os.environ.get('X_API_SECRET')
        self.access_token = os.environ.get('X_ACCESS_TOKEN')
        self.access_token_secret = os.environ.get('X_ACCESS_TOKEN_SECRET')

        self.client = None

    def _init_client(self):
        """Tweepyクライアントを初期化"""
        if not TWEEPY_AVAILABLE:
            print("Warning: tweepy is not installed. X scraping will be skipped.")
            return False

        if self.bearer_token:
            try:
                self.client = tweepy.Client(bearer_token=self.bearer_token)
                return True
            except Exception as e:
                print(f"Error initializing X client with bearer token: {e}")

        if self.api_key and self.api_secret and self.access_token and self.access_token_secret:
            try:
                self.client = tweepy.Client(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_token_secret
                )
                return True
            except Exception as e:
                print(f"Error initializing X client with OAuth: {e}")

        print("Warning: X API credentials not configured. X scraping will be skipped.")
        return False

    def scrape(self):
        """X(Twitter)から抽選情報を収集"""
        lotteries = []

        # API認証を確認
        if not self._init_client():
            return {
                'source': 'X (Twitter) 公式アカウント',
                'scraped_at': datetime.now().isoformat(),
                'lotteries': [],
                'error': 'X API credentials not configured or tweepy not installed'
            }

        for account in self.target_accounts:
            try:
                account_lotteries = self._scrape_account(account)
                lotteries.extend(account_lotteries)
            except Exception as e:
                print(f"Error scraping @{account}: {e}")

        # 重複除去
        unique_lotteries = self._remove_duplicates(lotteries)

        result = {
            'source': 'X (Twitter) 公式アカウント',
            'scraped_at': datetime.now().isoformat(),
            'accounts_monitored': self.target_accounts,
            'lotteries': unique_lotteries
        }

        return result

    def _scrape_account(self, username):
        """指定アカウントのツイートから抽選情報を取得"""
        lotteries = []

        try:
            # ユーザーIDを取得
            user = self.client.get_user(username=username)
            if not user.data:
                print(f"User @{username} not found")
                return []

            user_id = user.data.id

            # 最近のツイートを取得（最大100件、過去7日分）
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)

            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=100,
                start_time=start_time.isoformat() + 'Z',
                tweet_fields=['created_at', 'text', 'entities'],
                expansions=['author_id']
            )

            if not tweets.data:
                return []

            for tweet in tweets.data:
                # ポケモンカード関連かつ抽選関連のツイートを抽出
                if self._is_lottery_related(tweet.text):
                    lottery_info = self._parse_tweet(tweet, username)
                    if lottery_info:
                        lotteries.append(lottery_info)

        except tweepy.errors.TooManyRequests:
            print(f"Rate limit exceeded for @{username}")
        except tweepy.errors.Forbidden as e:
            print(f"Access forbidden for @{username}: {e}")
        except Exception as e:
            print(f"Error fetching tweets from @{username}: {e}")

        return lotteries

    def _is_lottery_related(self, text):
        """ポケモンカード抽選関連のツイートかチェック"""
        if not text:
            return False

        text_lower = text.lower()

        # ポケモンカード関連
        is_pokemon = any(kw in text_lower for kw in ['ポケモンカード', 'ポケカ', 'pokemon card', 'tcg'])

        # 抽選・予約関連
        is_lottery = any(kw in text_lower for kw in ['抽選', '予約', '応募', '受付', '販売'])

        return is_pokemon and is_lottery

    def _parse_tweet(self, tweet, username):
        """ツイートから抽選情報を抽出"""
        try:
            text = tweet.text

            # URLを抽出
            urls = re.findall(r'https?://[^\s]+', text)
            detail_url = urls[0] if urls else f'https://twitter.com/{username}/status/{tweet.id}'

            # 商品名を推定
            product_name = self._extract_product_name(text)

            # 期間を抽出
            period = self._extract_period(text)

            # ステータスを判定
            status = 'active'
            if '終了' in text or '締切' in text or '完売' in text:
                status = 'closed'
            elif '近日' in text or '予定' in text or 'まもなく' in text:
                status = 'upcoming'

            # 店舗名をマッピング
            store_names = {
                'GEO_official': 'ゲオ',
                'TSUTAYA_PR': 'TSUTAYA',
                'YodobashiCamera': 'ヨドバシカメラ',
                'yikiikimobile': 'ヨドバシカメラ',
                'biaboratory': 'ビックカメラ',
            }
            store = store_names.get(username, username)

            lottery = {
                'store': store,
                'product': product_name if product_name else text[:100],
                'lottery_type': '抽選販売',
                'period': period,
                'detail_url': detail_url,
                'status': status,
                'source_tweet': f'https://twitter.com/{username}/status/{tweet.id}',
                'tweet_date': tweet.created_at.isoformat() if tweet.created_at else ''
            }

            return lottery

        except Exception as e:
            print(f"Error parsing tweet: {e}")
            return None

    def _extract_product_name(self, text):
        """ツイートから商品名を抽出"""
        # 【】や「」で囲まれた商品名を探す
        patterns = [
            r'【(.+?)】',
            r'「(.+?)」',
            r'『(.+?)』',
            r'ポケモンカード(?:ゲーム)?\s*(.+?)(?:の|を|が|は|\s|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                product = match.group(1).strip()
                if len(product) > 5:  # 短すぎるものは除外
                    return product

        return None

    def _extract_period(self, text):
        """ツイートから期間を抽出"""
        # 日付パターン
        patterns = [
            r'(\d{1,2}[/月]\d{1,2}[日]?\s*[〜～\-]\s*\d{1,2}[/月]\d{1,2}[日]?)',
            r'(\d{1,2}月\d{1,2}日.*?まで)',
            r'(\d{1,2}/\d{1,2}.*?締切)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return ''

    def _remove_duplicates(self, lotteries):
        """重複を除去"""
        seen = set()
        unique = []

        for lottery in lotteries:
            # ツイートURLで重複判定
            key = lottery.get('source_tweet', lottery.get('detail_url', ''))
            if key not in seen and lottery.get('product'):
                seen.add(key)
                unique.append(lottery)

        return unique


if __name__ == '__main__':
    scraper = XLotteryScraper()
    data = scraper.scrape()

    if data:
        output_file = '../data/x_lottery_latest.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
        print(f"Found {len(data['lotteries'])} lottery entries")
        for lottery in data['lotteries']:
            print(f"  - [{lottery['store']}] {lottery['product']}")
