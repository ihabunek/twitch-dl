from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class User:
    login: str
    display_name: str

@dataclass
class Game:
    name: str

@dataclass
class Video:
    id: str
    title: str
    description: str
    published_at: datetime
    broadcast_type: str
    length_seconds: int
    game: Game
    creator: User


@dataclass
class AccessToken:
    signature: str
    value: str
