from dataclasses import dataclass
from typing import Any, List, Literal, Mapping, Optional, TypedDict


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


ClipsPeriod = Literal["last_day", "last_week", "last_month", "all_time"]
VideosSort = Literal["views", "time"]
VideosType = Literal["archive", "highlight", "upload"]


class AccessToken(TypedDict):
    signature: str
    value: str


class User(TypedDict):
    login: str
    displayName: str


class Game(TypedDict):
    id: str
    name: str


class VideoQuality(TypedDict):
    frameRate: str
    quality: str
    sourceURL: str


class ClipAccessToken(TypedDict):
    id: str
    playbackAccessToken: AccessToken
    videoQualities: List[VideoQuality]


class Clip(TypedDict):
    id: str
    slug: str
    title: str
    createdAt: str
    viewCount: int
    durationSeconds: int
    url: str
    videoQualities: Optional[List[VideoQuality]]
    game: Game
    broadcaster: User


class Video(TypedDict):
    id: str
    title: str
    description: str
    publishedAt: str
    broadcastType: str
    lengthSeconds: int
    game: Game
    creator: User


class Chapter(TypedDict):
    id: str
    durationMilliseconds: int
    positionMilliseconds: int
    type: str
    description: str
    subDescription: str
    thumbnailURL: str
    game: Game


# Type for annotating decoded JSON
# TODO: make data classes for common structs
Data = Mapping[str, Any]
