import logging
import time
from collections import deque
from dataclasses import dataclass
from statistics import mean
from typing import Deque, Dict, NamedTuple, Optional

import click

from twitchdl.output import blue
from twitchdl.utils import format_size, format_time

logger = logging.getLogger(__name__)


TaskId = int


@dataclass
class Task:
    id: TaskId
    size: int
    downloaded: int = 0

    def advance(self, size: int):
        self.downloaded += size


class Sample(NamedTuple):
    downloaded: int
    timestamp: float


class Progress:
    def __init__(self, vod_count: int):
        self.downloaded: int = 0
        self.estimated_total: Optional[int] = None
        self.last_printed: Optional[float] = None
        self.progress_bytes: int = 0
        self.progress_perc: int = 0
        self.remaining_time: Optional[int] = None
        self.samples: Deque[Sample] = deque(maxlen=1000)
        self.speed: Optional[float] = None
        self.tasks: Dict[TaskId, Task] = {}
        self.vod_count = vod_count
        self.vod_downloaded_count: int = 0

    def start(self, task_id: int, size: int):
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot start, already started")

        self.tasks[task_id] = Task(task_id, size)
        self.print()

    def advance(self, task_id: int, size: int):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot advance, not started")

        self.downloaded += size
        self.progress_bytes += size
        self.tasks[task_id].advance(size)
        self.samples.append(Sample(self.downloaded, time.time()))
        self.print()

    def already_downloaded(self, task_id: int, size: int):
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot mark as downloaded, already started")

        self.tasks[task_id] = Task(task_id, size)
        self.progress_bytes += size
        self.vod_downloaded_count += 1
        self.print()

    def abort(self, task_id: int):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot abort, not started")

        del self.tasks[task_id]
        self.progress_bytes = sum(t.downloaded for t in self.tasks.values())
        self.print()

    def end(self, task_id: int):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot end, not started")

        task = self.tasks[task_id]
        if task.size != task.downloaded:
            logger.warn(
                f"Taks {task_id} ended with {task.downloaded}b downloaded, expected {task.size}b."
            )

        self.vod_downloaded_count += 1
        self.print()

    def _recalculate(self):
        self.estimated_total = (
            int(mean(t.size for t in self.tasks.values()) * self.vod_count) if self.tasks else None
        )
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

        click.echo(f"\rDownloaded {self.vod_downloaded_count}/{self.vod_count} VODs", nl=False)
        click.secho(f" {self.progress_perc}%", fg="blue", nl=False)

        if self.estimated_total is not None:
            total = f"~{format_size(self.estimated_total)}"
            click.echo(f" of {blue(total)}", nl=False)

        if self.speed is not None:
            speed = f"{format_size(self.speed)}/s"
            click.echo(f" at {blue(speed)}", nl=False)

        if self.remaining_time is not None:
            click.echo(f" ETA {blue(format_time(self.remaining_time))}", nl=False)

        click.echo("    ", nl=False)

        self.last_printed = now
