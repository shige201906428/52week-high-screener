import datetime
import os
import sys
import pandas as pd
import yfinance as yf
from tqdm import tqdm

def get_sp500_tickers():
    """Wikipediaから現在のS&P 500構成銘柄のティッカーリストを自動取得する"""
    print("S&P 500の最新銘柄リストをオンラインから取得中...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"-> S&P 500の {len(tickers)} 銘柄を取得しました。")
        return tickers
    except Exception as e:
        print(f"エラー: S&P 500のオンライン取得に失敗しました。代替銘柄を使用します。({e})")
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

def check_52week_high(ticker_list):
    """直近で52週新高値を更新した銘柄のみを抽出する"""
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)

    print(f"\nYahoo Financeから株価データを一括ダウンロード中...")
    try:
        all_data = yf.download(ticker_list, start=start_date, end=end_date, group_by='ticker', progress=False)
    except Exception as e:
        print(f"データのダウンロード中にエラーが発生しました: {e}")
        return pd.DataFrame()

    for ticker_symbol in tqdm(ticker_list, desc="スクリーニング中"):
        try:
            if len(ticker_list) == 1:
                df = all_data.dropna()
            else:
                if ticker_symbol not in all_data.columns.levels[0]:
                    continue
                df = all_data[ticker_symbol].dropna()

            if len(df) < 252:
                continue

            # 直近（今日）の高値と終値
            current_high = df["High"].iloc[-1]
            current_price = df["Close"].iloc[-1]
            
            # 過去52週間（約252営業日）の最高値（直近の日は除く）
            past_52w_high = df["High"].iloc[-253:-1].max()

            # 今日の高値が過去52週の最高値を超えている場合のみヒット
            if current_high >= past_52w_high:
                results.append({
                    "Ticker": ticker_symbol,
                    "Current_Price": round(current_price, 2),
                    "52W_High_Price": round(max(current_high, past_52w_high), 2)
                })
        except Exception:
            continue

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        res_df = res_df.sort_values(by="Ticker").reset_index(drop=True)
    return res_df

def generate_html_report(df, output_path, title_suffix=""):
    """index.htmlとしてシンプルなレポートを出力する"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    table_rows = ""
    for idx, row in df.iterrows():
        table_rows += f"""
        <tr>
            <td><strong>{row['Ticker']}</strong></td>
            <td class="highlight-price">{row['Current_Price']:,}</td>
            <td>{row['52W_High_Price']:,}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ 52週新高値更新銘柄 {title_suffix}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
    <style>
        body {{ background-color: #f8f9fa; color: #333; font-family: 'Helvetica Neue', Arial, sans-serif; }}
        .container {{ margin-top: 30px; margin-bottom: 50px; }}
        .header-section {{ background: linear-gradient(135deg, #1f4037 0%, #99f2c8 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; }}
        .table thead th {{ background-color: #2c3e50; color: white; border: none; }}
        .highlight-price {{ color: #27ae60; font-weight: bold; }}
        footer {{ text-align: center; margin-top: 30px; color: #777; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-section">
            <h1 class="display-5">📈 52週新高値更新 銘柄一覧 {title_suffix}</h1>
            <p class="lead mb-0">直近で52週最高値を更新した銘柄を抽出しています</p>
            <hr class="my-2" style="border-color: rgba(255,255,255,0.2);">
            <small>最終更新日時: <strong>{now_str}</strong> | ヒット数: {len(df)} 銘柄</small>
        </div>

        <div class="card p-4">
            <div class="table-responsive">
                <table id="screenerTable" class="table table-hover table-striped table-bordered" style="width:100%">
                    <thead>
                        <tr>
                            <th>ティッカー (Ticker)</th>
                            <th>直近終値 (Current Price)</th>
                            <th>52週最高値 (52W High Price)</th>
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
        $(document).ready(function() {{
            $('#screenerTable').DataTable({{
                "pageLength": 50,
                "language": {{
                    "search": "絞り込み検索:",
                    "lengthMenu": "表示 _MENU_ 件",
                    "info": "全 _TOTAL_ 銘柄中 _START_ から _END_ まで表示",
                    "paginate": {{ "next": "次", "previous": "前" }}
                }}
            }});
        }});
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    print("=== 52週新高値専用スクリーナー ===")

    choice = os.environ.get("SCREENER_CHOICE")
    if not choice and len(sys.argv) > 1:
        choice = sys.argv[1]
    if not choice:
        if sys.stdin.isatty():
            print
