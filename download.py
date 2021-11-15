#!/usr/bin/env python3
import asyncio
import httpx
import m3u8
import os
import re
import requests

from rich.console import Console
from rich.progress import Progress, TaskID, TransferSpeedColumn
from twitchdl import twitch
from typing import List

console = Console()

# WORKER_POOL_SIZE = 5
CHUNK_SIZE = 1024 * 256
# CONNECT_TIMEOUT = 5
# RETRY_COUNT = 5


class Bucket:
    capacity: int
    rate: int
    content_kb: int = 0

    KB = 1024
    MB = 1024 * KB
    DEFAULT_CAPACITY = 10 * MB
    DEFAULT_RATE = 1 * MB

    def __init__(self, /, *, capacity=1 * MB, rate=100 * KB):
        self.capacity = capacity
        self.rate = rate


class Downloader:
    downloaded: int = 0
    downloaded_vod_count: int = 0
    progress: Progress
    total_task_id: TaskID
    vod_count: int

    def __init__(self, worker_count: int):
        self.worker_count = worker_count

    async def run(self, sources, targets):
        if len(sources) != len(targets):
            raise ValueError(f"Got {len(sources)} sources but {len(targets)} targets.")

        self.vod_count = len(sources)

        columns = [*Progress.get_default_columns(), TransferSpeedColumn()]
        with Progress(*columns, console=console) as progress:
            self.progress = progress
            self.total_task_id = self.progress.add_task("Total")
            await self.download(sources, targets)
            for task in self.progress.tasks:
                if task.id != self.total_task_id:
                    self.progress.remove_task(task.id)
        console.print("[chartreuse3]Done.[/chartreuse3]")

    def on_init(self, filename: str) -> TaskID:
        return self.progress.add_task(filename)

    def on_start(self, task_id: TaskID, size: int):
        self.downloaded_vod_count += 1
        self.downloaded += size

        estimated_total = int(self.downloaded * self.vod_count / self.downloaded_vod_count)

        self.progress.update(self.total_task_id, total=estimated_total)
        self.progress.update(task_id, total=size)
        self.progress.start_task(task_id)

    def on_progress(self, task_id: TaskID, chunk_size: int):
        self.progress.update(self.total_task_id, advance=chunk_size)
        self.progress.update(task_id, advance=chunk_size)

    def on_end(self, task_id: TaskID):
        async def remove_task_after(task_id, delay):
            await asyncio.sleep(delay)
            self.progress.remove_task(task_id)

        asyncio.create_task(remove_task_after(task_id, 1))

    async def download_one(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        source: str,
        target: str,
    ):
        async with semaphore:
            with open(target, "wb") as f:
                # TODO: handle failure (retries etc)
                task_id = self.on_init(os.path.basename(target))
                async with client.stream("GET", source) as response:
                    size = int(response.headers.get("content-length"))
                    self.on_start(task_id, size)
                    async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        self.on_progress(task_id, len(chunk))
                    self.on_end(task_id)

    async def download(self, sources: List[str], targets: List[str]):
        async with httpx.AsyncClient() as client:
            semaphore = asyncio.Semaphore(self.worker_count)
            tasks = [self.download_one(client, semaphore, source, target)
                     for source, target in zip(sources, targets)]
            await asyncio.gather(*tasks)


if __name__ == "__main__":
    videos = twitch.get_channel_videos("bananasaurus_rex", 1, "time")
    video_id = videos["edges"][0]["node"]["id"]

    from twitchdl.commands.download import _get_vod_paths
    console.print("[grey53]Fetching access token...[/grey53]")
    access_token = twitch.get_access_token(video_id)

    console.print("[grey53]Fetching playlists...[/grey53]")
    playlists = twitch.get_playlists(video_id, access_token)
    playlist_uri = m3u8.loads(playlists).playlists[-1].uri

    console.print("[grey53]Fetching playlist...[/grey53]")
    playlist = requests.get(playlist_uri).text

    vods = _get_vod_paths(m3u8.loads(playlist), None, None)
    base_uri = re.sub("/[^/]+$", "/", playlist_uri)
    urls = ["".join([base_uri, vod]) for vod in vods][:3]
    targets = [f"tmp/{os.path.basename(url).zfill(8)}" for url in urls]

    try:
        print("Starting download using 3 workers")
        d = Downloader(3)
        asyncio.run(d.run(urls, targets))
    except KeyboardInterrupt:
        console.print("[bold red]Aborted.[/bold red]")
