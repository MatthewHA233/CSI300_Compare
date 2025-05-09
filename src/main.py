import pandas as pd
from . import config
from . import data_loader
from . import portfolio_construction
from . import analysis
import argparse # 用于命令行参数解析

def run_analysis_pipeline(frequency: str = "daily",
                          start_date: str | None = None,
                          end_date: str | None = None,
                          portfolio_type: str = "equal_weighted"):
    """
    执行完整的分析流程。
    """
    print(f"Starting analysis for {frequency} data from {start_date} to {end_date}")
    print(f"Portfolio type: {portfolio_type}")

    # 1. 加载数据
    print("\n--- Loading Data ---")
    # 假设股票列表从文件夹中自动获取
    # 你也可以修改为从特定文件读取股票列表
    all_stock_returns = data_loader.load_all_stock_returns(
        stock_list=None, # None 表示扫描文件夹
        frequency=frequency,
        start_date=start_date,
        end_date=end_date
    )

    if all_stock_returns.empty:
        print("No stock data loaded. Exiting.")
        return

    print(f"Loaded returns for {all_stock_returns.shape[1]} stocks.")
    # print("Sample stock returns (head):")
    # print(all_stock_returns.head())


    index_returns_df = data_loader.load_index_data(
        index_code=config.CSI300_CODE,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date
    )

    if index_returns_df is None or index_returns_df.empty:
        print(f"{config.CSI300_CODE} index data not loaded. Analysis will be limited.")
        benchmark_returns_series = pd.Series(dtype=float) # 空Series
    else:
        benchmark_returns_series = index_returns_df['index_return']
        # print(f"\nSample {config.CSI300_CODE} returns (head):")
        # print(benchmark_returns_series.head())

    # 对齐股票收益率和指数收益率的日期索引 (非常重要)
    # 如果指数的交易日和股票组合的交易日不完全一致
    # (例如，某些股票在指数交易日停牌，或者反之)
    # 需要决定如何处理。通常是以两者共有的日期为准。
    if not benchmark_returns_series.empty:
        common_dates = all_stock_returns.index.intersection(benchmark_returns_series.index)
        all_stock_returns = all_stock_returns.loc[common_dates]
        benchmark_returns_series = benchmark_returns_series.loc[common_dates]
        print(f"Data aligned to {len(common_dates)} common trading dates.")


    # 2. 构建投资组合
    print("\n--- Constructing Portfolio ---")
    if portfolio_type == "equal_weighted":
        portfolio_returns_series = portfolio_construction.calculate_equal_weighted_portfolio_returns(
            all_stock_returns
        )
    elif portfolio_type == "cap_weighted":
        # 市值加权需要市值数据，这里简化，假设你有 market_cap_df
        # 你需要实现加载市值的逻辑，并传入 market_cap_df
        # market_cap_df = data_loader.load_all_market_caps(...)
        # portfolio_returns_series = portfolio_construction.calculate_cap_weighted_portfolio_returns(
        #     all_stock_returns, market_cap_df
        # )
        print("Cap-weighted portfolio not fully implemented in this example. Requires market cap data.")
        print("Falling back to equal-weighted for now.")
        portfolio_returns_series = portfolio_construction.calculate_equal_weighted_portfolio_returns(
            all_stock_returns
        )
    else:
        raise ValueError(f"Unsupported portfolio type: {portfolio_type}")

    if portfolio_returns_series.empty:
        print("Portfolio returns could not be calculated. Exiting.")
        return

    portfolio_returns_series = portfolio_returns_series.dropna() # 确保组合收益序列无NaN
    # print("\nSample portfolio returns (head):")
    # print(portfolio_returns_series.head())

    # 3. 业绩分析
    print("\n--- Performing Analysis ---")
    analysis_results = analysis.run_performance_analysis(
        portfolio_returns=portfolio_returns_series,
        benchmark_returns=benchmark_returns_series,
        risk_free_rate=config.RISK_FREE_RATE,
        frequency=frequency,
        portfolio_name=f"{portfolio_type.replace('_', ' ').title()} Portfolio",
        benchmark_name=f"{config.CSI300_CODE} Index"
    )

    print("\n--- Performance Results ---")
    if not analysis_results.empty:
        print(analysis_results.round(4)) # 保留4位小数
    else:
        print("No analysis results to display.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Portfolio Performance Analysis")
    parser.add_argument(
        "--frequency", type=str, default="daily", choices=["daily", "monthly"],
        help="Data frequency: 'daily' or 'monthly'"
    )
    parser.add_argument(
        "--start_date", type=str, default="2019-01-01", # 示例日期
        help="Start date for analysis (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end_date", type=str, default="2023-12-31", # 示例日期
        help="End date for analysis (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--portfolio_type", type=str, default="equal_weighted", choices=["equal_weighted", "cap_weighted"],
        help="Portfolio construction type: 'equal_weighted' or 'cap_weighted'"
    )
    # 你可以从 config.py 中读取默认日期，或者让用户必须指定
    # args_start_date = config.START_DATE_STR if config.START_DATE_STR else None
    # args_end_date = config.END_DATE_STR if config.END_DATE_STR else None

    args = parser.parse_args()

    run_analysis_pipeline(
        frequency=args.frequency,
        start_date=args.start_date,
        end_date=args.end_date,
        portfolio_type=args.portfolio_type
    ) 