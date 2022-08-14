import logging
import time

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, Optional

from twitchdl.output import print_out
from twitchdl.utils import format_size, format_duration

logger = logging.getLogger(__name__)


TaskId = int


@dataclass
class Task:
    id: TaskId
    size: int
    downloaded: int = 0

    def advance(self, size):
        self.downloaded += size


@dataclass
class Progress:
    vod_count: int
    downloaded: int = 0
    estimated_total: Optional[int] = None
    progress_bytes: int = 0
    progress_perc: int = 0
    remaining_time: Optional[int] = None
    speed: Optional[float] = None
    start_time: float = field(default_factory=time.time)
    tasks: Dict[TaskId, Task] = field(default_factory=dict)
    vod_downloaded_count: int = 0

    def start(self, task_id: int, size: int):
        logger.debug(f"#{task_id} start {size}b")

        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot start, already started")

        self.tasks[task_id] = Task(task_id, size)
        self._calculate_total()
        self._calculate_progress()
        self.print()

    def advance(self, task_id: int, chunk_size: int):
        logger.debug(f"#{task_id} advance {chunk_size}")

        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot advance, not started")

        self.downloaded += chunk_size
        self.progress_bytes += chunk_size
        self.tasks[task_id].advance(chunk_size)
        self._calculate_progress()
        self.print()

    def already_downloaded(self, task_id: int, size: int):
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id}: cannot mark as downloaded, already started")

        self.tasks[task_id] = Task(task_id, size)
        self.progress_bytes += size
        self.vod_downloaded_count += 1
        self._calculate_total()
        self._calculate_progress()
        self.print()

    def abort(self, task_id: int):
        logger.debug(f"#{task_id} abort")

        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot abort, not started")

        del self.tasks[task_id]
        self.progress_bytes = sum(t.downloaded for t in self.tasks.values())

        self._calculate_total()
        self._calculate_progress()
        self.print()

    def end(self, task_id: int):
        logger.debug(f"#{task_id} end")

        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id}: cannot end, not started")

        task = self.tasks[task_id]
        if task.size != task.downloaded:
            logger.warn(f"Taks {task_id} ended with {task.downloaded}b downloaded, expected {task.size}b.")

        self.vod_downloaded_count += 1
        self.print()

    def _calculate_total(self):
        self.estimated_total = int(mean(t.size for t in self.tasks.values()) * self.vod_count) if self.tasks else None

    def _calculate_progress(self):
        elapsed_time = time.time() - self.start_time
        self.progress_perc = int(100 * self.progress_bytes / self.estimated_total) if self.estimated_total else 0
        self.speed = self.downloaded / elapsed_time if elapsed_time else None
        self.remaining_time = int((self.estimated_total - self.progress_bytes) / self.speed) if self.estimated_total and self.speed else None

    def print(self):
        progress = " ".join([
            f"Downloaded {self.vod_downloaded_count}/{self.vod_count} VODs",
            f"({self.progress_perc}%)",
            f"<cyan>{format_size(self.progress_bytes)}</cyan>",
            f"of <cyan>~{format_size(self.estimated_total)}</cyan>" if self.estimated_total else "",
            f"at <cyan>{format_size(self.speed)}/s</cyan>" if self.speed else "",
            f"remaining <cyan>~{format_duration(self.remaining_time)}</cyan>" if self.remaining_time is not None else "",
        ])

        print_out(f"\r{progress}     ", end="")
