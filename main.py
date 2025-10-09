"""
ポケモンカード抽選情報収集メインスクリプト
"""
import json
import os
from datetime import datetime
from scrapers.nyuka_now_scraper import NyukaNowScraper
from scrapers.pokemon_center_scraper import PokemonCenterScraper
from scrapers.rakuten_books_scraper import RakutenBooksScraper


def load_previous_data(filename):
    """前回のデータを読み込み"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_data(data, filename):
    """データを保存"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def detect_changes(old_data, new_data):
    """変更を検出"""
    if not old_data:
        return True, "初回実行"

    changes = []

    # 抽選数の変化をチェック
    old_count = len(old_data.get('lotteries', []))
    new_count = len(new_data.get('lotteries', []))

    if old_count != new_count:
        changes.append(f"抽選数が変化: {old_count} → {new_count}")

    # 新しい抽選をチェック
    old_products = {l.get('product', '') for l in old_data.get('lotteries', [])}
    new_products = {l.get('product', '') for l in new_data.get('lotteries', [])}

    added = new_products - old_products
    if added:
        changes.append(f"新規抽選: {', '.join(added)}")

    removed = old_products - new_products
    if removed:
        changes.append(f"終了抽選: {', '.join(removed)}")

    return len(changes) > 0, changes


def main():
    """メイン処理"""
    print("=" * 60)
    print("ポケモンカード抽選情報収集開始")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'sources': []
    }

    # 1. 入荷Nowをスクレイピング
    print("\n[1/3] 入荷Nowをチェック中...")
    nyuka_scraper = NyukaNowScraper()
    nyuka_data = nyuka_scraper.scrape()

    if nyuka_data:
        all_results['sources'].append(nyuka_data)
        print(f"✓ 入荷Now: {len(nyuka_data['lotteries'])}件の抽選情報を取得")

        # 変更検出
        prev_data = load_previous_data('data/nyuka_now_latest.json')
        has_changes, changes = detect_changes(prev_data, nyuka_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(nyuka_data, 'data/nyuka_now_latest.json')
    else:
        print("✗ 入荷Nowの取得に失敗")

    # 2. 楽天ブックスをスクレイピング
    print("\n[2/3] 楽天ブックスをチェック中...")
    rakuten_scraper = RakutenBooksScraper()
    rakuten_data = rakuten_scraper.scrape()

    if rakuten_data:
        all_results['sources'].append(rakuten_data)
        print(f"✓ 楽天ブックス: {len(rakuten_data['lotteries'])}件の抽選情報を取得")

        # 変更検出
        prev_data = load_previous_data('data/rakuten_books_latest.json')
        has_changes, changes = detect_changes(prev_data, rakuten_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(rakuten_data, 'data/rakuten_books_latest.json')
    else:
        print("✗ 楽天ブックスの取得に失敗")

    # 3. ポケモンセンター公式をスクレイピング
    print("\n[3/3] ポケモンセンター公式をチェック中...")
    pokemon_center_scraper = PokemonCenterScraper()
    pokemon_center_data = pokemon_center_scraper.scrape()

    if pokemon_center_data:
        all_results['sources'].append(pokemon_center_data)
        status = "実施中" if pokemon_center_data['has_active_lottery'] else "なし"
        print(f"✓ ポケモンセンター公式: 抽選{status}")

        # 変更検出
        prev_data = load_previous_data('data/pokemon_center_latest.json')
        if prev_data and prev_data.get('has_active_lottery') != pokemon_center_data.get('has_active_lottery'):
            print(f"  ⚠️ 抽選状態が変化しました!")

        save_data(pokemon_center_data, 'data/pokemon_center_latest.json')
    else:
        print("✗ ポケモンセンター公式の取得に失敗")

    # 統合データを保存
    save_data(all_results, 'data/all_lotteries.json')

    print("\n" + "=" * 60)
    print("収集完了")
    print("=" * 60)

    # サマリー表示
    total_lotteries = sum(len(s.get('lotteries', [])) for s in all_results['sources'])
    print(f"\n合計: {total_lotteries}件の抽選情報を収集")


if __name__ == '__main__':
    main()
