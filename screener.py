import datetime
import os
import sys
import json
import pandas as pd
import yfinance as yf
from tqdm import tqdm

def get_sp500_tickers():
    """S&P 500の全500銘柄のティッカーリストを確実に入手する"""
    print("S&P 500の最新銘柄リストを取得中...")
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"-> S&P 500の {len(tickers)} 銘柄を正常に取得しました。")
        return tickers
    except Exception as e:
        print(f"一次ソースのエラーのため、代替ルートで取得を試みます... ({e})")
        try:
            url_fallback = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url_fallback)
            df = tables[0]
            tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
            return tickers
        except Exception:
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

def load_tickers_from_file(file_path, is_japan=False):
    """テキストファイルからティッカーを読み込む（日本株用）"""
    if not os.path.exists(file_path):
        return []
    tickers = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            ticker = line.strip()
            if not ticker or ticker.startswith("#"):
                continue
            if is_japan and not ticker.endswith(".T"):
                ticker = f"{ticker}.T"
            tickers.append(ticker)
    return tickers

# def check_52week_high(ticker_list, lookback_days=15):
#     """過去3週間（15営業日）の間に52週新高値を更新した回数をカウントし、直近2週間（10営業日）のローソク足データも取得する"""
#     results = []
#     end_date = datetime.date.today()
#     start_date = end_date - datetime.timedelta(days=365 * 2)

#     print(f"\nYahoo Financeから全株価データを一括ダウンロード中...")
#     try:
#         all_data = yf.download(ticker_list, start=start_date, end=end_date, group_by='ticker', progress=False)
#     except Exception as e:
#         print(f"データのダウンロード中にエラーが発生しました: {e}")
#         return pd.DataFrame()

#     for ticker_symbol in tqdm(ticker_list, desc="スクリーニング中"):
#         try:
#             if ticker_symbol not in all_data.columns.levels[0]:
#                 continue
#             df = all_data[ticker_symbol].dropna()

#             if len(df) < 252:
#                 continue

#             high_count = 0
#             for i in range(-lookback_days, 0):
#                 if abs(i) > len(df):
#                     continue
#                 target_day_high = df["High"].iloc[i]
#                 past_52w_high = df["High"].iloc[i - 252 : i].max()

#                 if target_day_high >= past_52w_high:
#                     high_count += 1

#             if high_count > 0:
#                 current_price = df["Close"].iloc[-1]
#                 latest_52w_high = df["High"].iloc[-252:].max()
                
#                 # 直近2週間（15営業日分）のOHLCデータを抽出
#                 candles_df = df.tail(15)
#                 candles_data = []
#                 for _, r in candles_df.iterrows():
#                     candles_data.append([
#                         round(r["Open"], 2),
#                         round(r["High"], 2),
#                         round(r["Low"], 2),
#                         round(r["Close"], 2)
#                     ])

#                 results.append({
#                     "Ticker": ticker_symbol,
#                     "High_Count": high_count,
#                     "Current_Price": round(current_price, 2),
#                     "52W_High_Price": round(latest_52w_high, 2),
#                     "Candles": json.dumps(candles_data)  # JSON文字列として保存
#                 })
#         except Exception:
#             continue

#     res_df = pd.DataFrame(results)
#     if not res_df.empty:
#         res_df = res_df.sort_values(by="High_Count", ascending=False).reset_index(drop=True)
#     return res_df

