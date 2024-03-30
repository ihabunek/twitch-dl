from dataclasses import dataclass
from typing import Any


@dataclass
class DownloadOptions:
    auth_token: str | None
    chapter: int | None
    concat: bool
    dry_run: bool
    end: int | None
    format: str
    keep: bool
    no_join: bool
    overwrite: bool
    output: str
    quality: str | None
    rate_limit: str | None
    start: int | None
    max_workers: int


# Type for annotating decoded JSON
# TODO: make data classes for common structs
Data = dict[str, Any]
