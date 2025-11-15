import pandas as pd

#해당 부분에 makeFactor.ipynb가 모듈화 되어 들어갈 것.

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
    
# -*- coding: utf-8 -*-
import yfinance as yf
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import scipy.optimize as sco

def makeFactor(weights, number):
    # ================================
    # 1. 프론트에서 오는 지표명을 실제 CSV 컬럼명으로 매핑
    # ================================
    name_map = {
        "ROE": "ROE (Return on Equity)",
        "ROA": "ROA (Return on Assets)",
        "PER": "P/E Ratio (PER)",

        "매출액 성장률": "Revenue Growth (YoY)",
        "순이익 성장률": "Earnings Growth (YoY)",
        "EPS 성장률(향후 5년 예상)": "EPS Growth (Next 5 Years)",

        "부채비율(Dept ratio)": "Debt/Equity Ratio",
        "유동비율(Current ratio)": "Current Ratio",
        "당좌비율(Quick Ratio)": "Quick Ratio",

        "20일 이동평균선": "20일 이동평균선",
        "RSI": "RSI(14)",
        "MACD": "MACD",
    }

    # 전달된 weights를 실제 컬럼명 기반으로 변환
    # 예: {"ROE": 0.3} → {"ROE (Return on Equity)": 0.3}
    converted_weights = {name_map.get(k, k): v for k, v in weights.items()}

    # ================================
    # 2. 기존 코드
    # ================================
    SYMBOLS_PATH = "data/sp500_symbols_filtered.csv"
    ANALYSIS_PATH = "data/stock_analysis_cleaned.csv"

    df_symbols = pd.read_csv(SYMBOLS_PATH)
    df = pd.read_csv(ANALYSIS_PATH)

    selected_features = [
        'ROE (Return on Equity)', 'ROA (Return on Assets)', 'P/E Ratio (PER)',
        'Debt/Equity Ratio', 'Current Ratio', 'Quick Ratio',
        'Revenue Growth (YoY)', 'Earnings Growth (YoY)', 'EPS Growth (Next 5 Years)',
        '20일 이동평균선', 'RSI(14)', 'MACD',
    ]

    df_copy = df.copy()

    # 역지표 처리
    df_copy['P/E Ratio (PER)'] = 1 / df_copy['P/E Ratio (PER)']
    df_copy['Debt/Equity Ratio'] = 1 / df_copy['Debt/Equity Ratio']

    df_copy = df_copy[selected_features]
    df_rank_all = df_copy.rank(axis=0)

    # ================================
    # 3. 가중치 계산 부분에 변환된 weights 적용
    # ================================
    if converted_weights:
        weighted_rank = df_rank_all.mul(pd.Series(converted_weights)).fillna(0)
    else:
        weighted_rank = df_rank_all

    # ================================
    # 4. 상위/하위 number개 종목 선택
    # ================================
    # 하위 number개
    value_sum_all = weighted_rank.sum(axis=1, skipna=False).rank()
    result_df = df[['Ticker'] + selected_features].loc[value_sum_all <= number]
    tickers_bottom = result_df['Ticker'].tolist()

    # 상위 number개
    value_sum_all = weighted_rank.sum(axis=1, skipna=False).rank(ascending=False)
    result_df = df[['Ticker'] + selected_features].loc[value_sum_all <= number]
    tickers_top = result_df['Ticker'].tolist()

    return tickers_top, tickers_bottom


