"""
ポケモンカード抽選情報収集メインスクリプト
"""
import json
import os
from datetime import datetime
from scrapers.nyuka_now_scraper import NyukaNowScraper
from scrapers.pokemon_center_scraper import PokemonCenterScraper
from scrapers.pokemoncenter_playwright_scraper import PokemonCenterPlaywrightScraper
from scrapers.rakuten_books_scraper import RakutenBooksScraper
from scrapers.amazon_reservation_scraper import AmazonReservationScraper
from scrapers.rakuten_reservation_scraper import RakutenReservationScraper
from scrapers.yodobashi_scraper import YodobashiScraper
from scrapers.x_lottery_scraper import XLotteryScraper
# 家電量販店 (Playwright版)
from scrapers.biccamera_playwright_scraper import BiccameraPlaywrightScraper
from scrapers.joshin_playwright_scraper import JoshinPlaywrightScraper
from scrapers.edion_playwright_scraper import EdionPlaywrightScraper
from scrapers.ksdenki_scraper import KsDenkiScraper
from scrapers.nojima_scraper import NojimaScraper
# ホビーショップ
# あみあみはサプライ品中心のため除外
from scrapers.yellow_submarine_scraper import YellowSubmarineScraper
from scrapers.cardshop_serra_scraper import CardShopSerraScraper
# コンビニ・小売 (Playwright版)
from scrapers.sevennet_playwright_scraper import SevenNetPlaywrightScraper
from scrapers.seven_eleven_scraper import SevenElevenScraper
from scrapers.lawson_scraper import LawsonScraper
from scrapers.aeon_playwright_scraper import AeonPlaywrightScraper
from scrapers.familymart_scraper import FamilyMartScraper


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


