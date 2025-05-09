import pandas as pd
from . import performance_metrics as pm
from . import config

def run_performance_analysis(portfolio_returns: pd.Series,
                             benchmark_returns: pd.Series,
                             risk_free_rate: float = config.RISK_FREE_RATE,
                             frequency: str = "daily",
                             portfolio_name: str = "Portfolio",
                             benchmark_name: str = "Benchmark") -> pd.DataFrame:
    """
    对投资组合和基准进行全面的业绩分析。
    返回一个包含各项指标的DataFrame。
    """
    if portfolio_returns.empty:
        print(f"Warning: {portfolio_name} returns are empty. Skipping analysis.")
        return pd.DataFrame()
    if benchmark_returns.empty:
        print(f"Warning: {benchmark_name} returns are empty. Cannot calculate Alpha/Beta.")
        # 可以选择只计算组合的指标
        # return pd.DataFrame()


    results = {}

    # Portfolio Metrics
    results[portfolio_name] = {
        "Annualized Mean Return": pm.calculate_annualized_mean_return(portfolio_returns, frequency),
        "Annualized Volatility": pm.calculate_annualized_volatility(portfolio_returns, frequency),
        "Annualized Variance": pm.calculate_variance(portfolio_returns, frequency),
        "Sharpe Ratio": pm.calculate_sharpe_ratio(portfolio_returns, risk_free_rate, frequency),
        "Max Drawdown": pm.calculate_max_drawdown(portfolio_returns),
        "Alpha (annualized)": np.nan, # 初始化
        "Beta": np.nan # 初始化
    }

    # Benchmark Metrics
    if not benchmark_returns.empty:
        results[benchmark_name] = {
            "Annualized Mean Return": pm.calculate_annualized_mean_return(benchmark_returns, frequency),
            "Annualized Volatility": pm.calculate_annualized_volatility(benchmark_returns, frequency),
            "Annualized Variance": pm.calculate_variance(benchmark_returns, frequency),
            "Sharpe Ratio": pm.calculate_sharpe_ratio(benchmark_returns, risk_free_rate, frequency),
            "Max Drawdown": pm.calculate_max_drawdown(benchmark_returns),
            "Alpha (annualized)": 0.0, # 基准相对于自身的Alpha为0 (或不适用)
            "Beta": 1.0 # 基准相对于自身的Beta为1 (或不适用)
        }

        # Alpha and Beta for Portfolio (relative to benchmark)
        if not portfolio_returns.empty:
            alpha, beta = pm.calculate_alpha_beta(portfolio_returns, benchmark_returns, risk_free_rate, frequency)
            results[portfolio_name]["Alpha (annualized)"] = alpha
            results[portfolio_name]["Beta"] = beta
    else: # 如果基准数据为空，Alpha和Beta无法计算
        results[portfolio_name]["Alpha (annualized)"] = np.nan
        results[portfolio_name]["Beta"] = np.nan


    results_df = pd.DataFrame(results)
    return results_df

# 示例用法 (可以在 main.py 中调用)
# if __name__ == '__main__':
#     # 假设有 portfolio_daily_returns 和 csi300_daily_returns
#     dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
#     np.random.seed(0)
#     port_rets = pd.Series(np.random.normal(0.0007, 0.012, 252), index=dates, name="MyPortfolio")
#     bench_rets = pd.Series(np.random.normal(0.0005, 0.01, 252), index=dates, name="CSI300")
#
#     analysis_results_df = run_performance_analysis(
#         portfolio_returns=port_rets,
#         benchmark_returns=bench_rets,
#         risk_free_rate=config.RISK_FREE_RATE,
#         frequency="daily",
#         portfolio_name="My Custom Portfolio",
#         benchmark_name="CSI 300 Index"
#     )
#
#     print("\nPerformance Analysis Results:")
#     print(analysis_results_df.round(4)) # 保留4位小数 