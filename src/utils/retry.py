"""Retry utilities for ingestion sources."""

import logging
from typing import Callable

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from src.ingestion.errors import TransientError

logger = logging.getLogger(__name__)


def retry_on_transient_error(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 60,
) -> Callable:
    """Decorator to retry functions that may raise TransientError.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_transient_error(max_attempts=3)
        def download_data(url):
            response = requests.get(url)
            if response.status_code == 429:
                raise TransientError("Rate limited")
            return response.json()
    """
    return retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )
