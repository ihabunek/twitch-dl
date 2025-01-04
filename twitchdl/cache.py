import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from httpx import HTTPError

from twitchdl.exceptions import ConsoleError
from twitchdl.http import download_file
from twitchdl.output import print_error, print_status

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


def download_cached_or_none(
    url: str,
    *,
    subdir: Optional[str] = None,
    filename: Optional[str] = None,
) -> Optional[Path]:
    try:
        return download_cached(url, subdir=subdir, filename=filename)
    except HTTPError as ex:
        print_error(ex)
        return None


def get_cache_dir(subdir: Optional[str] = None) -> Path:
    path = _cache_dir_path()
    if subdir:
        path = path / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_subdirs() -> List[Path]:
    subdirs: List[Path] = []
    for item in _cache_dir_path().iterdir():
        if item.is_dir():
            subdirs.append(item)
    return subdirs


def _cache_dir_path() -> Path:
    """Returns the path to the cache directory"""

    # Windows
    if sys.platform == "win32" and "LOCALAPPDATA" in os.environ:
        return Path(os.environ["LOCALAPPDATA"], CACHE_SUBFOLDER)

    # Mac OS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / CACHE_SUBFOLDER

    # Respect XDG_CONFIG_HOME env variable if set
    # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    if "XDG_CACHE_HOME" in os.environ:
        return Path(os.environ["XDG_CACHE_HOME"], CACHE_SUBFOLDER)

    return Path.home() / ".cache" / CACHE_SUBFOLDER


class Cache:
    """Helps keep track of cached files and folders and delete them when finished"""

    def __init__(self, root: Path):
        self.root = root
        self.files: List[Path] = []
        self.dirs: List[Path] = []
        self.mkdir(root)

    def get_path(self, filename: str) -> Path:
        path = self.root / filename
        self.files.append(path)
        return path

    def mkdir(self, path: Path):
        """Create a new directory recursively, save created dirs to self.dirs."""
        try:
            os.mkdir(path)
            self.dirs.append(path)
        except FileNotFoundError:
            if path.parent == path:
                raise
            self.mkdir(path.parent)
            self.mkdir(path)
        except NotADirectoryError:
            raise ConsoleError(f"Failed creating cache dir: {path} is not a directory")

    def delete(self):
        try:
            for file in self.files:
                if file.exists():
                    os.remove(file)
            for dir in reversed(self.dirs):
                os.rmdir(dir)
        except Exception as ex:
            print_error(f"Failed deleting cache: {ex}\nSome files are left over in {self.root}")
