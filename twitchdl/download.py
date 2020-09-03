import os
import requests

from collections import OrderedDict
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
        return os.path.getsize(path)

    for _ in range(retries):
        try:
            return _download(url, path)
        except RequestException:
            pass

    raise DownloadFailed(":(")


def _print_progress(futures):
    downloaded_count = 0
    downloaded_size = 0
    max_msg_size = 0
    start_time = datetime.now()
    total_count = len(futures)

    for future in as_completed(futures):
        size = future.result()
        downloaded_count += 1
        downloaded_size += size

        percentage = 100 * downloaded_count // total_count
        est_total_size = int(total_count * downloaded_size / downloaded_count)
        duration = (datetime.now() - start_time).seconds
        speed = downloaded_size // duration if duration else 0
        remaining = (total_count - downloaded_count) * duration / downloaded_count

        msg = " ".join([
            "Downloaded VOD {}/{}".format(downloaded_count, total_count),
            "({}%)".format(percentage),
            "<cyan>{}</cyan>".format(format_size(downloaded_size)),
            "of <cyan>~{}</cyan>".format(format_size(est_total_size)),
            "at <cyan>{}/s</cyan>".format(format_size(speed)) if speed > 0 else "",
            "remaining <cyan>~{}</cyan>".format(format_duration(remaining)) if speed > 0 else "",
        ])

        max_msg_size = max(len(msg), max_msg_size)
        print_out("\r" + msg.ljust(max_msg_size), end="")


def download_files(base_url, target_dir, vod_paths, max_workers):
    """
    Downloads a list of VODs defined by a common `base_url` and a list of
    `vod_paths`, returning a dict which maps the paths to the downloaded files.
    """
    urls = [base_url + path for path in vod_paths]
    targets = [os.path.join(target_dir, "{:05d}.ts".format(k)) for k, _ in enumerate(vod_paths)]
    partials = (partial(download_file, url, path) for url, path in zip(urls, targets))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fn) for fn in partials]
        _print_progress(futures)

    return OrderedDict(zip(vod_paths, targets))