def check_52week_high(ticker_list, lookback_days=15):
    """過去3週間（15営業日）の間に52週新高値を更新した回数をカウントし、直近3週間のローソク足と業種データも取得する"""
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)

    print(f"\nYahoo Financeから全株価データを一括ダウンロード中...")
    try:
        all_data = yf.download(ticker_list, start=start_date, end=end_date, group_by='ticker', progress=False)
    except Exception as e:
        print(f"データのダウンロード中にエラーが発生しました: {e}")
        return pd.DataFrame()

    for ticker_symbol in tqdm(ticker_list, desc="スクリーニング中"):
        try:
            if ticker_symbol not in all_data.columns.levels[0]:
                continue
            df = all_data[ticker_symbol].dropna()

            if len(df) < 252:
                continue

            high_count = 0
            for i in range(-lookback_days, 0):
                if abs(i) > len(df):
                    continue
                target_day_high = df["High"].iloc[i]
                past_52w_high = df["High"].iloc[i - 252 : i].max()

                if target_day_high >= past_52w_high:
                    high_count += 1

            if high_count > 0:
                current_price = df["Close"].iloc[-1]
                latest_52w_high = df["High"].iloc[-252:].max()
                
                # 直近3週間（15営業日分）のOHLCデータを抽出
                candles_df = df.tail(15)
                candles_data = []
                for _, r in candles_df.iterrows():
                    candles_data.append([
                        round(r["Open"], 2),
                        round(r["High"], 2),
                        round(r["Low"], 2),
                        round(r["Close"], 2)
                    ])

                # 💡【追加】ヒットした銘柄のみ業種（セクター）を取得
                try:
                    ticker_info = yf.Ticker(ticker_symbol).info
                    # 日本株と米国株でキーが異なる場合があるため、両対応
                    sector = ticker_info.get("sectorDisp", ticker_info.get("sector", "Unknown"))
                except Exception:
                    sector = "Unknown"

                results.append({
                    "Ticker": ticker_symbol,
                    "High_Count": high_count,
                    "Current_Price": round(current_price, 2),
                    "52W_High_Price": round(latest_52w_high, 2),
                    "Candles": json.dumps(candles_data),
                    "Sector": sector  # 💡【追加】
                })
        except Exception:
            continue

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        res_df = res_df.sort_values(by="High_Count", ascending=False).reset_index(drop=True)
    return res_df


# def generate_html_report(df, output_path, title_suffix=""):
#     """index.htmlとして概要・チャート・直近2週間ローソク足付きレポートを出力する"""
#     now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     table_rows = ""
#     for idx, row in df.iterrows():
#         ticker = row['Ticker']
#         if ".T" in ticker:
#             code = ticker.split('.')[0]
#             symbols_url = f"https://jp.tradingview.com/symbols/TSE-{code}/"
#             chart_url = f"https://jp.tradingview.com/chart/?symbol=TSE:{code}"
#             currency_prefix = "¥"
#         else:
#             symbols_url = f"https://jp.tradingview.com/symbols/{ticker}/"
#             chart_url = f"https://jp.tradingview.com/chart/?symbol={ticker}"
#             currency_prefix = "$"

#         table_rows += f"""
#         <tr>
#             <td>
#                 <span class="ticker-text">{ticker}</span>
#                 <div class="tv-links mt-1">
#                     <a href="{symbols_url}" target="_blank" class="badge badge-info mr-1">概要 📄</a>
#                     <a href="{chart_url}" target="_blank" class="badge badge-primary">チャート 📈</a>
#                 </div>
#             </td>
#             <td class="text-center text-success vertical-middle"><strong>{row['High_Count']} 回</strong></td>
#             <td class="vertical-middle">{currency_prefix}{row['Current_Price']:,}</td>
#             <td class="vertical-middle">{currency_prefix}{row['52W_High_Price']:,}</td>
#             <td class="text-center vertical-middle">
#                 <canvas class="spark-candle" width="160" height="35" data-candles='{row['Candles']}'></canvas>
#             </td>
#         </tr>
#         """

