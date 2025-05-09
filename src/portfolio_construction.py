import pandas as pd
import numpy as np

def calculate_equal_weighted_portfolio_returns(stock_returns_df: pd.DataFrame) -> pd.Series:
    """
    计算等权重投资组合的日/月收益率。
    假设 stock_returns_df 的每一列是一只股票的收益率，索引是日期。
    对于缺失的收益率 (NaN)，在计算当日组合收益时，这些股票不贡献（相当于权重为0）。
    """
    # 确保 stock_returns_df 不为空且包含数据
    if stock_returns_df.empty or stock_returns_df.shape[1] == 0:
        return pd.Series(dtype=float, name="portfolio_return")

    # 对于每一天，计算当天有有效数据的股票的平均收益率
    # .mean(axis=1) 会自动忽略NaN值进行计算
    # 如果某天所有股票数据都为NaN，则结果为NaN
    portfolio_returns = stock_returns_df.mean(axis=1)
    portfolio_returns.name = "portfolio_return"
    return portfolio_returns

def calculate_cap_weighted_portfolio_returns(stock_returns_df: pd.DataFrame,
                                             market_cap_df: pd.DataFrame) -> pd.Series:
    """
    计算市值加权投资组合的日/月收益率。
    stock_returns_df: DataFrame, 股票收益率，索引为日期，列为股票代码。
    market_cap_df: DataFrame, 股票市值，索引为日期，列为股票代码。
                   市值的日期应与收益率的日期对应（例如，使用期初市值计算当期收益的权重）。
    """
    if stock_returns_df.empty or market_cap_df.empty:
        return pd.Series(dtype=float, name="portfolio_return")

    # 确保股票代码和日期对齐
    common_stocks = stock_returns_df.columns.intersection(market_cap_df.columns)
    common_dates = stock_returns_df.index.intersection(market_cap_df.index)

    if len(common_stocks) == 0 or len(common_dates) == 0:
        print("Warning: No common stocks or dates between returns and market cap data.")
        return pd.Series(dtype=float, name="portfolio_return")

    returns_aligned = stock_returns_df.loc[common_dates, common_stocks]
    # 市值数据通常使用上一期末的市值来决定本期的权重
    # 为简单起见，这里假设 market_cap_df 已经是对应期初的市值
    # 或者，如果 market_cap_df 是每日市值，我们可以 shift(1) 来获取前一天的市值作为权重基础
    # weights_base = market_cap_df.loc[common_dates, common_stocks].shift(1) # 假设用T-1日市值
    weights_base = market_cap_df.loc[common_dates, common_stocks] # 假设已是期初市值

    # 处理权重计算中的NaN (例如，某股票某日市值缺失)
    weights_base = weights_base.fillna(0) # 市值缺失的股票权重为0

    # 计算权重：每只股票市值 / 当日总市值
    total_market_cap_daily = weights_base.sum(axis=1)
    # 防止除以0的情况
    weights = weights_base.divide(total_market_cap_daily, axis=0).fillna(0)

    # 计算加权组合收益：(收益率 * 权重).sum(axis=1)
    # 确保收益率和权重 DataFrame 的 NaN 处理方式一致，或者在相乘前处理好
    # 如果收益率为 NaN，即使有权重，乘积也为 NaN。如果权重为 NaN (或0)，乘积为 NaN (或0)。
    # (returns_aligned * weights) 会逐元素相乘
    portfolio_returns = (returns_aligned * weights).sum(axis=1)
    portfolio_returns.name = "portfolio_return"
    return portfolio_returns

# 示例用法 (可以在 main.py 中调用)
# if __name__ == '__main__':
#     # 假设已经通过 data_loader 加载了 all_daily_stock_returns
#     # 创建一个虚拟的 all_daily_stock_returns DataFrame
#     dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
#     data = {
#         'stockA_return': [0.01, -0.005, 0.012],
#         'stockB_return': [0.005, 0.002, np.nan], # stockB 在第三天收益缺失
#         'stockC_return': [-0.002, 0.01, 0.008]
#     }
#     sample_stock_returns = pd.DataFrame(data, index=dates)
#     print("Sample Stock Returns:")
#     print(sample_stock_returns)
#
#     eq_portfolio_returns = calculate_equal_weighted_portfolio_returns(sample_stock_returns)
#     print("\nEqual Weighted Portfolio Returns:")
#     print(eq_portfolio_returns)
#
#     # 对于市值加权，还需要市值数据
#     cap_data = {
#         'stockA': [100, 101, 100.5], # 假设这是期初或当日市值
#         'stockB': [200, 200.4, 200],
#         'stockC': [150, 149.7, 151]
#     }
#     sample_market_caps = pd.DataFrame(cap_data, index=dates)
#     print("\nSample Market Caps:")
#     print(sample_market_caps)
#
#     cap_portfolio_returns = calculate_cap_weighted_portfolio_returns(sample_stock_returns, sample_market_caps)
#     print("\nCap Weighted Portfolio Returns:")
#     print(cap_portfolio_returns) 