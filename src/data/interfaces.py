from abc import ABC, abstractmethod
import pandas as pd

class DataSourceInterface(ABC):
    """
    Abstract base class for data source interfaces.
    All data source implementations should inherit from this class
    and implement its abstract methods.
    """

    @abstractmethod
    def connect(self, **kwargs) -> None:
        """
        Establish connection to the data source.
        kwargs can be used to pass authentication details like API tokens,
        username/password, etc., depending on the data source.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the data source.
        """
        pass

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """
        Retrieve the list of available stocks.

        Returns:
            pd.DataFrame: DataFrame containing stock codes, names, etc.
                          Expected columns: ['stock_code', 'stock_name', ...]
        """
        pass

    @abstractmethod
    def get_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Retrieve daily historical market data for a specific stock.

        Args:
            stock_code (str): The code of the stock.
            start_date (str): The start date for the data (YYYY-MM-DD).
            end_date (str): The end date for the data (YYYY-MM-DD).

        Returns:
            pd.DataFrame: DataFrame containing daily market data.
                          Expected columns: ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        """
        pass

    @abstractmethod
    def get_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Retrieve daily historical market data for a specific index.

        Args:
            index_code (str): The code of the index.
            start_date (str): The start date for the data (YYYY-MM-DD).
            end_date (str): The end date for the data (YYYY-MM-DD).

        Returns:
            pd.DataFrame: DataFrame containing daily market data for the index.
                          Expected columns: ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        """
        pass

    @abstractmethod
    def get_risk_free_rate(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Retrieve risk-free rate data for a specified period.

        Args:
            start_date (str): The start date for the data (YYYY-MM-DD).
            end_date (str): The end date for the data (YYYY-MM-DD).

        Returns:
            pd.DataFrame: DataFrame containing dates and corresponding risk-free rates.
                          Expected columns: ['date', 'rate']
        """
        pass 