def generate_html_report(df, output_path, title_suffix=""):
    """index.htmlとして概要・チャート・直近3週間ローソク足付きレポートを出力する"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    table_rows = ""
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        sector = row.get('Sector', 'Unknown') # 💡【追加】
        
        if ".T" in ticker:
            code = ticker.split('.')[0]
            symbols_url = f"https://jp.tradingview.com/symbols/TSE-{code}/"
            chart_url = f"https://jp.tradingview.com/chart/?symbol=TSE:{code}"
            currency_prefix = "¥"
        else:
            symbols_url = f"https://jp.tradingview.com/symbols/{ticker}/"
            chart_url = f"https://jp.tradingview.com/chart/?symbol={ticker}"
            currency_prefix = "$"

        table_rows += f"""
        <tr>
            <td>
                <div>
                    <span class="ticker-text">{ticker}</span>
                    <span class="badge badge-secondary ml-1" style="background-color: #6c757d;">{sector}</span>
                </div>
                <div class="tv-links mt-1">
                    <a href="{symbols_url}" target="_blank" class="badge badge-info mr-1">概要 📄</a>
                    <a href="{chart_url}" target="_blank" class="badge badge-primary">チャート 📈</a>
                </div>
            </td>
            <td class="text-center text-success vertical-middle"><strong>{row['High_Count']} 回</strong></td>
            <td class="vertical-middle">{currency_prefix}{row['Current_Price']:,}</td>
            <td class="vertical-middle">{currency_prefix}{row['52W_High_Price']:,}</td>
            <td class="text-center vertical-middle">
                <canvas class="spark-candle" width="160" height="35" data-candles='{row['Candles']}'></canvas>
            </td>
        </tr>
        """
        
    # --- 以下、html_content の文字列やファイル書き込み処理は以前のままでOKです ---
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ 52週新高値更新回数 {title_suffix}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
    <style>
        body {{ background-color: #f8f9fa; color: #333; font-family: 'Helvetica Neue', Arial, sans-serif; }}
        .container {{ margin-top: 30px; margin-bottom: 50px; }}
        .header-section {{ background: linear-gradient(135deg, #1f4037 0%, #99f2c8 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; }}
        .table thead th {{ background-color: #2c3e50; color: white; border: none; vertical-align: middle; }}
        .vertical-middle {{ vertical-align: middle !important; }}
        .ticker-text {{ font-size: 1.1rem; font-weight: bold; color: #2c3e50; }}
        .badge {{ padding: 5px 8px; font-size: 0.75rem; }}
        .spark-candle {{ display: block; margin: 0 auto; }}
        footer {{ text-align: center; margin-top: 30px; color: #777; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-section">
            <h1 class="display-5">📈 52週高値 更新回数ランキング {title_suffix}</h1>
            <p class="lead mb-0">過去3週間（15営業日）の中で、何回52週最高値を更新したかを表示しています</p>
            <hr class="my-2" style="border-color: rgba(255,255,255,0.2);">
            <small>最終更新日時: <strong>{now_str}</strong> | ヒット数: {len(df)} 銘柄</small>
        </div>

        <div class="card p-4">
            <div class="table-responsive">
                <table id="screenerTable" class="table table-hover table-striped table-bordered" style="width:100%">
                    <thead>
                        <tr>
                            <th>ティッカー (Ticker)</th>
                            <th class="text-center">新高値カウント (過去3週間)</th>
                            <th>直近終値 (Current Price)</th>
                            <th>52週最高値 (52W High Price)</th>
                            <th class="text-center">直近2週間トレンド (日足)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        <footer>
            <p>Generated by 52-Week High Screener Tool</p>
        </footer>
    </div>

    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.10.21/js/dataTables.bootstrap4.min.js"></script>
    <script>
        // ローソク足を描画する関数
        function drawCandles() {{
            document.querySelectorAll('.spark-candle').forEach(canvas => {{
                if (canvas.getContext) {{
                    const ctx = canvas.getContext('2d');
                    const rawData = canvas.getAttribute('data-candles');
                    if (!rawData) return;
                    
                    const candles = JSON.parse(rawData); // [[O, H, L, C], ...]
                    if (candles.length === 0) return;

                    // 描画エリアの初期化
                    ctx.clearRect(0, 0, canvas.width, canvas.height);

                    // 2週間分の中での最高値と最安値を計算し、縦幅の基準にする
                    let maxVal = -Infinity;
                    let minVal = Infinity;
                    candles.forEach(c => {{
                        if (c[1] > maxVal) maxVal = c[1];
                        if (c[2] < minVal) minVal = c[2];
                    }});
                    const valRange = maxVal - minVal || 1;

                    // レイアウト計算用変数
                    const padding = 3;
                    const chartHeight = canvas.height - (padding * 2);
                    const numCandles = candles.length;
                    const candleWidth = Math.floor((canvas.width) / numCandles) - 2;

                    candles.forEach((candle, index) => {{
                        const [open, high, low, close] = candle;
                        const isUp = close >= open;

                        // 値をCanvasのY座標に変換するヘルパー関数
                        const getY = (val) => canvas.height - padding - ((val - minVal) / valRange) * chartHeight;

                        const x = index * (candleWidth + 2) + 1;
                        const yHigh = getY(high);
                        const yLow = getY(low);
                        const yOpen = getY(open);
                        const yClose = getY(close);

                        // 色の設定（陽線は緑、陰線は赤）
                        const color = isUp ? '#2ec4b6' : '#e71d36';
                        ctx.strokeStyle = color;
                        ctx.fillStyle = color;
                        ctx.lineWidth = 1;

                        // 1. 髭（ひげ）を描画
                        ctx.beginPath();
                        ctx.moveTo(x + candleWidth / 2, yHigh);
                        ctx.lineTo(x + candleWidth / 2, yLow);
                        ctx.stroke();

                        // 2. 実体を描画
                        const bodyY = Math.min(yOpen, yClose);
                        const bodyHeight = Math.max(Math.abs(yOpen - yClose), 1); // 最低1px確保
                        ctx.fillRect(x, bodyY, candleWidth, bodyHeight);
                    }});
                }}
            }});
        }}

        $(document).ready(function() {{
            const table = $('#screenerTable').DataTable({{
                "order": [[ 1, "desc" ]],
                "pageLength": 50,
                "language": {{
                    "search": "絞り込み検索:",
                    "lengthMenu": "表示 _MENU_ 件",
                    "info": "全 _TOTAL_ 銘柄中 _START_ から _END_ まで表示",
                    "paginate": {{ "next": "次", "previous": "前" }}
                }}
            }});

            // 初回表示時およびページ切り替え・検索時にローソク足を再描画
            drawCandles();
            table.on('draw', function() {{
                drawCandles();
            }});
        }});
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    choice = os.environ.get("SCREENER_CHOICE", "3")
    tickers = []
    title_suffix = ""
    os.makedirs("data", exist_ok=True)

    if choice in ["1", "3"]:
        sp500_tickers = get_sp500_tickers()
        tickers.extend(sp500_tickers)
        title_suffix += "[S&P 500] "

    if choice in ["2", "3"]:
        topix_file = os.path.join("data", "tickers_topix.txt")
        if not os.path.exists(topix_file):
            with open(topix_file, "w") as f:
                f.write("# 日本株コード\n1306\n7203\n6758\n9984\n")
        topix_tickers = load_tickers_from_file(topix_file, is_japan=True)
        tickers.extend(topix_tickers)
        title_suffix += "[TOPIX] "

    if not tickers:
        print("対象ティッカーがありません。")
        exit()

    result_df = check_52week_high(tickers, lookback_days=15)
    html_name = "index.html"
    
    # if result_df is None or result_df.empty:
    #     result_df = pd.DataFrame(columns=["Ticker", "High_Count", "Current_Price", "52W_High_Price", "Candles"])

    if result_df is None or result_df.empty:
    # 💡【修正】"Sector" をカラムに追加
    result_df = pd.DataFrame(columns=["Ticker", "High_Count", "Current_Price", "52W_High_Price", "Candles", "Sector"])
        
    generate_html_report(result_df, html_name, title_suffix)
    print(f"\n[成功] スクリーニング結果を '{html_name}' に上書き保存しました。")


# import datetime
# import os
# import sys
# import pandas as pd
# import yfinance as yf
# from tqdm import tqdm

# def get_sp500_tickers():
#     """S&P 500の全500銘柄のティッカーリストを確実に入手する"""
#     print("S&P 500の最新銘柄リストを取得中...")
#     try:
#         url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
#         df = pd.read_csv(url)
#         tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
#         print(f"-> S&P 500の {len(tickers)} 銘柄を正常に取得しました。")
#         return tickers
#     except Exception as e:
#         print(f"一次ソースのエラーのため、代替ルートで取得を試みます... ({e})")
#         try:
#             url_fallback = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
#             tables = pd.read_html(url_fallback)
#             df = tables[0]
#             tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
#             return tickers
#         except Exception:
#             return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

# def load_tickers_from_file(file_path, is_japan=False):
#     """テキストファイルからティッカーを読み込む（日本株用）"""
#     if not os.path.exists(file_path):
#         return []
#     tickers = []
#     with open(file_path, "r", encoding="utf-8") as f:
#         for line in f:
#             ticker = line.strip()
#             if not ticker or ticker.startswith("#"):
#                 continue
#             if is_japan and not ticker.endswith(".T"):
#                 ticker = f"{ticker}.T"
#             tickers.append(ticker)
#     return tickers

# def check_52week_high(ticker_list, lookback_days=15):
#     """過去3週間（15営業日）の間に52週新高値を更新した回数をカウントする"""
#     results = []
#     end_date = datetime.date.today()
#     start_date = end_date - datetime.timedelta(days=365 * 2)

#     print(f"\nYahoo Financeから全株価データを一括ダウンロード中...")
#     try:
#         all_data = yf.download(ticker_list, start=start_date, end=end_date, group_by='ticker', progress=False)
#     except Exception as e:
#         print(f"データのダウンロード中にエラーが発生しました: {e}")
#         return pd.DataFrame()

#     for ticker_symbol in tqdm(ticker_list, desc="スクリーニング中"):
#         try:
#             if ticker_symbol not in all_data.columns.levels[0]:
#                 continue
#             df = all_data[ticker_symbol].dropna()

#             if len(df) < 252:
#                 continue

#             high_count = 0
#             for i in range(-lookback_days, 0):
#                 if abs(i) > len(df):
#                     continue
#                 target_day_high = df["High"].iloc[i]
#                 past_52w_high = df["High"].iloc[i - 252 : i].max()

#                 if target_day_high >= past_52w_high:
#                     high_count += 1

#             if high_count > 0:
#                 current_price = df["Close"].iloc[-1]
#                 latest_52w_high = df["High"].iloc[-252:].max()
#                 results.append({
#                     "Ticker": ticker_symbol,
#                     "High_Count": high_count,
#                     "Current_Price": round(current_price, 2),
#                     "52W_High_Price": round(latest_52w_high, 2)
#                 })
#         except Exception:
#             continue

#     res_df = pd.DataFrame(results)
#     if not res_df.empty:
#         res_df = res_df.sort_values(by="High_Count", ascending=False).reset_index(drop=True)
#     return res_df

# def generate_html_report(df, output_path, title_suffix=""):
#     """index.htmlとして概要・チャート両方のリンク付きレポートを出力する"""
#     now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     table_rows = ""
#     for idx, row in df.iterrows():
#         ticker = row['Ticker']
#         if ".T" in ticker:
#             code = ticker.split('.')[0]
#             # 日本株のTradingViewリンク（概要と詳細チャート）
#             symbols_url = f"https://jp.tradingview.com/symbols/TSE-{code}/"
#             chart_url = f"https://jp.tradingview.com/chart/?symbol=TSE:{code}"
#             currency_prefix = "¥"
#         else:
#             # 米国株のTradingViewリンク（概要と詳細チャート）
#             symbols_url = f"https://jp.tradingview.com/symbols/{ticker}/"
#             chart_url = f"https://jp.tradingview.com/chart/?symbol={ticker}"
#             currency_prefix = "$"

#         table_rows += f"""
#         <tr>
#             <td>
#                 <span class="ticker-text">{ticker}</span>
#                 <div class="tv-links mt-1">
#                     <a href="{symbols_url}" target="_blank" class="badge badge-info mr-1">概要 📄</a>
#                     <a href="{chart_url}" target="_blank" class="badge badge-primary">チャート 📈</a>
#                 </div>
#             </td>
#             <td class="text-center text-success vertical-middle"><strong>{row['High_Count']} 回</strong></td>
#             <td class="vertical-middle">{currency_prefix}{row['Current_Price']:,}</td>
#             <td class="vertical-middle">{currency_prefix}{row['52W_High_Price']:,}</td>
#         </tr>
#         """

