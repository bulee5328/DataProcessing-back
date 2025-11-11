import pandas as pd

CSV_PATH = "app/data/finance_data.csv"

def get_metrics_data_from_csv(ticker: str, metrics: list[str]):
    try:
        df = pd.read_csv(CSV_PATH)

        # 대소문자 구분 없이 symbol 검색
        row = df.loc[df['symbol'].str.upper() == ticker.upper()]

        if row.empty:
            raise ValueError(f"Ticker '{ticker}' not found in CSV")

        result = {}
        for metric in metrics:
            metric_lower = metric.lower()
            if metric_lower not in [col.lower() for col in df.columns]:
                result[metric] = "Invalid metric"
            else:
                # 원본 컬럼명 대소문자 일치 처리
                col_name = next(c for c in df.columns if c.lower() == metric_lower)
                result[metric] = float(row[col_name].values[0])

        return result

    except Exception as e:
        raise RuntimeError(f"Error reading CSV: {str(e)}")
