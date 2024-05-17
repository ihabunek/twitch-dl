"""
Twitch API access.
"""

import json
import logging
import time
from typing import Any, Dict, Generator, List, Literal, Mapping, Optional, Tuple, TypedDict, Union

import click
import httpx

from twitchdl import CLIENT_ID
from twitchdl.entities import Data
from twitchdl.exceptions import ConsoleError

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
    videoQualities: List[VideoQuality]
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


class GQLError(click.ClickException):
    def __init__(self, errors: List[str]):
        message = "GraphQL query failed."
        for error in errors:
            message += f"\n* {error}"
        super().__init__(message)


Content = Union[str, bytes]
Headers = Dict[str, str]


def authenticated_post(
    url: str,
    *,
    json: Any = None,
    content: Optional[Content] = None,
    auth_token: Optional[str] = None,
):
    headers = {"Client-ID": CLIENT_ID}
    if auth_token is not None:
        headers["authorization"] = f"OAuth {auth_token}"

    response = request("POST", url, content=content, json=json, headers=headers)
    if response.status_code == 400:
        data = response.json()
        raise ConsoleError(data["message"])

    response.raise_for_status()

    return response


def request(
    method: str,
    url: str,
    json: Any = None,
    content: Optional[Content] = None,
    headers: Optional[Mapping[str, str]] = None,
):
    with httpx.Client() as client:
        request = client.build_request(method, url, json=json, content=content, headers=headers)
        log_request(request)
        start = time.time()
        response = client.send(request)
        duration = time.time() - start
        log_response(response, duration)
        return response


logger = logging.getLogger(__name__)


def log_request(request: httpx.Request):
    logger.debug(f"--> {request.method} {request.url}")
    if request.content:
        logger.debug(f"--> {request.content}")


def log_response(response: httpx.Response, duration: float):
    request = response.request
    duration_ms = int(1000 * duration)
    logger.debug(f"<-- {request.method} {request.url} HTTP {response.status_code} {duration_ms}ms")
    if response.content:
        logger.debug(f"<-- {response.content}")


def gql_post(query: str):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, content=query)
    gql_raise_on_error(response)
    return response.json()


def gql_query(query: str, auth_token: Optional[str] = None):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, json={"query": query}, auth_token=auth_token)
    gql_raise_on_error(response)
    return response.json()


def gql_raise_on_error(response: httpx.Response):
    data = response.json()
    if "errors" in data:
        errors = [e["message"] for e in data["errors"]]
        raise GQLError(errors)


VIDEO_FIELDS = """
    id
    title
    description
    publishedAt
    broadcastType
    lengthSeconds
    game {
        id
        name
    }
    creator {
        login
        displayName
    }
"""


CLIP_FIELDS = """
    id
    slug
    title
    createdAt
    viewCount
    durationSeconds
    url
    videoQualities {
        frameRate
        quality
        sourceURL
    }
    game {
        id
        name
    }
    broadcaster {
        displayName
        login
    }
"""


def get_video(video_id: str) -> Optional[Video]:
    query = f"""
    {{
        video(id: "{video_id}") {{
            {VIDEO_FIELDS}
        }}
    }}
    """

    response = gql_query(query)
    return response["data"]["video"]


def get_clip(slug: str) -> Optional[Clip]:
    query = f"""
    {{
        clip(slug: "{slug}") {{
            {CLIP_FIELDS}
        }}
    }}
    """

    response = gql_query(query)
    return response["data"]["clip"]


def get_clip_access_token(slug: str) -> ClipAccessToken:
    query = f"""
    {{
        "operationName": "VideoAccessToken_Clip",
        "variables": {{
            "slug": "{slug}"
        }},
        "extensions": {{
            "persistedQuery": {{
                "version": 1,
                "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11"
            }}
        }}
    }}
    """

    response = gql_post(query.strip())
    return response["data"]["clip"]


def get_channel_clips(
    channel_id: str,
    period: ClipsPeriod,
    limit: int,
    after: Optional[str] = None,
):
    """
    List channel clips.

    At the time of writing this:
    * filtering by game name returns an error
    * sorting by anything but VIEWS_DESC or TRENDING returns an error
    * sorting by VIEWS_DESC and TRENDING returns the same results
    * there is no totalCount
    """
    query = f"""
    {{
      user(login: "{channel_id}") {{
        clips(first: {limit}, after: "{after or ''}", criteria: {{ period: {period.upper()}, sort: VIEWS_DESC }}) {{
          pageInfo {{
            hasNextPage
            hasPreviousPage
          }}
          edges {{
            cursor
            node {{
              {CLIP_FIELDS}
            }}
          }}
        }}
      }}
    }}
    """

    response = gql_query(query)
    user = response["data"]["user"]
    if not user:
        raise ConsoleError(f"Channel {channel_id} not found")

    return response["data"]["user"]["clips"]


