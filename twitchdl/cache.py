import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from twitchdl.http import download_file
from twitchdl.output import print_status

CACHE_SUBFOLDER = "twitch-dl"


logger = logging.getLogger(__name__)


def download_cached(
    url: str,
    *,
    subdir: Optional[str] = None,
    filename: Optional[str] = None,
) -> Path:
    target_dir = get_cache_dir(subdir)

    if not filename:
        filename = hashlib.sha256(url.encode()).hexdigest()
    target = target_dir / filename

    if not target.exists():
        print_status(f"Downloading {url}", dim=True)
        download_file(url, target)

    return target


def get_cache_dir(subdir: Optional[str] = None) -> Path:
    path = _cache_dir_path()
    if subdir:
        path = path / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_dir_path() -> Path:
    """Returns the path to the cache directory"""

    # Windows
    if sys.platform == "win32" and "APPDATA" in os.environ:
        return Path(os.environ["APPDATA"], CACHE_SUBFOLDER, "cache")

    # Mac OS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / CACHE_SUBFOLDER

    # Respect XDG_CONFIG_HOME env variable if set
    # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    if "XDG_CACHE_HOME" in os.environ:
        return Path(os.environ["XDG_CACHE_HOME"], CACHE_SUBFOLDER)

    return Path.home() / ".cache" / CACHE_SUBFOLDER
