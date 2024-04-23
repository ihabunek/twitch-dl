from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class DownloadOptions:
    auth_token: Optional[str]
    chapter: Optional[int]
    concat: bool
    dry_run: bool
    end: Optional[int]
    format: str
    keep: bool
    no_join: bool
    overwrite: bool
    output: str
    quality: Optional[str]
    rate_limit: Optional[int]
    start: Optional[int]
    max_workers: int


# Type for annotating decoded JSON
# TODO: make data classes for common structs
Data = Mapping[str, Any]
