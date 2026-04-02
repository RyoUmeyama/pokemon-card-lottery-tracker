#!/usr/bin/env python3
"""
Verify all detail_urls in all_lotteries.json
Detects invalid URLs and optionally removes them from the JSON file.
"""

import json
import sys
import argparse
import requests
import logging
from pathlib import Path
from urllib.parse import urlparse

# Logging設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATA_FILE = Path(__file__).parent.parent / 'data' / 'all_lotteries.json'
TIMEOUT = 5
INVALID_KEYWORDS = {'login', 'signin', 'auth'}


def is_invalid_url(url):
    """Check if URL is empty or ends with #"""
    if not url or not url.strip():
        return True, "Empty URL"
    if url.endswith('#'):
        return True, "URL ends with #"
    return False, None


def check_redirect_to_auth(final_url):
    """Check if redirected URL contains auth keywords"""
    parsed = urlparse(final_url.lower())
    full_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}{parsed.params}{parsed.query}"
    if any(keyword in full_url for keyword in INVALID_KEYWORDS):
        return True, f"Redirected to auth page: {final_url}"
    return False, None


def verify_url(url):
    """
    Verify a single URL via HEAD request.
    Returns: (is_valid, reason)
    """
    # Check for empty/invalid URLs
    is_empty, reason = is_invalid_url(url)
    if is_empty:
        return False, reason

    try:
        response = requests.head(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; URL Verifier)'}
        )

        # Check HTTP status code
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        # Check if redirected to auth page
        is_auth_redirect, reason = check_redirect_to_auth(response.url)
        if is_auth_redirect:
            return False, reason

        return True, None

    except requests.Timeout:
        return False, "Timeout (5s)"
    except requests.RequestException as e:
        return False, f"Request error: {str(e)[:50]}"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def load_json():
    """Load all_lotteries.json"""
    if not DATA_FILE.exists():
        logger.error(f"Error: {DATA_FILE} not found")
        return None

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
        return None


def collect_urls(data):
    """Collect all detail_urls from sources"""
    urls = []
    for source in data.get('sources', []):
        for lottery in source.get('lotteries', []):
            detail_url = lottery.get('detail_url')
            if detail_url:
                urls.append({
                    'url': detail_url,
                    'source': source.get('source', 'unknown'),
                    'store': lottery.get('store', 'unknown'),
                    'product': lottery.get('product', 'unknown')
                })
    return urls


def verify_all_urls(data):
    """Verify all URLs and return results"""
    urls = collect_urls(data)
    results = []
    invalid_count = 0

    for entry in urls:
        url = entry['url']
        is_valid, reason = verify_url(url)

        status = "VALID" if is_valid else "INVALID"
        reason_str = f" ({reason})" if reason else ""

        logger.info(f"{status}: {url}{reason_str}")
        logger.info(f"  └─ {entry['source']} > {entry['store']}")

        results.append({
            'url': url,
            'valid': is_valid,
            'reason': reason,
            'source': entry['source'],
            'store': entry['store']
        })

        if not is_valid:
            invalid_count += 1

    return results, invalid_count


def remove_invalid_urls(data, results):
    """Remove invalid entries from data"""
    invalid_urls = {r['url'] for r in results if not r['valid']}

    for source in data.get('sources', []):
        original_count = len(source.get('lotteries', []))
        source['lotteries'] = [
            lottery for lottery in source.get('lotteries', [])
            if lottery.get('detail_url') not in invalid_urls
        ]
        removed_count = original_count - len(source['lotteries'])
        if removed_count > 0:
            logger.info(f"Removed {removed_count} invalid entries from {source.get('source', 'unknown')}")

    return data


def save_json(data):
    """Save modified JSON back to file"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Updated {DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Verify all detail_urls in all_lotteries.json'
    )
    parser.add_argument(
        '--remove',
        action='store_true',
        help='Remove invalid entries from all_lotteries.json'
    )
    args = parser.parse_args()

    # Load JSON
    data = load_json()
    if data is None:
        sys.exit(1)

    logger.info(f"Verifying URLs from {DATA_FILE}\n")

    # Verify all URLs
    results, invalid_count = verify_all_urls(data)

    logger.info(f"\n{'='*60}")
    logger.info(f"Total URLs: {len(results)}")
    logger.info(f"Valid: {len(results) - invalid_count}")
    logger.info(f"Invalid: {invalid_count}")

    # Remove invalid entries if requested
    if args.remove and invalid_count > 0:
        logger.info(f"\nRemoving {invalid_count} invalid entries...")
        data = remove_invalid_urls(data, results)
        save_json(data)

    # Exit code: 0 if all valid, 1 if any invalid
    sys.exit(0 if invalid_count == 0 else 1)


if __name__ == '__main__':
    main()