#     html_content = f"""<!DOCTYPE html>
# <html lang="ja">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>⚡ 52週新高値更新回数 {title_suffix}</title>
#     <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
#     <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
#     <style>
#         body {{ background-color: #f8f9fa; color: #333; font-family: 'Helvetica Neue', Arial, sans-serif; }}
#         .container {{ margin-top: 30px; margin-bottom: 50px; }}
#         .header-section {{ background: linear-gradient(135deg, #1f4037 0%, #99f2c8 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
#         .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; }}
#         .table thead th {{ background-color: #2c3e50; color: white; border: none; vertical-align: middle; }}
#         .vertical-middle {{ vertical-align: middle !important; }}
#         .ticker-text {{ font-size: 1.1rem; font-weight: bold; color: #2c3e50; }}
#         .badge {{ padding: 5px 8px; font-size: 0.75rem; }}
#         footer {{ text-align: center; margin-top: 30px; color: #777; font-size: 0.9rem; }}
#     </style>
# </head>
# <body>
#     <div class="container">
#         <div class="header-section">
#             <h1 class="display-5">📈 52週高値 更新回数ランキング {title_suffix}</h1>
#             <p class="lead mb-0">過去3週間（15営業日）の中で、何回52週最高値を更新したかを表示しています</p>
#             <hr class="my-2" style="border-color: rgba(255,255,255,0.2);">
#             <small>最終更新日時: <strong>{now_str}</strong> | ヒット数: {len(df)} 銘柄</small>
#         </div>