def detect_reservation_changes(old_data, new_data):
    """予約情報の変更を検出"""
    if not old_data:
        return True, "初回実行"

    changes = []

    # 予約商品数の変化をチェック
    old_count = len(old_data.get('reservations', []))
    new_count = len(new_data.get('reservations', []))

    if old_count != new_count:
        changes.append(f"予約商品数が変化: {old_count} → {new_count}")

    # 新しい予約商品をチェック
    old_products = {r.get('title', '') for r in old_data.get('reservations', [])}
    new_products = {r.get('title', '') for r in new_data.get('reservations', [])}

    added = new_products - old_products
    if added:
        added_list = list(added)[:3]  # 最大3件表示
        more = len(added) - 3
        if more > 0:
            changes.append(f"新規予約: {', '.join(added_list)} 他{more}件")
        else:
            changes.append(f"新規予約: {', '.join(added_list)}")

    removed = old_products - new_products
    if removed:
        changes.append(f"予約終了: {len(removed)}件")

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

    total_sources = 21  # 全ソース数

    # 1. 入荷Nowをスクレイピング（在庫チェック有効）
    print(f"\n[1/{total_sources}] 入荷Nowをチェック中...")
    nyuka_scraper = NyukaNowScraper(check_availability=True)
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
    print(f"\n[2/{total_sources}] 楽天ブックスをチェック中...")
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

    # 3. ポケモンセンター公式をスクレイピング (通常版)
    print(f"\n[3/{total_sources}] ポケモンセンター公式をチェック中...")
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

    # 3.5. ポケモンセンター公式をスクレイピング (Playwright版 - JS対応)
    print(f"\n[4/{total_sources}] ポケモンセンター公式(Playwright)をチェック中...")
    pokemon_center_pw_scraper = PokemonCenterPlaywrightScraper()
    pokemon_center_pw_data = pokemon_center_pw_scraper.scrape()

    if pokemon_center_pw_data:
        # 通常版と結果が異なる場合のみ追加
        pw_lottery_count = len(pokemon_center_pw_data.get('lotteries', []))
        if pw_lottery_count > 0:
            all_results['sources'].append(pokemon_center_pw_data)
            print(f"✓ ポケモンセンター公式(Playwright): {pw_lottery_count}件の抽選情報を取得")
        else:
            print(f"✓ ポケモンセンター公式(Playwright): 抽選なし（通常版と同じ）")
    else:
        print("✗ ポケモンセンター公式(Playwright)の取得に失敗")

    # 5. Amazon予約情報をスクレイピング
    print(f"\n[5/{total_sources}] Amazon予約情報をチェック中...")
    amazon_scraper = AmazonReservationScraper()
    amazon_data = amazon_scraper.scrape()

    if amazon_data:
        all_results['sources'].append(amazon_data)
        reservation_count = len(amazon_data.get('reservations', []))
        print(f"✓ Amazon: {reservation_count}件の予約可能商品を取得")

        # 変更検出（新規予約を検出）
        prev_data = load_previous_data('data/amazon_reservation_latest.json')
        has_changes, changes = detect_reservation_changes(prev_data, amazon_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(amazon_data, 'data/amazon_reservation_latest.json')
    else:
        print("✗ Amazon予約情報の取得に失敗")

    # 6. 楽天ブックス予約情報をスクレイピング
    print(f"\n[6/{total_sources}] 楽天ブックス予約情報をチェック中...")
    rakuten_reservation_scraper = RakutenReservationScraper()
    rakuten_reservation_data = rakuten_reservation_scraper.scrape()

    if rakuten_reservation_data:
        all_results['sources'].append(rakuten_reservation_data)
        reservation_count = len(rakuten_reservation_data.get('reservations', []))
        print(f"✓ 楽天ブックス: {reservation_count}件の予約可能商品を取得")

        # 変更検出
        prev_data = load_previous_data('data/rakuten_reservation_latest.json')
        has_changes, changes = detect_reservation_changes(prev_data, rakuten_reservation_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(rakuten_reservation_data, 'data/rakuten_reservation_latest.json')
    else:
        print("✗ 楽天ブックス予約情報の取得に失敗")

    # 7. ヨドバシカメラをスクレイピング
    print(f"\n[7/{total_sources}] ヨドバシカメラをチェック中...")
    yodobashi_scraper = YodobashiScraper()
    yodobashi_data = yodobashi_scraper.scrape()

    if yodobashi_data:
        all_results['sources'].append(yodobashi_data)
        lottery_count = len(yodobashi_data.get('lotteries', []))
        print(f"✓ ヨドバシカメラ: {lottery_count}件の抽選情報を取得")

        # 変更検出
        prev_data = load_previous_data('data/yodobashi_latest.json')
        has_changes, changes = detect_changes(prev_data, yodobashi_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(yodobashi_data, 'data/yodobashi_latest.json')
    else:
        print("✗ ヨドバシカメラの取得に失敗")

    # 8. ビックカメラをスクレイピング (Playwright版)
    print(f"\n[8/{total_sources}] ビックカメラをチェック中...")
    biccamera_scraper = BiccameraPlaywrightScraper()
    biccamera_data = biccamera_scraper.scrape()

    if biccamera_data:
        all_results['sources'].append(biccamera_data)
        lottery_count = len(biccamera_data.get('lotteries', []))
        print(f"✓ ビックカメラ: {lottery_count}件の抽選情報を取得")

        # 変更検出
        prev_data = load_previous_data('data/biccamera_latest.json')
        has_changes, changes = detect_changes(prev_data, biccamera_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(biccamera_data, 'data/biccamera_latest.json')
    else:
        print("✗ ビックカメラの取得に失敗")

    # 9. X(Twitter)公式アカウントをスクレイピング
    print(f"\n[9/{total_sources}] X(Twitter)公式アカウントをチェック中...")
    x_scraper = XLotteryScraper()
    x_data = x_scraper.scrape()

    if x_data:
        all_results['sources'].append(x_data)
        lottery_count = len(x_data.get('lotteries', []))
        if x_data.get('error'):
            print(f"⚠️ X(Twitter): {x_data['error']}")
        else:
            print(f"✓ X(Twitter): {lottery_count}件の抽選情報を取得")

        # 変更検出
        prev_data = load_previous_data('data/x_lottery_latest.json')
        has_changes, changes = detect_changes(prev_data, x_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(x_data, 'data/x_lottery_latest.json')
    else:
        print("✗ X(Twitter)の取得に失敗")

    # ===== 家電量販店 =====

    # 10. ジョーシンをスクレイピング (Playwright版)
    print(f"\n[10/{total_sources}] ジョーシンをチェック中...")
    joshin_scraper = JoshinPlaywrightScraper()
    joshin_data = joshin_scraper.scrape()

    if joshin_data:
        all_results['sources'].append(joshin_data)
        lottery_count = len(joshin_data.get('lotteries', []))
        print(f"✓ ジョーシン: {lottery_count}件の抽選情報を取得")

        prev_data = load_previous_data('data/joshin_latest.json')
        has_changes, changes = detect_changes(prev_data, joshin_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(joshin_data, 'data/joshin_latest.json')
    else:
        print("✗ ジョーシンの取得に失敗")

    # 11. エディオンをスクレイピング (Playwright版)
    print(f"\n[11/{total_sources}] エディオンをチェック中...")
    edion_scraper = EdionPlaywrightScraper()
    edion_data = edion_scraper.scrape()

    if edion_data:
        all_results['sources'].append(edion_data)
        lottery_count = len(edion_data.get('lotteries', []))
        print(f"✓ エディオン: {lottery_count}件の抽選情報を取得")

        prev_data = load_previous_data('data/edion_latest.json')
        has_changes, changes = detect_changes(prev_data, edion_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(edion_data, 'data/edion_latest.json')
    else:
        print("✗ エディオンの取得に失敗")

    # 12. ケーズデンキをスクレイピング
    print(f"\n[12/{total_sources}] ケーズデンキをチェック中...")
    ksdenki_scraper = KsDenkiScraper()
    ksdenki_data = ksdenki_scraper.scrape()

    if ksdenki_data:
        all_results['sources'].append(ksdenki_data)
        lottery_count = len(ksdenki_data.get('lotteries', []))
        print(f"✓ ケーズデンキ: {lottery_count}件の抽選情報を取得")

        prev_data = load_previous_data('data/ksdenki_latest.json')
        has_changes, changes = detect_changes(prev_data, ksdenki_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(ksdenki_data, 'data/ksdenki_latest.json')
    else:
        print("✗ ケーズデンキの取得に失敗")

    # 13. ノジマをスクレイピング
    print(f"\n[13/{total_sources}] ノジマをチェック中...")
    nojima_scraper = NojimaScraper()
    nojima_data = nojima_scraper.scrape()

    if nojima_data:
        all_results['sources'].append(nojima_data)
        lottery_count = len(nojima_data.get('lotteries', []))
        print(f"✓ ノジマ: {lottery_count}件の抽選情報を取得")

        prev_data = load_previous_data('data/nojima_latest.json')
        has_changes, changes = detect_changes(prev_data, nojima_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(nojima_data, 'data/nojima_latest.json')
    else:
        print("✗ ノジマの取得に失敗")

    # ===== ホビーショップ =====

    # 14. あみあみをスクレイピング (スキップ - サプライ品中心のため除外)
    print(f"\n[14/{total_sources}] あみあみをスキップ（サプライ品中心のため除外）")

    # 15. イエローサブマリンをスクレイピング
    print(f"\n[15/{total_sources}] イエローサブマリンをチェック中...")
    yellow_submarine_scraper = YellowSubmarineScraper()
    yellow_submarine_data = yellow_submarine_scraper.scrape()

    if yellow_submarine_data:
        all_results['sources'].append(yellow_submarine_data)
        lottery_count = len(yellow_submarine_data.get('lotteries', []))
        print(f"✓ イエローサブマリン: {lottery_count}件の予約情報を取得")

        prev_data = load_previous_data('data/yellow_submarine_latest.json')
        has_changes, changes = detect_changes(prev_data, yellow_submarine_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(yellow_submarine_data, 'data/yellow_submarine_latest.json')
    else:
        print("✗ イエローサブマリンの取得に失敗")

    # 16. カードショップセラをスクレイピング
    print(f"\n[16/{total_sources}] カードショップセラをチェック中...")
    cardshop_serra_scraper = CardShopSerraScraper()
    cardshop_serra_data = cardshop_serra_scraper.scrape()

    if cardshop_serra_data:
        all_results['sources'].append(cardshop_serra_data)
        lottery_count = len(cardshop_serra_data.get('lotteries', []))
        print(f"✓ カードショップセラ: {lottery_count}件の予約情報を取得")

        prev_data = load_previous_data('data/cardshop_serra_latest.json')
        has_changes, changes = detect_changes(prev_data, cardshop_serra_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(cardshop_serra_data, 'data/cardshop_serra_latest.json')
    else:
        print("✗ カードショップセラの取得に失敗")

    # ===== コンビニ・小売 =====

    # 17. セブンネットショッピングをスクレイピング (通常版・在庫チェック有効)
    print(f"\n[17/{total_sources}] セブンネットショッピングをチェック中...")
    seven_eleven_scraper = SevenElevenScraper(check_availability=True)
    seven_eleven_data = seven_eleven_scraper.scrape()

    if seven_eleven_data:
        all_results['sources'].append(seven_eleven_data)
        lottery_count = len(seven_eleven_data.get('lotteries', []))
        print(f"✓ セブンネットショッピング: {lottery_count}件の予約情報を取得")

        prev_data = load_previous_data('data/seven_eleven_latest.json')
        has_changes, changes = detect_changes(prev_data, seven_eleven_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(seven_eleven_data, 'data/seven_eleven_latest.json')
    else:
        print("✗ セブンネットショッピングの取得に失敗")

    # 18. セブンネットショッピングをスクレイピング (Playwright版 - 抽選専用)
    print(f"\n[18/{total_sources}] セブンネット抽選ページ(Playwright)をチェック中...")
    sevennet_pw_scraper = SevenNetPlaywrightScraper()
    sevennet_pw_data = sevennet_pw_scraper.scrape()

    if sevennet_pw_data:
        pw_lottery_count = len(sevennet_pw_data.get('lotteries', []))
        if pw_lottery_count > 0:
            all_results['sources'].append(sevennet_pw_data)
            print(f"✓ セブンネット抽選(Playwright): {pw_lottery_count}件の抽選情報を取得")
            save_data(sevennet_pw_data, 'data/sevennet_lottery_latest.json')
        else:
            print(f"✓ セブンネット抽選(Playwright): 抽選情報なし")
    else:
        print("✗ セブンネット抽選(Playwright)の取得に失敗")

    # 19. ローソンHMVをスクレイピング
    print(f"\n[19/{total_sources}] ローソンHMVをチェック中...")
    lawson_scraper = LawsonScraper()
    lawson_data = lawson_scraper.scrape()

    if lawson_data:
        all_results['sources'].append(lawson_data)
        lottery_count = len(lawson_data.get('lotteries', []))
        print(f"✓ ローソンHMV: {lottery_count}件の予約情報を取得")

        prev_data = load_previous_data('data/lawson_latest.json')
        has_changes, changes = detect_changes(prev_data, lawson_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(lawson_data, 'data/lawson_latest.json')
    else:
        print("✗ ローソンHMVの取得に失敗")

    # 20. イオンをスクレイピング (Playwright版)
    print(f"\n[20/{total_sources}] イオンをチェック中...")
    aeon_scraper = AeonPlaywrightScraper()
    aeon_data = aeon_scraper.scrape()

    if aeon_data:
        all_results['sources'].append(aeon_data)
        lottery_count = len(aeon_data.get('lotteries', []))
        print(f"✓ イオン: {lottery_count}件の予約情報を取得")

        prev_data = load_previous_data('data/aeon_latest.json')
        has_changes, changes = detect_changes(prev_data, aeon_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(aeon_data, 'data/aeon_latest.json')
    else:
        print("✗ イオンの取得に失敗")

    # 21. ファミリーマートをスクレイピング
    print(f"\n[21/{total_sources}] ファミリーマートをチェック中...")
    familymart_scraper = FamilyMartScraper()
    familymart_data = familymart_scraper.scrape()

    if familymart_data:
        all_results['sources'].append(familymart_data)
        lottery_count = len(familymart_data.get('lotteries', []))
        print(f"✓ ファミリーマート: {lottery_count}件の抽選情報を取得")

        prev_data = load_previous_data('data/familymart_latest.json')
        has_changes, changes = detect_changes(prev_data, familymart_data)
        if has_changes:
            print(f"  変更検出: {changes}")

        save_data(familymart_data, 'data/familymart_latest.json')
    else:
        print("✗ ファミリーマートの取得に失敗")

    # 統合データを保存
    save_data(all_results, 'data/all_lotteries.json')

    print("\n" + "=" * 60)
    print("収集完了")
    print("=" * 60)

    # サマリー表示
    total_lotteries = sum(len(s.get('lotteries', [])) for s in all_results['sources'])
    total_reservations = sum(len(s.get('reservations', [])) for s in all_results['sources'])
    print(f"\n合計: {total_lotteries}件の抽選情報、{total_reservations}件の予約情報を収集")

    # Gmail通知
    if os.environ.get('ENABLE_EMAIL_NOTIFICATION') == 'true':
        print("\n📧 メール通知を送信中...")
        from notify import GmailNotifier
        notifier = GmailNotifier()
        notifier.send_notification(all_results)


if __name__ == '__main__':
    main()
