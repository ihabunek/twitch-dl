from dataclasses import dataclass


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
