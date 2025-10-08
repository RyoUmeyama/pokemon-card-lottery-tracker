"""
ポケモンカード抽選情報のHTMLレポート生成
"""
import json
from datetime import datetime
from pathlib import Path


def load_data(filename='data/all_lotteries.json'):
    """データを読み込み"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_html_report(data, output_file='data/lottery_report.html'):
    """HTMLレポートを生成"""

    timestamp = datetime.fromisoformat(data['timestamp'])

    # 全抽選情報を収集
    all_lotteries = []
    for source in data['sources']:
        for lottery in source['lotteries']:
            lottery['_source'] = source['source']
            all_lotteries.append(lottery)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ポケモンカード抽選・販売情報</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}

        header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .summary {{
            background: #f8f9fa;
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .summary h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
        }}

        .filter-controls {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .filter-controls input {{
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #ddd;
            border-radius: 25px;
            font-size: 1em;
            transition: border-color 0.3s;
        }}

        .filter-controls input:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .lotteries {{
            padding: 30px;
        }}

        .lottery-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}

        .lottery-card:hover {{
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
            border-color: #667eea;
        }}

        .lottery-card .header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}

        .lottery-card .store {{
            font-size: 1.1em;
            color: #667eea;
            font-weight: bold;
        }}

        .lottery-card .source {{
            background: #e0e7ff;
            color: #667eea;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .lottery-card .product {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 15px;
            line-height: 1.5;
            font-weight: 600;
        }}

        .lottery-card .detail-row {{
            display: flex;
            align-items: start;
            margin: 10px 0;
            color: #555;
        }}

        .lottery-card .detail-row .icon {{
            width: 25px;
            margin-right: 10px;
            flex-shrink: 0;
        }}

        .lottery-card .detail-row .content {{
            flex: 1;
        }}

        .lottery-card .lottery-type {{
            display: inline-block;
            background: #ffd700;
            color: #333;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            margin: 10px 0;
        }}

        .lottery-card a {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            margin-top: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 600;
        }}

        .lottery-card a:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}

        .no-results .emoji {{
            font-size: 4em;
            margin-bottom: 20px;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.8em;
            }}

            .lottery-card .header {{
                flex-direction: column;
                gap: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎴 ポケモンカード抽選・販売情報</h1>
            <div class="subtitle">最終更新: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}</div>
        </header>

        <div class="summary">
            <h2>📊 サマリー</h2>
            <div class="stats">
"""

    # サマリー統計
    for source in data['sources']:
        status_text = ""
        if source['source'] == 'pokemoncenter-online.com':
            status_text = "✅ 抽選実施中" if source.get('has_active_lottery') else "⚠️ 現在抽選なし"

        html_content += f"""
                <div class="stat-card">
                    <div class="number">{len(source['lotteries'])}</div>
                    <div class="label">{source['source']}</div>
                    {f'<div style="margin-top: 10px; color: #667eea;">{status_text}</div>' if status_text else ''}
                </div>
"""

    html_content += f"""
            </div>
        </div>

        <div class="filter-controls">
            <input type="text" id="searchBox" placeholder="🔍 商品名、店舗名、抽選形式で検索..." onkeyup="filterLotteries()">
        </div>

        <div class="lotteries" id="lotteriesList">
"""

    # 各抽選情報をカード形式で表示
    for i, lottery in enumerate(all_lotteries, 1):
        store = lottery.get('store', '')
        product = lottery.get('product', '')
        lottery_type = lottery.get('lottery_type', '')
        start_date = lottery.get('start_date', '')
        end_date = lottery.get('end_date', '')
        announcement = lottery.get('announcement_date', '')
        conditions = lottery.get('conditions', '')
        url = lottery.get('detail_url', '')
        source = lottery.get('_source', 'unknown')

        html_content += f"""
            <div class="lottery-card" data-search="{product.lower()} {store.lower()} {lottery_type.lower()}">
                <div class="header">
                    <div class="store">{'🕐' if '(' in store and ')' in store else '🏪'} {store}</div>
                    <div class="source">📌 {source}</div>
                </div>

                <div class="product">📦 {product}</div>
"""

        if lottery_type:
            html_content += f"""
                <div class="lottery-type">🎯 {lottery_type}</div>
"""

        if start_date or end_date:
            period_text = ""
            if start_date:
                period_text += f"開始: {start_date}"
            if end_date:
                period_text += f" / 終了: {end_date}" if period_text else f"終了: {end_date}"

            html_content += f"""
                <div class="detail-row">
                    <div class="icon">📅</div>
                    <div class="content">{period_text}</div>
                </div>
"""

        if announcement:
            html_content += f"""
                <div class="detail-row">
                    <div class="icon">🎊</div>
                    <div class="content">当選発表: {announcement}</div>
                </div>
"""

        if conditions and len(conditions) > 5:
            html_content += f"""
                <div class="detail-row">
                    <div class="icon">ℹ️</div>
                    <div class="content">{conditions[:200]}{'...' if len(conditions) > 200 else ''}</div>
                </div>
"""

        if url and url.startswith('http'):
            html_content += f"""
                <a href="{url}" target="_blank">🔗 詳細を見る</a>
"""

        html_content += """
            </div>
"""

    if not all_lotteries:
        html_content += """
            <div class="no-results">
                <div class="emoji">🔍</div>
                <div>現在、抽選・販売情報はありません</div>
            </div>
"""

    html_content += f"""
        </div>

        <footer>
            <p>🤖 自動収集システム | データ件数: {len(all_lotteries)}件</p>
        </footer>
    </div>

    <script>
        function filterLotteries() {{
            const searchText = document.getElementById('searchBox').value.toLowerCase();
            const cards = document.querySelectorAll('.lottery-card');
            let visibleCount = 0;

            cards.forEach(card => {{
                const searchData = card.getAttribute('data-search');
                if (searchData.includes(searchText)) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            // 検索結果がない場合のメッセージ表示
            const lotteriesList = document.getElementById('lotteriesList');
            let noResultsDiv = document.getElementById('noResults');

            if (visibleCount === 0 && searchText !== '') {{
                if (!noResultsDiv) {{
                    noResultsDiv = document.createElement('div');
                    noResultsDiv.id = 'noResults';
                    noResultsDiv.className = 'no-results';
                    noResultsDiv.innerHTML = '<div class="emoji">🔍</div><div>検索結果が見つかりませんでした</div>';
                    lotteriesList.appendChild(noResultsDiv);
                }}
                noResultsDiv.style.display = 'block';
            }} else if (noResultsDiv) {{
                noResultsDiv.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>
"""

    # HTMLファイルを出力
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_file


def main():
    try:
        data = load_data()
        output_file = generate_html_report(data)
        print(f"✅ HTMLレポートを生成しました: {output_file}")
        print(f"\nブラウザで開くには:")
        print(f"  open {output_file}")
    except FileNotFoundError:
        print("❌ データファイルが見つかりません")
        print("まず python main.py を実行してデータを収集してください")


if __name__ == '__main__':
    main()
