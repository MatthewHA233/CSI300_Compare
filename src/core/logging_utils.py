import logging
import sys

DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL = logging.INFO

def setup_logging(level=DEFAULT_LOG_LEVEL, log_format=DEFAULT_LOG_FORMAT, stream=sys.stdout):
    """
    Set up basic logging configuration.

    Args:
        level (int, optional): The logging level. Defaults to logging.INFO.
        log_format (str, optional): The log message format. 
                                 Defaults to '%(asctime)s - %(name)s - %(levelname)s - %(message)s'.
        stream (IO, optional): The output stream for the log. Defaults to sys.stdout.
    """
    logging.basicConfig(level=level, format=log_format, stream=stream)

def get_logger(name: str):
    """
    Retrieves a logger instance with the specified name.

    Args:
        name (str): The name for the logger (usually __name__).

    Returns:
        logging.Logger: The logger instance.
    """
    return logging.getLogger(name)

# Example of how to use it (optional, can be called by the application entry point):
# if __name__ == '__main__':
#     setup_logging(level=logging.DEBUG)
#     logger = get_logger(__name__)
#     logger.debug("This is a debug message from logging_utils.")
#     logger.info("This is an info message from logging_utils.")
#     logger.warning("This is a warning message from logging_utils.") 