######################################################
def makePortpolio(tickers, tickers_bottom):
    data = yf.download(tickers, start='2010-01-05', end='2025-10-21', auto_adjust=False)['Adj Close']

    data_bottom = yf.download(tickers_bottom, start='2010-01-05', end='2025-10-21', auto_adjust=False)['Adj Close']


    def calc_annual_return(price_df):
        daily_returns = price_df.pct_change().dropna()
        portfolio_returns = daily_returns.mean(axis=1)  # 동일가중 평균
        cumulative_return = (1 + portfolio_returns).prod() - 1
        total_days = (daily_returns.index[-1] - daily_returns.index[0]).days
        annualized_return = (1 + cumulative_return) ** (365 / total_days) - 1
        return float(annualized_return), float(cumulative_return)

    # 상위 / 하위 포트폴리오 연평균 수익률 계산
    top_annual, _ = calc_annual_return(data)
    bottom_annual, _ = calc_annual_return(data_bottom)

    annual = {"top_annual":top_annual, "bottom_annual":bottom_annual}

    # 데이터 확인
    # print(data.head())

    # data.isnull().sum()

    filtered_data = data.dropna(axis=1)

    # filtered_data.isnull().sum()

    universe = filtered_data
    df=universe.resample('M').last().pct_change(1) # 월간수익률 변환

    covmat= np.array(filtered_data.pct_change(1).cov()*12)            # 자산별 수익률의 공분산  (월별수익률의 연율화)
    avg_returns= np.array(filtered_data.pct_change(1).mean()*12)      #  자산별 기대수익률 (월별수익률의 연율화)
    names = filtered_data.columns.tolist()
    n_assets = len(names)     # 대상자산수
    rf = .02                                  # 무위험이자율
    weight=np.array(n_assets*[1/n_assets]).T  # 자산별 초기 비중
    # print(f"초기 비중 :\n{weight}\n")              # 기초계산값 확인
    # print(f"기대수익률:\n{avg_returns}\n")
    # print(f"공분산 행렬:\n{covmat}\n")

    # 포트폴리오 기대수익률 계산

    def get_portf_rtn(w, avg_rtns):
        return np.sum(avg_rtns * w)

    # 포트폴리오 변동성 계산

    def get_portf_vol(w, cov_mat):
        return np.sqrt(w.T@cov_mat@ w) # np.dot(w.T, np.dot(cov_mat, w))

    # 효율적 프론티어 산출 (포트폴리오수익률, 공분산행렬, 기대수익률 범위)

    def get_efficient_frontier(avg_rtns, cov_mat, rtns_range):

        efficient_portfolios = []

        n_assets = len(avg_rtns)   # 자산갯수
        args = (cov_mat) # get_portf_vol 함수에 들어갈 인수 정의

        bounds = tuple((0.0,1) for asset in range(n_assets))  # 자산별 비중 제약조건 설정
        initial_guess = n_assets * [1. / n_assets, ]          # 초기값 0.2 씩 5개 자산에 배정

        for ret in rtns_range:  # 기대수익률별 최적투자비중을 산출

            constraints = ({'type': 'eq',
                            'fun': lambda x: get_portf_rtn(x, avg_rtns) - ret}, # 포트폴리오 기대수익률 계산
                        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1})  # 자산별 비중합은 1
            efficient_portfolio = minimize(get_portf_vol, initial_guess,
                                            args=args, method='SLSQP',
                                            constraints=constraints,
                                            bounds=bounds)
            efficient_portfolios.append(efficient_portfolio)

        return efficient_portfolios

    def get_efficient_frontier_value(avg_rtns, cov_mat, nums):  #  nums:프론티어에서 계산할 기대수익률의 갯수
        # 기대수익률 범위 설정
        rtns_range = np.linspace(np.min(avg_rtns), np.max(avg_rtns), nums)
        # 효율적 프론티어 계산
        efficient_portfolios = get_efficient_frontier(avg_rtns, cov_mat, rtns_range)
        # 결과 추출 (NumPy 배열 변환)
        vols_range = np.array([res["fun"] for res in efficient_portfolios])
        weight_range = np.vstack([res["x"] for res in efficient_portfolios])

        # DataFrame 생성 (= ["Volatility", "Return"] + ["weight1", "weight2", "weight3",.."weight6" ,]
        portfolio_result_df = pd.DataFrame(
            np.column_stack([vols_range, rtns_range, weight_range]),   # 열 단위로 나란히 붙이는 함수
            columns=["Volatility", "Return"] + [f"weight{i+1}" for i in range(weight_range.shape[1])]
        )

        # 최소 리스크 지점의 기대수익률
        min_vol_idx = portfolio_result_df["Volatility"].idxmin()  # Series의 최소값 위치
        exp_ret = portfolio_result_df.loc[min_vol_idx, "Return"]

        # 효율적 프론티어: 최소 리스크 이상만 선택
        port_result = portfolio_result_df[portfolio_result_df["Return"] >= exp_ret]

        return port_result.round(4)

    # 프론티어 구성하는 계산값 구기기
    port_result_df = get_efficient_frontier_value(avg_returns, covmat,50)

    # 프론티어에 필요한 변동성과 기대수익률만 따로 추린다.

    port_result=port_result_df.iloc[:,[0,1]]  # 포트폴리오 변동성과 기대수익률
    port_result.columns=['portf_vol', 'portf_rtns']

    # import matplotlib.pylab as plt
    # fig, ax = plt.subplots()
    # port_result.plot(kind='scatter', x='portf_vol',
    #                       y='portf_rtns',
    #                       cmap='RdYlGn', edgecolors='black', title='Efficient Frontier',
    #                       ax=ax)
    # plt.show()

    portfolio_weight_df= port_result_df.iloc[:,2:]  #  # 효율적 포트폴리오 결과치에서 자산별 비중만 추출
    portfolio_weight_df.columns=df.columns  # 자산명

    # 포트폴리오 기대수익률과 자산별 투자비중의 결합
    port_all=  pd.concat([portfolio_weight_df, port_result[['portf_rtns']]],axis=1)
    opt_port= port_all.set_index('portf_rtns')

    # 포트폴리오 기대수익률에 따른 자산별 투자비중 변화 그래프
    # opt_port.plot.bar(stacked=True,legend='reverse', figsize=(24,8))

    # 포트폴리오 변동성 계산

    def get_portf_vol(weight, cov_mat):
        return np.sqrt(weight.T@cov_mat@weight)

    # covmat= np.array(df.cov()*12) , weight=np.array(n_assets*[1/n_assets]).T

    get_portf_vol(weight,covmat)

    # 포트폴리오 변동성 최소화를 위한 최적화

    def minimum_variance_optimization(exp_ret,cov_mat):

        num_assets=len(exp_ret) # 자산갯수
        args=(cov_mat)          # 공분산 입력
        constraints=({'type': 'eq','fun': lambda x: np.sum(x)-1})
        bounds=[(0,1) for i in range(num_assets)]  # 자산별 비중 제약 (0, 1)

        result_mv= sco.minimize(get_portf_vol,num_assets*[1./num_assets],args=args, method='SLSQP',
                            bounds=bounds,constraints=constraints)
        MVO_Allocation =pd.DataFrame(result_mv.x,index=df.columns,columns=['allocation'])  # 종목명 인덱스만 가져다 쓴다.

        return round(MVO_Allocation*100,2)

    # 함수 결과값 확인

    MVO =minimum_variance_optimization(avg_returns,covmat)

    allocations = [
        {"ticker": ticker, "allocation": float(MVO.loc[ticker, "allocation"])}
        for ticker in MVO.index
    ]

    return allocations, annual