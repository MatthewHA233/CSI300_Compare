class DataSourceError(Exception):
    """Base class for exceptions raised by data source operations."""
    pass

class DataSourceConnectionError(DataSourceError):
    """Raised when there is an error connecting to a data source."""
    pass

class DataNotFoundError(DataSourceError):
    """Raised when requested data is not found in the data source."""
    pass

class InvalidAPIKeyError(DataSourceConnectionError):
    """Raised when an API key is invalid or has insufficient permissions."""
    pass

class APILimitExceededError(DataSourceConnectionError):
    """Raised when API call frequency or quota limits are exceeded."""
    pass

class DataParsingError(DataSourceError):
    """Raised when an error occurs while parsing data from a data source."""
    pass 