#         <div class="card p-4">
#             <div class="table-responsive">
#                 <table id="screenerTable" class="table table-hover table-striped table-bordered" style="width:100%">
#                     <thead>
#                         <tr>
#                             <th>ティッカー (Ticker)</th>
#                             <th class="text-center">新高値カウント (過去3週間)</th>
#                             <th>直近終値 (Current Price)</th>
#                             <th>52週最高値 (52W High Price)</th>
#                         </tr>
#                     </thead>
#                     <tbody>
#                         {table_rows}
#                     </tbody>
#                 </table>
#             </div>
#         </div>
#         <footer>
#             <p>Generated by 52-Week High Screener Tool</p>
#         </footer>
#     </div>

#     <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
#     <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>
#     <script src="https://cdn.datatables.net/1.10.21/js/dataTables.bootstrap4.min.js"></script>
#     <script>
#         $(document).ready(function() {{
#             $('#screenerTable').DataTable({{
#                 "order": [[ 1, "desc" ]],
#                 "pageLength": 50,
#                 "language": {{
#                     "search": "絞り込み検索:",
#                     "lengthMenu": "表示 _MENU_ 件",
#                     "info": "全 _TOTAL_ 銘柄中 _START_ から _END_ まで表示",
#                     "paginate": {{ "next": "次", "previous": "前" }}
#                 }}
#             }});
#         }});
#     </script>
# </body>
# </html>
# """
#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(html_content)

