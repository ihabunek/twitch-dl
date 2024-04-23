import os

import httpx

from twitchdl.exceptions import ConsoleError

CHUNK_SIZE = 1024
CONNECT_TIMEOUT = 5
RETRY_COUNT = 5


def _download(url: str, path: str):
    tmp_path = path + ".tmp"
    size = 0
    with httpx.stream("GET", url, timeout=CONNECT_TIMEOUT) as response:
        with open(tmp_path, "wb") as target:
            for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                target.write(chunk)
                size += len(chunk)

    os.rename(tmp_path, path)
    return size


def download_file(url: str, path: str, retries: int = RETRY_COUNT):
    if os.path.exists(path):
        from_disk = True
        return (os.path.getsize(path), from_disk)

    from_disk = False
    for _ in range(retries):
        try:
            return (_download(url, path), from_disk)
        except httpx.RequestError:
            pass

    raise ConsoleError(f"Failed downloading after {retries} attempts: {url}")
