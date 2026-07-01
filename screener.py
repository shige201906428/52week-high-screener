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
        print(
            f"エラー: S&P 500のオンライン取得に失敗しました。代替銘柄を使用します。({e})"
        )
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


def check_52week_high_and_trend(ticker_list, lookback_days=10):
    """52週新高値のカウントと移動平均線によるトレンド判定"""
    results = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365 * 2)

    for ticker_symbol in tqdm(ticker_list, desc="スクリーニング中"):
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, end=end_date, progress=False)

            if len(df) < 252:
                continue

            # 移動平均線の計算
            df["MA25"] = df["Close"].rolling(window=25).mean()
            df["MA75"] = df["Close"].rolling(window=75).mean()
            df["MA200"] = df["Close"].rolling(window=200).mean()

            current_price = df["Close"].iloc[-1]
            ma25 = df["MA25"].iloc[-1]
            ma75 = df["MA75"].iloc[-1]
            ma200 = df["MA200"].iloc[-1]

            # トレンド判定
            if current_price > ma25 > ma75 > ma200:
                trend = "上昇 (Perfect Order)"
            elif current_price < ma25 < ma75 < ma200:
                trend = "下降 (Reverse Order)"
            else:
                trend = "レンジ / 不明"

            # 52週新高値カウント
            high_count = 0
            for i in range(-lookback_days, 0):
                if abs(i) > len(df):
                    continue
                target_day_high = df["High"].iloc[i]
                past_52w_high = df["High"].iloc[i - 252 : i].max()

                if target_day_high > past_52w_high:
                    high_count += 1

            latest_52w_high = df["High"].iloc[-252:].max()
            results.append(
                {
                    "Ticker": ticker_symbol,
                    "Trend": trend,
                    "52W_High_Count": high_count,
                    "Current_Price": round(current_price, 2),
                    "52W_High_Price": round(latest_52w_high, 2),
                }
            )
        except Exception:
            continue

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        res_df = res_df.sort_values(
            by=["52W_High_Count", "Trend"], ascending=[False, True]
        ).reset_index(drop=True)
    return res_df


def generate_html_report(df, output_path, title_suffix=""):
    """固定ファイル名（index.html）としてレポートを出力する"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_trend_badge(trend):
        if "上昇" in trend:
            return '<span class="badge badge-success">上昇 (Perfect Order)</span>'
        elif "下降" in trend:
            return '<span class="badge badge-danger">下降 (Reverse Order)</span>'
        return '<span class="badge badge-warning">レンジ / 不明</span>'

    table_rows = ""
    for idx, row in df.iterrows():
        trend_badge = get_trend_badge(row["Trend"])
        count_class = "highlight-count" if row["52W_High_Count"] > 0 else ""

        table_rows += f"""
        <tr>
            <td>{row['Ticker']}</td>
            <td>{trend_badge}</td>
            <td class="{count_class}"><strong>{row['52W_High_Count']}</strong></td>
            <td>{row['Current_Price']:,}</td>
            <td>{row['52W_High_Price']:,}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ 最新スクリーニング結果 {title_suffix}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
    <style>
        body {{ background-color: #f8f9fa; color: #333; font-family: 'Helvetica Neue', Arial, sans-serif; }}
        .container {{ margin-top: 30px; margin-bottom: 50px; }}
        .header-section {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; }}
        .table thead th {{ background-color: #343a40; color: white; border: none; }}
        .badge-success {{ background-color: #28a745; }}
        .badge-danger {{ background-color: #dc3545; }}
        .badge-warning {{ background-color: #ffc107; color: #212529; }}
        .highlight-count {{ background-color: #e8f5e9; color: #2e7d32; }}
        footer {{ text-align: center; margin-top: 30px; color: #777; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-section">
            <h1 class="display-5">📈 最新株式スクリーニング状況 {title_suffix}</h1>
            <p class="lead mb-0">52週新高値更新日数（過去2週間） ＆ 移動平均線トレンド判定</p>
            <hr class="my-2" style="border-color: rgba(255,255,255,0.2);">
            <small>最終更新日時: <strong>{now_str}</strong> | 対象銘柄数: {len(df)}</small>
        </div>

        <div class="card p-4">
            <div class="table-responsive">
                <table id="screenerTable" class="table table-hover table-striped table-bordered" style="width:100%">
                    <thead>
                        <tr>
                            <th>ティッカー (Ticker)</th>
                            <th>トレンド (Trend)</th>
                            <th>新高値日数 (52W High Count)</th>
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
                "order": [[ 2, "desc" ]],
                "pageLength": 50,
                "language": {{
                    "search": "絞り込み検索:",
                    "lengthMenu": "表示 _MENU_ 件",
                    "info": "全 _TOTAL_ 銘柄中 _START_ から _END_ まで表示",
                    "paginate": {{
                        "next": "次",
                        "previous": "前"
                    }}
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
    print("=== 52週新高値＆トレンド スクリーナー ===")

    # GitHub Actions（非対話環境）を考慮し、環境変数や引数から選択を取得
    # 指定がない場合は自動的に "3" (両方実行) にする
    choice = os.environ.get("SCREENER_CHOICE")
    if not choice and len(sys.argv) > 1:
        choice = sys.argv[1]

    if not choice:
        # ローカル実行時のみ入力を求める
        if sys.stdin.isatty():
            print("1: S&P 500 (米国株・全銘柄自動取得)")
            print("2: TOPIX (日本株・ファイル読み込み)")
            print("3: 両方実行")
            choice = input("実行するスクリーニングの番号を選択してください: ")
        else:
            choice = "3"  # 自動実行時はデフォルトで両方

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
                f.write("# ここに日本株のコードを1行ずつ書いてください\n7203\n6758\n")
        topix_tickers = load_tickers_from_file(topix_file, is_japan=True)
        tickers.extend(topix_tickers)
        title_suffix += "[TOPIX] "

    if not tickers:
        print("対象のティッカーがありません。プログラムを終了します。")
        exit()

    print(f"\n合計 {len(tickers)} 銘柄のスクリーニングを開始します...")
    result_df = check_52week_high_and_trend(tickers, lookback_days=10)

    if not result_df.empty:
        html_name = "index.html"
        generate_html_report(result_df, html_name, title_suffix)
        print(f"\n[成功] スクリーニング結果を '{html_name}' に上書き保存しました。")
    else:
        print("該当データがありませんでした。")
