import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Deque, Dict, NamedTuple, Optional

import click
from typing_extensions import override

from twitchdl.entities import TaskID
from twitchdl.output import blue, clear_line
from twitchdl.utils import format_size, format_time

logger = logging.getLogger(__name__)


@dataclass
class Task:
    id: TaskID
    size: Optional[int] = None
    downloaded: int = 0

    def advance(self, size: int):
        self.downloaded += size


class Sample(NamedTuple):
    downloaded: int
    timestamp: float


class Progress:
    def already_downloaded(self, task_id: TaskID, source: str, target: Path, size: int):
        """Skipping download since it's already been downloaded"""
        pass

    def start(self, task_id: TaskID, source: str, target: Path):
        """A new download task is started"""
        pass

    def content_length(self, task_id: TaskID, size: int):
        """Received content length from the server"""
        pass

    def advance(self, task_id: TaskID, size: int):
        """Advancing a download task by {size} bytes"""
        pass

    def abort(self, task_id: TaskID, ex: Exception):
        """Download restarting from beginning due to an error."""
        pass

    def failed(self, task_id: TaskID, ex: Exception):
        """Aborting download due to error"""
        pass

    def end(self, task_id: TaskID):
        """Download successfully finished"""
        pass


class PrintingProgress(Progress):
    @override
    def already_downloaded(self, task_id: TaskID, source: str, target: Path, size: int):
        print("already_downloaded", task_id, size)

    @override
    def start(self, task_id: TaskID, source: str, target: Path):
        print("start", task_id)

    @override
    def content_length(self, task_id: TaskID, size: int):
        print("start", task_id, size)

    @override
    def advance(self, task_id: TaskID, size: int):
        pass

    @override
    def abort(self, task_id: TaskID, ex: Exception):
        print("abort", task_id, repr(ex))

    @override
    def failed(self, task_id: TaskID, ex: Exception):
        print("failed", task_id, repr(ex))

    @override
    def end(self, task_id: TaskID):
        print("downloaded", task_id)


class VideoDownloadProgress(Progress):
    def __init__(self, file_count: Optional[int] = None):
        self.downloaded: int = 0
        self.estimated_total: Optional[int] = None
        self.last_printed: Optional[float] = None
        self.progress_bytes: int = 0
        self.progress_perc: int = 0
        self.remaining_time: Optional[int] = None
        self.samples: Deque[Sample] = deque(maxlen=1000)
        self.speed: Optional[float] = None
        self.tasks: Dict[TaskID, Task] = {}
        self.file_count = file_count
        self.downloaded_count: int = 0

    @override
    def start(self, task_id: TaskID, source: str, target: Path):
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot start, already started")

        self.tasks[task_id] = Task(task_id)
        self.print()

    @override
    def content_length(self, task_id: TaskID, size: int):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot set size, not started")

        self.tasks[task_id].size = size
        self.print()

    @override
    def advance(self, task_id: TaskID, size: int):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot advance, not started")

        self.downloaded += size
        self.progress_bytes += size
        self.tasks[task_id].advance(size)
        self.samples.append(Sample(self.downloaded, time.time()))
        self.print()

    @override
    def already_downloaded(self, task_id: TaskID, source: str, target: Path, size: int):
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot mark as downloaded, already started")

        self.tasks[task_id] = Task(task_id, size)
        self.progress_bytes += size
        self.downloaded_count += 1
        self.print()

    @override
    def abort(self, task_id: TaskID, ex: Exception):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot abort, not started")

        del self.tasks[task_id]
        self.progress_bytes = sum(t.downloaded for t in self.tasks.values())
        self.print()

    @override
    def end(self, task_id: TaskID):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot end, not started")

        task = self.tasks[task_id]
        if task.size != task.downloaded:
            logger.warning(
                f"Taks {task_id} ended with {task.downloaded}b downloaded, expected {task.size}b."
            )

        self.downloaded_count += 1
        self.print()

    def _recalculate(self):
        if self.file_count:
            sizes = [t.size for t in self.tasks.values() if t.size]
            if sizes:
                self.estimated_total = int(mean(sizes) * self.file_count)

        self.speed = self._calculate_speed()
        self.progress_perc = (
            int(100 * self.progress_bytes / self.estimated_total) if self.estimated_total else 0
        )
        self.remaining_time = (
            int((self.estimated_total - self.progress_bytes) / self.speed)
            if self.estimated_total and self.speed
            else None
        )

    def _calculate_speed(self):
        if len(self.samples) < 2:
            return None

        first_sample = self.samples[0]
        last_sample = self.samples[-1]

        size = last_sample.downloaded - first_sample.downloaded
        duration = last_sample.timestamp - first_sample.timestamp

        return size / duration if duration > 0 else None

    def print(self):
        now = time.time()

        # Don't print more often than 10 times per second
        if self.last_printed and now - self.last_printed < 0.1:
            return

        self._recalculate()

        clear_line()
        total_label = f"/{self.file_count}" if self.file_count else ""
        click.echo(f"Downloaded {self.downloaded_count}{total_label} VODs", nl=False)
        click.secho(f" {self.progress_perc}%", fg="blue", nl=False)

        if self.estimated_total is not None:
            total = f"~{format_size(self.estimated_total)}"
            click.echo(f" of {blue(total)}", nl=False)

        if self.speed is not None:
            speed = f"{format_size(self.speed)}/s"
            click.echo(f" at {blue(speed)}", nl=False)

        if self.remaining_time is not None:
            click.echo(f" ETA {blue(format_time(self.remaining_time))}", nl=False)

        self.last_printed = now
