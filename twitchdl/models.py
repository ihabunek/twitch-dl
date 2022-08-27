from typing import Any, Dict, List, Optional, Generator
from dataclasses import dataclass


Json = Dict[str, Any]
GameID = str


@dataclass(frozen=True)
class Broadcaster():
    login: str
    display_name: str

    @staticmethod
    def from_json(data: Json) -> "Broadcaster":
        return Broadcaster(data["login"], data["displayName"])


@dataclass(frozen=True)
class VideoQuality():
    frame_rate: int
    quality: str
    source_url: str

    @staticmethod
    def from_json(data: Json) -> "VideoQuality":
        return VideoQuality(data["frameRate"], data["quality"], data["sourceURL"])


@dataclass(frozen=True)
class Game():
    id: str
    name: str

    @staticmethod
    def from_json(data: Json) -> "Game":
        return Game(data["id"], data["name"])


@dataclass(frozen=True)
class Clip():
    id: str
    slug: str
    title: str
    created_at: str
    view_count: int
    duration_seconds: int
    url: str
    game: Optional[Game]
    broadcaster: Broadcaster
    video_qualities: List[VideoQuality]
    raw: Json

    @staticmethod
    def from_json(data: Json) -> "Clip":
        game = Game.from_json(data["game"]) if data["game"] else None
        broadcaster = Broadcaster.from_json(data["broadcaster"])
        video_qualities = [VideoQuality.from_json(q) for q in data["videoQualities"]]

        return Clip(
            data["id"],
            data["slug"],
            data["title"],
            data["createdAt"],
            data["viewCount"],
            data["durationSeconds"],
            data["url"],
            game,
            broadcaster,
            video_qualities,
            data
        )


@dataclass(frozen=True)
class ClipsPage():
    cursor: str
    has_next_page: bool
    has_previous_page: bool
    clips: List[Clip]

    @staticmethod
    def from_json(data: Json) -> "ClipsPage":
        return ClipsPage(
            data["edges"][-1]["cursor"],
            data["pageInfo"]["hasNextPage"],
            data["pageInfo"]["hasPreviousPage"],
            [Clip.from_json(c["node"]) for c in data["edges"]]
        )


ClipGenerator = Generator[Clip, None, None]
