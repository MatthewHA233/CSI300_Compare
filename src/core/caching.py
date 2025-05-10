import functools
import hashlib
import inspect
import json
import os
import pathlib
from cachetools import TTLCache
from diskcache import Cache as DiskCache
import logging
from typing import Callable, Optional, Any

# --- 默认配置 ---
DEFAULT_TTL_SECONDS = 3600  # 1 hour
DEFAULT_MEMORY_MAX_SIZE = 128
DEFAULT_DISK_CACHE_DIR = ".cache_data"

# --- 内部缓存实例管理 ---
# 使用字典来存储不同参数组合的缓存实例，避免重复创建
_memory_caches = {}
_disk_caches = {}

# Get a logger instance
logger = logging.getLogger(__name__)

def _get_memory_cache(max_size: int, ttl: int) -> TTLCache:
    """获取或创建内存缓存实例"""
    key = (max_size, ttl)
    if key not in _memory_caches:
        _memory_caches[key] = TTLCache(maxsize=max_size, ttl=ttl)
    return _memory_caches[key]

def _get_disk_cache(disk_path: str, ttl: int) -> DiskCache:
    """获取或创建磁盘缓存实例"""
    # 确保路径是绝对路径，或者相对于某个固定点
    # 这里简单处理，实际项目中可能需要更健壮的路径管理
    path = pathlib.Path(disk_path)
    if not path.is_absolute():
        # 假设相对于项目根目录（如果caching.py在src/core下）
        # 这需要根据实际项目结构调整
        # 为简单起见，我们直接使用提供的路径，并确保它存在
        pass # 用户需要确保disk_path是有效的
    
    path.mkdir(parents=True, exist_ok=True)
    
    key = str(path.resolve()) # 使用解析后的绝对路径作为键
    if key not in _disk_caches:
        # diskcache 的 Cache 类没有直接的ttl参数在构造时，但可以在set时指定
        # 不过，我们可以通过 eviction_policy='least-recently-used' 和 size_limit 来管理
        # 或者在get的时候检查过期（diskcache会自动处理tag_index的过期）
        # 为了简单起见，我们依赖diskcache内部的过期处理（如果它支持的话，或通过set时的expire参数）
        # DiskCache 的 timeout 参数用于连接，不是TTL
        _disk_caches[key] = DiskCache(directory=str(path))
    return _disk_caches[key]

def _generate_cache_key(func, *args, **kwargs) -> str:
    """为函数调用生成一个唯一的、可哈希的缓存键"""
    # 获取函数签名以区分默认参数
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    # 包含模块名、类名（如果有）、函数名
    key_parts = [func.__module__, func.__qualname__]

    # 包含所有最终应用的参数（位置参数和关键字参数）
    # 为了稳定性，对字典参数按键排序
    for k, v in bound_args.arguments.items():
        key_parts.append(k)
        # 如果参数是复杂对象，json序列化可能失败或不稳定
        # 对于本项目中的数据获取，参数通常是字符串、数字等简单类型
        # 如果要缓存更复杂对象的方法，这里需要更健壮的序列化
        try:
            key_parts.append(json.dumps(v, sort_keys=True, default=str))
        except TypeError:
            key_parts.append(repr(v)) # 回退到repr

    # 使用hashlib确保键的长度可控且为字符串
    # 使用UTF-8编码
    hasher = hashlib.md5()
    hasher.update("||".join(key_parts).encode('utf-8'))
    return hasher.hexdigest()

def cached_method(
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    cache_type: str = 'memory',
    max_size: int = DEFAULT_MEMORY_MAX_SIZE,
    disk_path: str = DEFAULT_DISK_CACHE_DIR,
    # New callback parameters
    on_cache_hit: Optional[Callable[[str, str, str], None]] = None, # func_name, key, cache_type
    on_cache_miss: Optional[Callable[[str, str, str], None]] = None, # func_name, key, cache_type
    on_cache_set: Optional[Callable[[str, str, Any, str], None]] = None, # func_name, key, value, cache_type
    on_cache_get_error: Optional[Callable[[str, str, str, Exception], None]] = None, # func_name, key, cache_type, error
    on_cache_set_error: Optional[Callable[[str, str, Any, str, Exception], None]] = None # func_name, key, value, cache_type, error
):
    """
    一个可配置的缓存装饰器，支持内存和磁盘缓存，TTL，日志记录和回调。

    Args:
        ttl_seconds (int): 缓存条目的存活时间（秒）。
        cache_type (str): 缓存类型，'memory' 或 'disk'。
        max_size (int): 当 cache_type 为 'memory' 时，内存缓存的最大条目数。
        disk_path (str): 当 cache_type 为 'disk' 时，磁盘缓存的存储目录。
        on_cache_hit (Optional[Callable]): 缓存命中时的回调。
            Args: (func_name: str, cache_key: str, cache_type: str)
        on_cache_miss (Optional[Callable]): 缓存未命中时的回调。
            Args: (func_name: str, cache_key: str, cache_type: str)
        on_cache_set (Optional[Callable]): 成功设置缓存时的回调。
            Args: (func_name: str, cache_key: str, value: Any, cache_type: str)
        on_cache_get_error (Optional[Callable]): 获取缓存出错时的回调。
            Args: (func_name: str, cache_key: str, cache_type: str, error: Exception)
        on_cache_set_error (Optional[Callable]): 设置缓存出错时的回调。
            Args: (func_name: str, cache_key: str, value: Any, cache_type: str, error: Exception)
    """
    if cache_type not in ['memory', 'disk']:
        raise ValueError("cache_type must be 'memory' or 'disk'")

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__ # Get qualified name (e.g., Class.method)
            cache_key = _generate_cache_key(func, *args, **kwargs)
            
            cache_instance = None
            is_disk_cache = False

            try:
                if cache_type == 'memory':
                    cache_instance = _get_memory_cache(max_size=max_size, ttl=ttl_seconds)
                elif cache_type == 'disk':
                    cache_instance = _get_disk_cache(disk_path=disk_path, ttl=ttl_seconds)
                    is_disk_cache = True
            except Exception as e_init:
                logger.error(f"Cache INIT ERROR for {func_name} (type: {cache_type}): {e_init}", exc_info=True)
                # If cache init fails, just call the original function without caching
                return func(*args, **kwargs)

            cached_value = None # Initialize to ensure it's defined
            cache_hit = False

            # 尝试从缓存获取
            if cache_instance is not None:
                try:
                    if is_disk_cache:
                        # DiskCache's get correctly returns None if key not found or expired (if expire was used in set)
                        cached_value = cache_instance.get(cache_key, default=None) 
                    else: # Memory (TTLCache)
                        cached_value = cache_instance[cache_key] # TTLCache raises KeyError on miss or expiry
                    
                    # If we are here and cached_value came from TTLCache, it's a hit because no KeyError.
                    # If cached_value came from DiskCache and is not None, it's a hit.
                    if not (is_disk_cache and cached_value is None): # This condition means it's a hit
                        logger.debug(f"Cache HIT for {func_name} (key: {cache_key}, type: {cache_type})")
                        if on_cache_hit:
                            try:
                                on_cache_hit(func_name, cache_key, cache_type)
                            except Exception as e_cb:
                                logger.error(f"Error in on_cache_hit callback for {func_name}: {e_cb}", exc_info=True)
                        cache_hit = True
                        return cached_value
                    else: # Specifically for DiskCache miss where get returns None
                        logger.debug(f"Cache MISS (DiskCache returned None) for {func_name} (key: {cache_key}, type: {cache_type})")
                        if on_cache_miss:
                            try:
                                on_cache_miss(func_name, cache_key, cache_type)
                            except Exception as e_cb:
                                logger.error(f"Error in on_cache_miss callback for {func_name}: {e_cb}", exc_info=True)
                        # cache_hit remains False, cached_value is None
                
                except KeyError: # Specifically for TTLCache miss/expiry
                    logger.debug(f"Cache MISS (TTLCache KeyError) for {func_name} (key: {cache_key}, type: {cache_type})")
                    if on_cache_miss:
                        try:
                            on_cache_miss(func_name, cache_key, cache_type)
                        except Exception as e_cb:
                            logger.error(f"Error in on_cache_miss callback for {func_name}: {e_cb}", exc_info=True)
                    # cache_hit remains False, cached_value is implicitly None now
                
                except Exception as e_get:
                    logger.error(f"Cache GET ERROR for {func_name} (key: {cache_key}, type: {cache_type}): {e_get}", exc_info=True)
                    if on_cache_get_error:
                        try:
                            on_cache_get_error(func_name, cache_key, cache_type, e_get)
                        except Exception as e_cb:
                            logger.error(f"Error in on_cache_get_error callback for {func_name}: {e_cb}", exc_info=True)
                    # Proceed to call original function as if it was a miss
                    # cache_hit remains False, cached_value is None
            
            # If cache_hit is False at this point, it means it was a miss or an error during GET.
            # The on_cache_miss callback should have been called already if applicable.
            if not cache_hit:
                 logger.debug(f"Proceeding to execute original function {func_name} due to cache miss or GET error.")
            
            result = func(*args, **kwargs)

            # 存储到缓存
            if cache_instance is not None:
                try:
                    if is_disk_cache:
                        cache_instance.set(cache_key, result, expire=ttl_seconds)
                    else: # Memory (TTLCache)
                        cache_instance[cache_key] = result # TTLCache handles its own TTL based on initialization
                    logger.debug(f"Cache SET for {func_name} (key: {cache_key}, type: {cache_type})")
                    if on_cache_set:
                        try:
                            # Be cautious if 'result' is very large, might impact callback performance or logging.
                            on_cache_set(func_name, cache_key, "<value_omitted_for_ brevity>" if len(str(result)) > 100 else result, cache_type)
                        except Exception as e_cb:
                            logger.error(f"Error in on_cache_set callback for {func_name}: {e_cb}", exc_info=True)
                except Exception as e_set:
                    logger.error(f"Cache SET ERROR for {func_name} (key: {cache_key}, type: {cache_type}): {e_set}", exc_info=True)
                    if on_cache_set_error:
                        try:
                            on_cache_set_error(func_name, cache_key, "<value_omitted_for_ brevity>", cache_type, e_set)
                        except Exception as e_cb:
                            logger.error(f"Error in on_cache_set_error callback for {func_name}: {e_cb}", exc_info=True)
            
            return result
        return wrapper
    return decorator

