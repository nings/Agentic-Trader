"""重试机制"""

import time
import logging
from typing import Callable, TypeVar, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    重试装饰器（指数退避）

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        exceptions: 需要重试的异常类型

    Example:
        @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

            raise RuntimeError(f"{func.__name__} failed after all retries")

        return wrapper
    return decorator
