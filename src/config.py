import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # 这会加载 .env 文件中的变量到环境变量中

# --- 数据路径配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 项目根目录
DATA_DIR = os.path.join(BASE_DIR, "data")

DAILY_STOCK_DATA_DIR = os.path.join(DATA_DIR, "daily", "stocks")
MONTHLY_STOCK_DATA_DIR = os.path.join(DATA_DIR, "monthly", "stocks")
DAILY_INDEX_DATA_DIR = os.path.join(DATA_DIR, "daily", "index")
MONTHLY_INDEX_DATA_DIR = os.path.join(DATA_DIR, "monthly", "index")

# --- 指数代码 ---
CSI300_CODE = "000300.SH" # 假设沪深300指数文件名为 000300.SH.csv

# --- 时间范围 ---
# 假设从5年前的今天开始，到今天结束
# 你可以根据实际数据情况修改
END_DATE = datetime.now()
# START_DATE = END_DATE - timedelta(days=5*365) # 更精确的计算需要考虑闰年
# 为简化，先硬编码，后续可以改为动态计算
# 例如: START_DATE_STR = "2019-01-01"
# END_DATE_STR = "2023-12-31"

# --- 业绩计算参数 ---
RISK_FREE_RATE = 0.02  # 年化无风险利率, 例如 2%
TRADING_DAYS_PER_YEAR_DAILY = 252 # 日度数据每年的交易日数量
TRADING_PERIODS_PER_YEAR_MONTHLY = 12 # 月度数据每年的期数

# --- 股票列表 ---
# "中国市场所有的股票" 是一个动态且庞大的列表。
# 你需要一种方式来获取这个列表。
# 可能是从一个文件中读取，或者在 data_loader 中动态发现。
# 如果文件过多，直接列出不现实。
# 假设 data_loader 会扫描对应文件夹下的所有股票文件。

# --- Tushare Token ---
# 从环境变量中获取 Tushare token
TUSHARE_API_TOKEN = os.getenv("TUSHARE_TOKEN")

# if TUSHARE_API_TOKEN is None:
#     print("Warning: TUSHARE_TOKEN not found in environment variables. Tushare functionality will be limited.") 