import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional, Tuple

import httpx

from twitchdl.exceptions import ConsoleError
from twitchdl.progress import Progress

logger = logging.getLogger(__name__)

KB = 1024

CHUNK_SIZE = 256 * KB
"""How much of a VOD to download in each iteration"""

RETRY_COUNT = 5
"""Number of times to retry failed downloads before aborting."""

TIMEOUT = 30
"""
Number of seconds to wait before aborting when there is no network activity.
https://www.python-httpx.org/advanced/#timeout-configuration
"""


class TokenBucket(ABC):
    @abstractmethod
    def advance(self, size: int):
        pass


class LimitingTokenBucket(TokenBucket):
    """Limit the download speed by strategically inserting sleeps."""

    def __init__(self, rate: int, capacity: Optional[int] = None):
        self.rate: int = rate
        self.capacity: int = capacity or rate * 2
        self.available: int = 0
        self.last_refilled: float = time.time()

    def advance(self, size: int):
        """Called every time a chunk of data is downloaded."""
        self._refill()

        if self.available < size:
            deficit = size - self.available
            time.sleep(deficit / self.rate)

        self.available -= size

    def _refill(self):
        """Increase available capacity according to elapsed time since last refill."""
        now = time.time()
        elapsed = now - self.last_refilled
        refill_amount = int(elapsed * self.rate)
        self.available = min(self.available + refill_amount, self.capacity)
        self.last_refilled = now


class EndlessTokenBucket(TokenBucket):
    """Used when download speed is not limited."""

    def advance(self, size: int):
        pass


async def download(
    client: httpx.AsyncClient,
    task_id: int,
    source: str,
    target: Path,
    progress: Progress,
    token_bucket: TokenBucket,
):
    # Download to a temp file first, then copy to target when over to avoid
    # getting saving chunks which may persist if canceled or --keep is used
    tmp_target = f"{target}.tmp"
    with open(tmp_target, "wb") as f:
        async with client.stream("GET", source) as response:
            content_length = response.headers.get("content-length")
            if content_length is None:
                raise ConsoleError('No content length: {}'.format(source))

            size = int(content_length)
            progress.start(task_id, size)
            async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                size = len(chunk)
                token_bucket.advance(size)
                progress.advance(task_id, size)
            progress.end(task_id)
    os.rename(tmp_target, target)


async def download_with_retries(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    task_id: int,
    source: str,
    target: Path,
    progress: Progress,
    token_bucket: TokenBucket,
):
    async with semaphore:
        if target.exists():
            size = os.path.getsize(target)
            progress.already_downloaded(task_id, size)
            return

        for n in range(RETRY_COUNT):
            try:
                return await download(client, task_id, source, target, progress, token_bucket)
            except httpx.RequestError:
                logger.exception("Task {task_id} failed. Retrying. Maybe.")
                progress.abort(task_id)
                if n + 1 >= RETRY_COUNT:
                    raise

        raise Exception("Should not happen")


async def download_all(
    source_targets: Iterable[Tuple[str, Path]],
    workers: int,
    *,
    count: Optional[int] = None,
    rate_limit: Optional[int] = None,
):
    progress = Progress(count)
    token_bucket = LimitingTokenBucket(rate_limit) if rate_limit else EndlessTokenBucket()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        semaphore = asyncio.Semaphore(workers)
        tasks = [
            download_with_retries(
                client,
                semaphore,
                task_id,
                source,
                target,
                progress,
                token_bucket,
            )
            for task_id, (source, target) in enumerate(source_targets)
        ]
        await asyncio.gather(*tasks)


def download_file(url: str, target: Path, retries: int = RETRY_COUNT) -> None:
    """Download URL to given target path with retries"""
    error_message = ""
    for r in range(retries):
        try:
            retry_info = f" (retry {r})" if r > 0 else ""
            logger.info(f"Downloading {url} to {target}{retry_info}")
            return _do_download_file(url, target)
        except httpx.HTTPStatusError as ex:
            logger.error(ex)
            error_message = f"Server responded with HTTP {ex.response.status_code}"
        except httpx.RequestError as ex:
            logger.error(ex)
            error_message = str(ex)

    raise ConsoleError(f"Failed downloading after {retries} attempts: {error_message}")


def _do_download_file(url: str, target: Path) -> None:
    tmp_path = Path(str(target) + ".tmp")

    with httpx.stream("GET", url, timeout=TIMEOUT, follow_redirects=True) as response:
        response.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)

    os.rename(tmp_path, target)
