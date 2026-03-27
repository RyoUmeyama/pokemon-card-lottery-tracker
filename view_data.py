"""
収集したポケモンカード抽選情報を見やすく表示
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def load_data(filename='data/all_lotteries.json'):
    """データを読み込み"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def display_summary(data):
    """サマリー表示"""
    logger.info("=" * 80)
    logger.info("📊 ポケモンカード抽選・販売情報サマリー")
    logger.info("=" * 80)

    timestamp = datetime.fromisoformat(data['timestamp'])
    logger.info(f"\n最終更新: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}")

    for source in data['sources']:
        logger.info(f"\n【{source['source']}】")

        if source['source'] == 'pokemoncenter-online.com':
            status = "✅ 抽選実施中" if source.get('has_active_lottery') else "⚠️ 現在抽選なし"
            logger.info(f"  状態: {status}")

        logger.info(f"  データ件数: {len(source['lotteries'])}件")

        if source.get('update_date'):
            logger.info(f"  情報更新日: {source['update_date']}")


def display_lotteries(data, limit=20):
    """抽選情報を詳しく表示"""
    logger.info("\n" + "=" * 80)
    logger.info("📝 商品情報一覧")
    logger.info("=" * 80)

    all_lotteries = []
    for source in data['sources']:
        for lottery in source['lotteries']:
            lottery['_source'] = source['source']
            all_lotteries.append(lottery)

    # 表示件数を制限
    display_count = min(limit, len(all_lotteries))

    for i, lottery in enumerate(all_lotteries[:display_count], 1):
        logger.info(f"\n{i}. ", end="")

        # 店舗/日時
        store_info = lottery.get('store', '')
        if '(' in store_info and ')' in store_info:
            # 日時が含まれている場合
            logger.info(f"🕐 {store_info}")
        else:
            logger.info(f"🏪 {store_info}")

        # 商品名
        product = lottery.get('product', '')
        if product:
            # 長い商品名は改行
            if len(product) > 70:
                logger.info(f"   📦 {product[:70]}...")
                logger.info(f"      {product[70:]}")
            else:
                logger.info(f"   📦 {product}")

        # 抽選形式
        lottery_type = lottery.get('lottery_type', '')
        if lottery_type:
            logger.info(f"   🎯 {lottery_type}")

        # 期間情報
        start_date = lottery.get('start_date', '')
        end_date = lottery.get('end_date', '')
        if start_date or end_date:
            period = f"開始: {start_date}" if start_date else ""
            if end_date:
                period += f" / 終了: {end_date}" if period else f"終了: {end_date}"
            logger.info(f"   📅 {period}")

        # 当選発表
        announcement = lottery.get('announcement_date', '')
        if announcement:
            logger.info(f"   🎊 当選発表: {announcement}")

        # 応募条件
        conditions = lottery.get('conditions', '')
        if conditions and len(conditions) > 5:
            logger.info(f"   ℹ️ {conditions[:100]}")

        # URL
        url = lottery.get('detail_url', '')
        if url and url.startswith('http'):
            logger.info(f"   🔗 {url}")

        # ソース
        logger.info(f"   📌 出典: {lottery.get('_source', 'unknown')}")

    if len(all_lotteries) > display_count:
        logger.info(f"\n... 他 {len(all_lotteries) - display_count} 件のデータがあります")
        logger.info(f"すべて表示するには: python view_data.py --all")


def main():
    import sys

    # データ読み込み
    try:
        data = load_data()
    except FileNotFoundError:
        logger.error("❌ データファイルが見つかりません")
        logger.info("まず python main.py を実行してデータを収集してください")
        return

    # 表示件数の設定
    limit = None if '--all' in sys.argv else 20

    # サマリー表示
    display_summary(data)

    # 詳細表示
    display_lotteries(data, limit=limit or 999999)

    logger.info("\n" + "=" * 80)


if __name__ == '__main__':
    main()
