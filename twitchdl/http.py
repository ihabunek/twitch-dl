import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import (
    AsyncIterable,
    Awaitable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

import httpx
from typing_extensions import override

from twitchdl.entities import TaskID
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

Source = Union[str, Awaitable[str]]


@dataclass
class Task:
    task_id: TaskID
    source: Source
    target: Path
    url: Optional[str] = None

    async def get_url(self) -> str:
        if not self.url:
            if isinstance(self.source, str):
                self.url = self.source
            else:
                self.url = await self.source
        return self.url


@dataclass
class TaskResult(ABC):
    task_id: TaskID
    target: Path

    @property
    def ok(self) -> bool:
        return isinstance(self, TaskSuccess)


@dataclass
class TaskSuccess(TaskResult):
    url: str
    size: int
    existing: bool


@dataclass
class TaskError(TaskResult):
    url: Optional[str]
    exception: Exception


@dataclass
class TaskCanceled(TaskResult):
    url: Optional[str]


class TokenBucket(ABC):
    @abstractmethod
    async def advance(self, size: int):
        pass


class LimitingTokenBucket(TokenBucket):
    """Limit the download speed by strategically inserting sleeps."""

    def __init__(self, rate: int, capacity: Optional[int] = None):
        self.rate: int = rate
        self.capacity: int = capacity or rate * 2
        self.available: int = 0
        self.last_refilled: float = time.time()

    @override
    async def advance(self, size: int):
        """Called every time a chunk of data is downloaded."""
        self._refill()

        if self.available < size:
            deficit = size - self.available
            await asyncio.sleep(deficit / self.rate)

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

    @override
    async def advance(self, size: int):
        pass


async def download(
    client: httpx.AsyncClient,
    task_id: int,
    source: str,
    target: Path,
    progress: Progress,
    token_bucket: TokenBucket,
) -> int:
    # Download to a temp file first, then copy to target when over to avoid
    # getting saving chunks which may persist if canceled or --keep is used
    downloaded_size = 0

    with open(target, "wb") as f:
        async with client.stream("GET", source) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length"))
            progress.content_length(task_id, content_length)

            async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                chunk_size = len(chunk)
                downloaded_size += chunk_size
                await token_bucket.advance(chunk_size)
                progress.advance(task_id, chunk_size)

    return downloaded_size


async def download_with_retries(
    client: httpx.AsyncClient,
    task_id: int,
    source: str,
    target: Path,
    progress: Progress,
    token_bucket: TokenBucket,
    skip_existing: bool,
) -> TaskResult:
    if skip_existing and target.exists():
        size = os.path.getsize(target)
        progress.already_downloaded(task_id, source, target, size)
        return TaskSuccess(task_id, target, source, size, existing=True)

    # Download to a temp file first, then rename to target when over to avoid
    # getting saving chunks which may persist if canceled or --keep is used
    tmp_target = Path(f"{target}.tmp")

    progress.start(task_id, source, target)
    for n in range(RETRY_COUNT):
        try:
            size = await download(client, task_id, source, tmp_target, progress, token_bucket)
            progress.end(task_id)
            os.rename(tmp_target, target)
            return TaskSuccess(task_id, target, source, size, existing=False)
        except httpx.HTTPError as ex:
            if n + 1 >= RETRY_COUNT:
                progress.failed(task_id, ex)
                tmp_target.unlink(missing_ok=True)
                return TaskError(task_id, target, source, ex)
            else:
                progress.abort(task_id, ex)
        except Exception as ex:
            progress.failed(task_id, ex)
            tmp_target.unlink(missing_ok=True)
            return TaskError(task_id, target, source, ex)

    raise Exception("Should not happen")


class DownloadAllResult(NamedTuple):
    ok: bool
    results: List[TaskResult]

    @property
    def exceptions(self):
        return [r.exception for r in self.results if isinstance(r, TaskError)]


async def download_all(
    source_targets: AsyncIterable[Tuple[Source, Path]],
    worker_count: int,
    *,
    allow_failures: bool = True,
    skip_existing: bool = True,
    rate_limit: Optional[int] = None,
    progress: Optional[Progress] = None,
) -> DownloadAllResult:
    """Download files concurently."""
    progress = progress or Progress()
    token_bucket = LimitingTokenBucket(rate_limit) if rate_limit else EndlessTokenBucket()
    queue: asyncio.Queue[Task] = asyncio.Queue()
    tasks: List[Task] = []
    results_map: Mapping[TaskID, TaskResult] = {}

    async def producer():
        index = 0
        async for source, target in source_targets:
            task = Task(index, source, target)
            await queue.put(task)
            tasks.append(task)
            index += 1
        await queue.join()

    async def worker(client: httpx.AsyncClient, worker_id: int):
        while True:
            task = await queue.get()
            url = await task.get_url()
            result = await download_with_retries(
                client,
                task.task_id,
                url,
                task.target,
                progress,
                token_bucket,
                skip_existing,
            )
            results_map[task.task_id] = result
            if not result.ok and not allow_failures:
                return
            queue.task_done()

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Task which fills the queue and then waits until it is depleted
        producer_task = asyncio.create_task(producer(), name="Producer")

        # Worker tasks to process the download queue
        worker_tasks = [
            asyncio.create_task(worker(client, worker_id), name=f"Downloader {worker_id}")
            for worker_id in range(worker_count)
        ]

        # Wait for queue to deplete or any of the worker tasks to finish,
        # whichever comes first. Worker tasks will only finish if
        # allow_failures is False and a download fails with an exception,
        # otherwise they will run forever and the producer task will finish
        # first.
        await asyncio.wait([producer_task, *worker_tasks], return_when=asyncio.FIRST_COMPLETED)

        success = producer_task.done()

        # Cancel tasks and wait until they are cancelled
        for task in worker_tasks + [producer_task]:
            task.cancel()
        await asyncio.gather(producer_task, *worker_tasks, return_exceptions=True)

        results = [
            results_map.get(t.task_id, TaskCanceled(t.task_id, t.target, t.url)) for t in tasks
        ]
        return DownloadAllResult(success, results)


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
