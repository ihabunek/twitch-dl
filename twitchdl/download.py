import os
import requests

from requests.exceptions import RequestException


CHUNK_SIZE = 1024
CONNECT_TIMEOUT = 5


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


def download_file(url, path, retries=3):
    if os.path.exists(path):
        return 0

    for _ in range(retries):
        try:
            return _download(url, path)
        except RequestException as e:
            print("Download failed: {}".format(e))

    raise DownloadFailed(":(")
