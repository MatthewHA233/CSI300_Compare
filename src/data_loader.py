import pandas as pd
import os
from . import config

def load_single_stock_data(ticker: str, frequency: str = "daily", start_date=None, end_date=None) -> pd.DataFrame | None:
    """
    加载单只股票的数据。
    假设股价数据在 'adj_close' 列，日期在 'date' 列。
    """
    if frequency == "daily":
        file_path = os.path.join(config.DAILY_STOCK_DATA_DIR, f"{ticker}.csv")
    elif frequency == "monthly":
        file_path = os.path.join(config.MONTHLY_STOCK_DATA_DIR, f"{ticker}.csv")
    else:
        raise ValueError("Frequency must be 'daily' or 'monthly'")

    if not os.path.exists(file_path):
        print(f"Warning: Data file not found for {ticker} at {file_path}")
        return None

    try:
        df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')
        # 确保使用复权收盘价，如果列名不同请修改
        price_col = 'adj_close' if 'adj_close' in df.columns else 'close'
        df = df[[price_col]].rename(columns={price_col: 'price'})

        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]

        df[f'{ticker}_return'] = df['price'].pct_change()
        df = df[[f'{ticker}_return']].dropna()
        return df
    except Exception as e:
        print(f"Error loading or processing data for {ticker}: {e}")
        return None

def load_all_stock_returns(stock_list: list[str] | None = None,
                           frequency: str = "daily",
                           start_date=None, end_date=None) -> pd.DataFrame:
    """
    加载指定列表或目录下所有股票的收益率数据，并合并。
    """
    all_returns = []
    if stock_list is None: # 如果未提供股票列表，则扫描文件夹
        stock_dir = config.DAILY_STOCK_DATA_DIR if frequency == "daily" else config.MONTHLY_STOCK_DATA_DIR
        if not os.path.exists(stock_dir):
            print(f"Stock directory not found: {stock_dir}")
            return pd.DataFrame()
        stock_list = [f.split('.')[0] for f in os.listdir(stock_dir) if f.endswith('.csv')]
        print(f"Found {len(stock_list)} stocks in {stock_dir}")


    for ticker in stock_list:
        stock_returns_df = load_single_stock_data(ticker, frequency, start_date, end_date)
        if stock_returns_df is not None and not stock_returns_df.empty:
            all_returns.append(stock_returns_df)

    if not all_returns:
        return pd.DataFrame()

    # 合并所有股票的收益率到一个DataFrame，日期为索引
    # 使用 outer join 以保留所有日期，然后处理 NaN (例如用0填充或前向填充)
    # 这里需要仔细考虑如何处理不同股票交易日不完全匹配的情况
    # 一个简单的方法是只保留所有股票都有数据的日期 (inner join)，但这可能会损失很多数据
    # 或者，更常见的是使用 outer join 然后决定如何填充缺失值
    # 为了演示，我们先用 outer join，然后你可以决定如何处理 NaN
    # 实际操作中，对齐数据非常重要
    combined_df = pd.concat(all_returns, axis=1, join='outer') # 'outer' join to keep all dates

    # 处理合并后可能产生的全NaN行 (如果某天没有任何股票数据)
    combined_df.dropna(axis=0, how='all', inplace=True)

    # 对于个股在某些日期的缺失收益率，可以考虑如何填充
    # 例如，如果某股票当天停牌，其收益率可以认为是0，但这需要小心处理
    # combined_df = combined_df.fillna(0) # 这是一个简化的处理，实际应更细致

    return combined_df


def load_index_data(index_code: str = config.CSI300_CODE,
                    frequency: str = "daily",
                    start_date=None, end_date=None) -> pd.DataFrame | None:
    """
    加载指数数据。
    """
    if frequency == "daily":
        file_path = os.path.join(config.DAILY_INDEX_DATA_DIR, f"{index_code}.csv")
    elif frequency == "monthly":
        file_path = os.path.join(config.MONTHLY_INDEX_DATA_DIR, f"{index_code}.csv")
    else:
        raise ValueError("Frequency must be 'daily' or 'monthly'")

    if not os.path.exists(file_path):
        print(f"Warning: Data file not found for index {index_code} at {file_path}")
        return None
    try:
        df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')
        price_col = 'adj_close' if 'adj_close' in df.columns else 'close' # 指数通常用 'close'
        df = df[[price_col]].rename(columns={price_col: 'price'})

        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]

        df['index_return'] = df['price'].pct_change()
        df = df[['index_return']].dropna()
        return df
    except Exception as e:
        print(f"Error loading or processing data for index {index_code}: {e}")
        return None

# 示例用法 (可以在 main.py 中调用)
# if __name__ == '__main__':
#     # 假设你的数据文件夹结构和config.py配置正确
#     # 并且在 data/daily/stocks/ 下有 000001.SZ.csv 和 600000.SH.csv
#     # 在 data/daily/index/ 下有 000300.SH.csv
#
#     start_date_str = "2020-01-01"
#     end_date_str = "2023-12-31"
#
#     # 加载所有股票日收益率
#     all_daily_stock_returns = load_all_stock_returns(frequency="daily",
#                                                      start_date=start_date_str,
#                                                      end_date=end_date_str)
#     print("All Daily Stock Returns Head:")
#     print(all_daily_stock_returns.head())
#
#     # 加载沪深300日收益率
#     csi300_daily_returns = load_index_data(index_code=config.CSI300_CODE,
#                                            frequency="daily",
#                                            start_date=start_date_str,
#                                            end_date=end_date_str)
#     print("\nCSI 300 Daily Returns Head:")
#     print(csi300_daily_returns.head()) 