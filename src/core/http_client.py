import logging
import time
from typing import Callable, Optional, Any # For type hints
import functools # For functools.wraps
import os # For PID logging, if desired

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 默认配置
DEFAULT_TIMEOUT_SECONDS = 10  # 连接和读取超时均为10秒
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3 # 重试之间的等待时间因子
DEFAULT_USER_AGENT = "CSI300_Compare_Project/1.0 (Python Requests)"

class HTTPSessionManager:
    """
    管理和配置 `requests.Session` 对象，用于高效的HTTP API调用。
    支持通用的超时、重试策略和请求头配置。

    内置的重试机制通过 `urllib3.util.retry.Retry` 实现，并应用于所有通过此会话发出的HTTP/HTTPS请求。
    默认的重试参数如下:
    - 最大总重试次数 (`max_retries`): 3 次。
    - 连接相关错误重试次数: 3 次。
    - 读取相关错误重试次数: 3 次。
    - 退避因子 (`backoff_factor`): 0.3。这会影响重试间的等待时间，
      计算方式为: `backoff_factor * (2 ** (重试次数 - 1))`。
      例如，等待时间序列大致为: 0s, 0.6s, 1.2s。
    - 强制重试的HTTP状态码 (`status_forcelist`): (500, 502, 503, 504)。
      这些是表示服务器端临时错误的常见状态码。
    - 允许重试的HTTP方法: HEAD, GET, PUT, DELETE, OPTIONS, TRACE, POST。
      (对于POST方法的重试，请确保操作的幂等性)。
    这些参数可以在实例化 `HTTPSessionManager` 时进行覆盖。
    """
    _session_instance: Optional[requests.Session] = None
    logger = logging.getLogger(__name__) # Class-level logger

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        user_agent: str = DEFAULT_USER_AGENT,
        status_forcelist: tuple = (500, 502, 503, 504),
        on_request_success: Optional[Callable[[requests.Response, float], None]] = None,
        on_request_failure: Optional[Callable[[str, Exception, int, float], None]] = None # url_method_str, exc, attempts, duration
    ):
        """
        初始化 HTTPSessionManager。
        通常，这个类会被实例化一次，并在应用中复用其 get_session() 方法。

        Args:
            timeout (int): 默认的连接和读取超时时间（秒）。
            max_retries (int): 最大重试次数。
            backoff_factor (float): 重试等待时间的退避因子。
            user_agent (str): 默认的User-Agent请求头。
            status_forcelist (tuple): 需要触发重试的HTTP状态码元组。
            on_request_success (Optional[Callable]): Callback for successful requests.
                                                  Args: response_obj, duration_seconds.
            on_request_failure (Optional[Callable]): Callback for failed requests (after all retries).
                                                  Args: url_method_string, exception_obj, attempt_count, duration_seconds.
        """
        # Store callbacks and configuration on the instance for the wrapped request method to access
        self.on_request_success = on_request_success
        self.on_request_failure = on_request_failure
        self.timeout_config = timeout # For the wrapped request to potentially use
        # Other configs like max_retries are used during session creation only if it's the first time
        
        if HTTPSessionManager._session_instance is None:
            self.logger.info(f"First HTTPSessionManager instance. Creating shared session. PID: {os.getpid()}")
            self._create_and_configure_session(
                timeout=timeout,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                user_agent=user_agent,
                status_forcelist=status_forcelist
            )
        else:
            self.logger.debug(f"HTTPSessionManager re-instantiated, but shared session already exists. PID: {os.getpid()}")
            # Ensure current instance also has access to callbacks if they were provided to this specific instantiation
            # This is a bit tricky if _session_instance is shared and configured by the *first* instance.
            # The callbacks are instance-specific via self.on_request_success etc.
            # The wrapped request method on the *shared* session will need access to the *correct* instance's callbacks.
            # This current singleton-like model for _session_instance makes instance-specific callbacks for a shared session complex.
            # A better model might be a factory that returns configured sessions, or instance-specific sessions.
            # For now, the wrapped method will refer to `self` of the instance whose `get_session` was used to make the call,
            # assuming get_session is called on an instance.
            pass 

        # These are instance-specific attributes, separate from the shared session's direct config
        self.timeout_default_for_requests = timeout
        self.user_agent_used_at_creation = user_agent # Just for reference

    def _create_and_configure_session(self, timeout, max_retries, backoff_factor, user_agent, status_forcelist):
        session = requests.Session()
        session.headers.update({'User-Agent': user_agent})

        retry_strategy = Retry(
            total=max_retries, read=max_retries, connect=max_retries,
            backoff_factor=backoff_factor, status_forcelist=status_forcelist,
            allowed_methods=frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE', 'POST'])
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Storing the timeout on the session for potential use by the wrapper, not a direct requests feature.
        session.timeout_config = timeout 

        original_request_method = session.request

        @functools.wraps(original_request_method)
        def wrapped_request(*args, **kwargs_request):
            # `self` here refers to the HTTPSessionManager instance whose get_session() was called,
            # which then returned this wrapped session.request.
            # This is crucial for callbacks to be instance-specific if manager instances are not singletons.
            
            # Determine method and URL for logging
            rq_method = kwargs_request.get('method', args[0] if args else None)
            rq_url = kwargs_request.get('url', args[1] if len(args) > 1 else None)
            
            # Use the instance's timeout_default_for_requests if no timeout is specified in the call
            if 'timeout' not in kwargs_request:
                kwargs_request['timeout'] = self.timeout_default_for_requests

            self.logger.debug(f"HTTP Request START: {rq_method} {rq_url}, Params: {kwargs_request.get('params')}, Timeout: {kwargs_request.get('timeout')}")
            start_time = time.monotonic()
            
            # attempt_count is tricky to get from outside Retry; for failure, assume max_retries were used up.
            # For simplicity, we pass max_retries + 1 as attempts for the on_request_failure callback.
            max_attempts_for_failure_cb = max_retries + 1 

            try:
                response = original_request_method(*args, **kwargs_request)
                duration_seconds = time.monotonic() - start_time
                self.logger.info(
                    f"HTTP Request SUCCESS: {rq_method} {rq_url} -> Status: {response.status_code} in {duration_seconds:.4f}s"
                )
                if self.on_request_success: # Callback from the specific manager instance
                    try:
                        self.on_request_success(response, duration_seconds)
                    except Exception as e_cb:
                        self.logger.error(f"Error in on_request_success callback: {e_cb}", exc_info=True)
                return response
            except requests.exceptions.RequestException as e:
                duration_seconds = time.monotonic() - start_time
                self.logger.error(
                    f"HTTP Request FAILED (final): {rq_method} {rq_url} after {max_retries} retries in {duration_seconds:.4f}s. Error: {e}",
                    exc_info=True 
                )
                if self.on_request_failure: # Callback from the specific manager instance
                    try:
                        # Construct a string for the first arg of on_request_failure as context
                        url_method_str = f"{rq_method} {rq_url}"
                        self.on_request_failure(url_method_str, e, max_attempts_for_failure_cb, duration_seconds)
                    except Exception as e_cb:
                        self.logger.error(f"Error in on_request_failure callback: {e_cb}", exc_info=True)
                raise
        
        session.request = wrapped_request
        HTTPSessionManager._session_instance = session

    def get_session(self) -> requests.Session:
        """
        获取配置好的 `requests.Session` 实例。
        
        Returns:
            requests.Session: 配置好的会话对象。
        """
        if HTTPSessionManager._session_instance is None:
            self.logger.info("Shared session not yet created. Initializing with default parameters via get_session().")
            # Call __init__ with defaults to trigger _create_and_configure_session
            # Pass current instance's callbacks if they were meant to be defaults for the first session.
            # This part of singleton + instance-specific config/callbacks is complex.
            # A cleaner way: make HTTPSessionManager a true singleton or a factory.
            # For now, let's assume __init__ with defaults sets up the first shared session correctly.
            HTTPSessionManager() # Calls __init__ with default values
            
        return HTTPSessionManager._session_instance

# --- 全局实例 (可选，方便直接导入和使用) ---
# manager = HTTPSessionManager()
# def get_default_session():
#     return manager.get_session()

# --- 示例用法 (可选，用于测试) ---
# if __name__ == "__main__":
#     # from .logging_utils import setup_logging, get_logger # 需要logging_utils在正确的路径
#     # import logging
#     # setup_logging(level=logging.DEBUG)
#     # logger = get_logger(__name__)

#     # 首次创建，会配置session
#     session_manager = HTTPSessionManager(timeout=5, max_retries=2)
#     session1 = session_manager.get_session()
#     print(f"Session 1 User-Agent: {session1.headers.get('User-Agent')}")
#     print(f"Session 1 Timeout (custom attr): {getattr(session1, 'timeout_config', None)}")

#     # 后续获取，会返回同一个已配置的session实例
#     session_manager2 = HTTPSessionManager() # 构造函数不会重新创建 _session_instance
#     session2 = session_manager2.get_session()
#     assert session1 is session2
#     print("Session1 and Session2 are the same instance.")

#     # 测试超时和重试 (需要一个会超时的URL或导致特定状态码的URL)
#     # try:
#     #     # 这个URL会连接超时
#     #     response = session1.get("http://localhost:12345", timeout=getattr(session1, 'timeout_config', DEFAULT_TIMEOUT_SECONDS))
#     #     logger.info(f"Response status: {response.status_code}")
#     # except requests.exceptions.RequestException as e:
#     #     logger.error(f"Request failed: {e}")

#     # print("Done with example.") 