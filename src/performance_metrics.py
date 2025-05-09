import pandas as pd
import numpy as np
import statsmodels.api as sm
from . import config

def calculate_annualized_mean_return(returns_series: pd.Series, frequency: str = "daily") -> float:
    """计算年化平均收益率"""
    if returns_series.empty: return np.nan
    periods_per_year = config.TRADING_DAYS_PER_YEAR_DAILY if frequency == "daily" \
        else config.TRADING_PERIODS_PER_YEAR_MONTHLY
    return returns_series.mean() * periods_per_year

def calculate_annualized_volatility(returns_series: pd.Series, frequency: str = "daily") -> float:
    """计算年化波动率 (标准差)"""
    if returns_series.empty: return np.nan
    periods_per_year = config.TRADING_DAYS_PER_YEAR_DAILY if frequency == "daily" \
        else config.TRADING_PERIODS_PER_YEAR_MONTHLY
    return returns_series.std() * np.sqrt(periods_per_year)

def calculate_sharpe_ratio(returns_series: pd.Series,
                           risk_free_rate: float = config.RISK_FREE_RATE,
                           frequency: str = "daily") -> float:
    """计算夏普比率"""
    if returns_series.empty: return np.nan
    annual_return = calculate_annualized_mean_return(returns_series, frequency)
    annual_vol = calculate_annualized_volatility(returns_series, frequency)
    if annual_vol == 0: # 防止除以零
        return np.nan if annual_return - risk_free_rate == 0 else np.inf * np.sign(annual_return - risk_free_rate)
    return (annual_return - risk_free_rate) / annual_vol

def calculate_max_drawdown(returns_series: pd.Series) -> float:
    """计算最大回撤"""
    if returns_series.empty: return np.nan
    cumulative_returns = (1 + returns_series).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / peak
    return drawdown.min() # 最大回撤是负数，取最小值

def calculate_alpha_beta(portfolio_returns: pd.Series,
                         benchmark_returns: pd.Series,
                         risk_free_rate: float = config.RISK_FREE_RATE,
                         frequency: str = "daily") -> tuple[float, float]:
    """
    计算 Alpha 和 Beta (基于CAPM模型)
    portfolio_returns: 组合的收益率序列 (日度或月度)
    benchmark_returns: 基准指数的收益率序列 (日度或月度)
    risk_free_rate: 年化无风险利率
    frequency: 'daily' 或 'monthly'
    返回: (alpha_annualized, beta)
    """
    if portfolio_returns.empty or benchmark_returns.empty:
        return np.nan, np.nan

    # 对齐数据并移除NaN
    df = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if df.empty or len(df) < 2: # 需要至少两个数据点进行回归
        return np.nan, np.nan

    # 计算超额收益率
    # 无风险利率需要从年化转换为对应频率
    periods_per_year = config.TRADING_DAYS_PER_YEAR_DAILY if frequency == "daily" \
        else config.TRADING_PERIODS_PER_YEAR_MONTHLY
    rf_period = (1 + risk_free_rate)**(1/periods_per_year) - 1

    portfolio_excess_returns = df['portfolio'] - rf_period
    benchmark_excess_returns = df['benchmark'] - rf_period

    # OLS回归: PortfolioExcessReturn = Alpha_period + Beta * BenchmarkExcessReturn
    X = sm.add_constant(benchmark_excess_returns) # 添加常数项 (截距项)
    y = portfolio_excess_returns

    model = sm.OLS(y, X).fit()
    # model.params[0] 是截距 (alpha_period), model.params[1] 是斜率 (beta)
    alpha_period = model.params.iloc[0] if isinstance(model.params, pd.Series) else model.params[0]
    beta = model.params.iloc[1] if isinstance(model.params, pd.Series) else model.params[1]

    # 将Alpha年化: Alpha_annual = (1 + Alpha_period)^periods_per_year - 1
    # 或者更常见的近似：Alpha_annual = Alpha_period * periods_per_year (如果alpha_period很小)
    # 对于Jensen's Alpha，通常直接将回归得到的alpha_period进行年化
    annualized_alpha = alpha_period * periods_per_year

    return annualized_alpha, beta

def calculate_variance(returns_series: pd.Series, frequency: str = "daily") -> float:
    """计算年化方差"""
    if returns_series.empty: return np.nan
    periods_per_year = config.TRADING_DAYS_PER_YEAR_DAILY if frequency == "daily" \
        else config.TRADING_PERIODS_PER_YEAR_MONTHLY
    # 方差是波动率的平方，或者直接用日/月方差乘以期数 (近似)
    # 更准确的是 (日/月标准差)^2 * 期数，或者 日/月方差 * 期数 (如果收益率独立同分布)
    # 这里我们用 (std_dev * sqrt(periods))^2 = var * periods
    return returns_series.var() * periods_per_year

# 示例用法
# if __name__ == '__main__':
#     # 假设有以下收益率序列
#     dates = pd.date_range(start='2023-01-01', periods=252, freq='B') # 约一年日度数据
#     np.random.seed(42)
#     port_rets = pd.Series(np.random.normal(0.0005, 0.01, 252), index=dates)
#     bench_rets = pd.Series(np.random.normal(0.0004, 0.008, 252), index=dates)
#
#     print(f"Annualized Mean Return: {calculate_annualized_mean_return(port_rets, 'daily'):.4f}")
#     print(f"Annualized Volatility: {calculate_annualized_volatility(port_rets, 'daily'):.4f}")
#     print(f"Annualized Variance: {calculate_variance(port_rets, 'daily'):.6f}")
#     print(f"Sharpe Ratio: {calculate_sharpe_ratio(port_rets, risk_free_rate=0.02, frequency='daily'):.4f}")
#     print(f"Max Drawdown: {calculate_max_drawdown(port_rets):.4f}")
#
#     alpha, beta = calculate_alpha_beta(port_rets, bench_rets, risk_free_rate=0.02, frequency='daily')
#     print(f"Annualized Alpha: {alpha:.4f}")
#     print(f"Beta: {beta:.4f}") 