# if __name__ == "__main__":
#     choice = os.environ.get("SCREENER_CHOICE", "3")
#     tickers = []
#     title_suffix = ""
#     os.makedirs("data", exist_ok=True)

#     if choice in ["1", "3"]:
#         sp500_tickers = get_sp500_tickers()
#         tickers.extend(sp500_tickers)
#         title_suffix += "[S&P 500] "

#     if choice in ["2", "3"]:
#         topix_file = os.path.join("data", "tickers_topix.txt")
#         if not os.path.exists(topix_file):
#             with open(topix_file, "w") as f:
#                 f.write("# 日本株コード\n1306\n7203\n6758\n9984\n")
#         topix_tickers = load_tickers_from_file(topix_file, is_japan=True)
#         tickers.extend(topix_tickers)
#         title_suffix += "[TOPIX] "

#     if not tickers:
#         print("対象ティッカーがありません。")
#         exit()

#     result_df = check_52week_high(tickers, lookback_days=15)
#     html_name = "index.html"
    
#     if result_df is None or result_df.empty:
#         result_df = pd.DataFrame(columns=["Ticker", "High_Count", "Current_Price", "52W_High_Price"])
        
#     generate_html_report(result_df, html_name, title_suffix)
#     print(f"\n[成功] スクリーニング結果を '{html_name}' に上書き保存しました。")