# --- 示例用法 (可选，用于测试) ---
# if __name__ == "__main__":
#     # 配置日志以便查看内部信息（如果添加了日志的话）
#     # from logging_utils import setup_logging # 假设在同级或可导入
#     # setup_logging(logging.DEBUG)

#     @cached_method(ttl_seconds=5, cache_type='memory', max_size=2)
#     def expensive_calculation_memory(a, b):
#         print(f"Memory: Performing expensive calculation with {a}, {b}...")
#         import time
#         time.sleep(1)
#         return a + b

#     print(expensive_calculation_memory(1, 2))  # 计算
#     print(expensive_calculation_memory(1, 2))  # 缓存
#     print(expensive_calculation_memory(2, 3))  # 计算
#     print(expensive_calculation_memory(3, 4))  # 计算 (max_size=2, (1,2)可能被挤出)
#     print(expensive_calculation_memory(1, 2))  # 重新计算 (如果(1,2)被挤出)
#     print(expensive_calculation_memory(2, 3))  # 缓存 (如果(2,3)还在)


#     DISK_CACHE_TEST_PATH = "./.test_cache_dir_caching_py"
#     # 清理之前的测试缓存
#     import shutil
#     if os.path.exists(DISK_CACHE_TEST_PATH):
#         shutil.rmtree(DISK_CACHE_TEST_PATH)

#     @cached_method(ttl_seconds=5, cache_type='disk', disk_path=DISK_CACHE_TEST_PATH)
#     def expensive_calculation_disk(x, y, z=10):
#         print(f"Disk: Performing expensive calculation with {x}, {y}, {z}...")
#         import time
#         time.sleep(1)
#         return x * y * z

#     print(expensive_calculation_disk(2, 3)) # 计算
#     print(expensive_calculation_disk(2, 3)) # 缓存
#     print(expensive_calculation_disk(2, 3, z=100)) # 计算 (参数不同)
#     print(expensive_calculation_disk(2, 3, z=100)) # 缓存

#     print("Waiting for TTL to expire (5 seconds)...")
#     import time
#     time.sleep(6)
#     print(expensive_calculation_disk(2, 3)) # 应重新计算

#     # 清理测试缓存
#     if os.path.exists(DISK_CACHE_TEST_PATH):
#         shutil.rmtree(DISK_CACHE_TEST_PATH)
#     print("Test cache cleaned up.") 