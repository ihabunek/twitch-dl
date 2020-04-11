import os
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import partial
from requests.exceptions import RequestException
from twitchdl.output import print_out
from twitchdl.utils import format_size, format_duration


CHUNK_SIZE = 1024
CONNECT_TIMEOUT = 5
RETRY_COUNT = 5


class DownloadFailed(Exception):
    pass


def _download(url, path):
    tmp_path = path + ".tmp"
    response = requests.get(url, stream=True, timeout=CONNECT_TIMEOUT)
    size = 0
    with open(tmp_path, 'wb') as target:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            target.write(chunk)
            size += len(chunk)

    os.rename(tmp_path, path)
    return size


def download_file(url, path, retries=RETRY_COUNT):
    if os.path.exists(path):
        return 0

    for _ in range(retries):
        try:
            return _download(url, path)
        except RequestException:
            pass

    raise DownloadFailed(":(")


def _print_progress(futures):
    counter = 1
    total = len(futures)
    total_size = 0
    start_time = datetime.now()

    for future in as_completed(futures):
        size = future.result()
        percentage = 100 * counter // total
        total_size += size
        duration = (datetime.now() - start_time).seconds
        speed = total_size // duration if duration else 0
        remaining = (total - counter) * duration / counter

        msg = "Downloaded VOD {}/{} ({}%) total <cyan>{}B</cyan> at <cyan>{}B/s</cyan> remaining <cyan>{}</cyan>".format(
            counter, total, percentage, format_size(total_size), format_size(speed), format_duration(remaining))

        print_out("\r" + msg.ljust(80), end='')
        counter += 1


def download_files(base_url, directory, filenames, max_workers):
    urls = [base_url + f for f in filenames]
    paths = ["/".join([directory, f]) for f in filenames]
    partials = (partial(download_file, url, path) for url, path in zip(urls, paths))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fn) for fn in partials]
        _print_progress(futures)

    return paths