def channel_clips_generator(
    channel_id: str,
    period: ClipsPeriod,
    limit: int,
) -> Generator[Clip, None, None]:
    def _generator(clips: Data, limit: int) -> Generator[Clip, None, None]:
        for clip in clips["edges"]:
            if limit < 1:
                return
            yield clip["node"]
            limit -= 1

        has_next = clips["pageInfo"]["hasNextPage"]
        if limit < 1 or not has_next:
            return

        req_limit = min(limit, 100)
        cursor = clips["edges"][-1]["cursor"]
        clips = get_channel_clips(channel_id, period, req_limit, cursor)
        yield from _generator(clips, limit)

    req_limit = min(limit, 100)
    clips = get_channel_clips(channel_id, period, req_limit)
    return _generator(clips, limit)


def channel_clips_generator_old(channel_id: str, period: ClipsPeriod, limit: int):
    cursor = ""
    while True:
        clips = get_channel_clips(channel_id, period, limit, after=cursor)

        if not clips["edges"]:
            break

        has_next = clips["pageInfo"]["hasNextPage"]
        cursor = clips["edges"][-1]["cursor"] if has_next else None

        yield clips, has_next

        if not cursor:
            break


def get_channel_videos(
    channel_id: str,
    limit: int,
    sort: str,
    type: str = "archive",
    game_ids: Optional[List[str]] = None,
    after: Optional[str] = None,
):
    game_ids = game_ids or []
    game_ids_str = f"[{','.join(game_ids)}]"

    query = f"""
    {{
        user(login: "{channel_id}") {{
            videos(
                first: {limit},
                type: {type.upper()},
                sort: {sort.upper()},
                after: "{after or ''}",
                options: {{
                    gameIDs: {game_ids_str}
                }}
            ) {{
                totalCount
                pageInfo {{
                    hasNextPage
                }}
                edges {{
                    cursor
                    node {{
                        {VIDEO_FIELDS}
                    }}
                }}
            }}
        }}
    }}
    """

    response = gql_query(query)

    if not response["data"]["user"]:
        raise ConsoleError(f"Channel {channel_id} not found")

    return response["data"]["user"]["videos"]


def channel_videos_generator(
    channel_id: str,
    max_videos: int,
    sort: VideosSort,
    type: VideosType,
    game_ids: Optional[List[str]] = None,
) -> Tuple[int, Generator[Video, None, None]]:
    game_ids = game_ids or []

    def _generator(videos: Data, max_videos: int) -> Generator[Video, None, None]:
        for video in videos["edges"]:
            if max_videos < 1:
                return
            yield video["node"]
            max_videos -= 1

        has_next = videos["pageInfo"]["hasNextPage"]
        if max_videos < 1 or not has_next:
            return

        limit = min(max_videos, 100)
        cursor = videos["edges"][-1]["cursor"]
        videos = get_channel_videos(channel_id, limit, sort, type, game_ids, cursor)
        yield from _generator(videos, max_videos)

    limit = min(max_videos, 100)
    videos = get_channel_videos(channel_id, limit, sort, type, game_ids)
    return videos["totalCount"], _generator(videos, max_videos)


def get_access_token(video_id: str, auth_token: Optional[str] = None) -> AccessToken:
    query = f"""
    {{
        videoPlaybackAccessToken(
            id: "{video_id}",
            params: {{
                platform: "web",
                playerBackend: "mediaplayer",
                playerType: "site"
            }}
        ) {{
            signature
            value
        }}
    }}
    """

    try:
        response = gql_query(query, auth_token=auth_token)
        return response["data"]["videoPlaybackAccessToken"]
    except httpx.HTTPStatusError as error:
        # Provide a more useful error message when server returns HTTP 401
        # Unauthorized while using a user-provided auth token.
        if error.response.status_code == 401:
            if auth_token:
                raise ConsoleError("Unauthorized. The provided auth token is not valid.")
            else:
                raise ConsoleError(
                    "Unauthorized. This video may be subscriber-only. See docs:\n"
                    "https://twitch-dl.bezdomni.net/commands/download.html#downloading-subscriber-only-vods"
                )

        raise


def get_playlists(video_id: str, access_token: AccessToken) -> str:
    """
    For a given video return a playlist which contains possible video qualities.
    """
    url = f"https://usher.ttvnw.net/vod/{video_id}"

    response = httpx.get(
        url,
        params={
            "nauth": access_token["value"],
            "nauthsig": access_token["signature"],
            "allow_audio_only": "true",
            "allow_source": "true",
            "player": "twitchweb",
        },
    )
    response.raise_for_status()
    return response.content.decode("utf-8")


def get_game_id(name: str):
    query = f"""
    {{
        game(name: "{name.strip()}") {{
            id
        }}
    }}
    """

    response = gql_query(query)
    game = response["data"]["game"]
    if game:
        return game["id"]


def get_video_chapters(video_id: str) -> List[Chapter]:
    query = {
        "operationName": "VideoPlayer_ChapterSelectButtonVideo",
        "variables": {
            "includePrivate": False,
            "videoID": video_id,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "8d2793384aac3773beab5e59bd5d6f585aedb923d292800119e03d40cd0f9b41",
            }
        },
    }

    response = gql_post(json.dumps(query))
    return list(_chapter_nodes(response["data"]["video"]["moments"]))


def _chapter_nodes(moments: Data) -> Generator[Chapter, None, None]:
    for edge in moments["edges"]:
        node = edge["node"]
        node["game"] = node["details"]["game"]
        del node["details"]
        del node["moments"]
        yield node
