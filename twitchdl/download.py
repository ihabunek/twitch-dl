import os
from pathlib import Path
from typing import Tuple

import httpx

from twitchdl.exceptions import ConsoleError

CHUNK_SIZE = 1024
CONNECT_TIMEOUT = 5
RETRY_COUNT = 5


def _download(url: str, target: Path):
    tmp_path = Path(str(target) + ".tmp")
    size = 0
    with httpx.stream("GET", url, timeout=CONNECT_TIMEOUT, follow_redirects=True) as response:
        response.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                size += len(chunk)

    os.rename(tmp_path, target)
    return size


def download_file(url: str, target: Path, retries: int = RETRY_COUNT) -> Tuple[int, bool]:
    if target.exists():
        from_disk = True
        return os.path.getsize(target), from_disk

    from_disk = False
    for _ in range(retries):
        try:
            return _download(url, target), from_disk
        except httpx.RequestError:
            pass

    raise ConsoleError(f"Failed downloading after {retries} attempts: {url}")
