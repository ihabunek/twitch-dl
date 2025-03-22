"""
Twitch API access.
"""

import logging
import random
import time
from typing import Any, Dict, Generator, List, Mapping, Optional, Tuple, Union

import click
import httpx

from twitchdl import CLIENT_ID
from twitchdl.entities import (
    AccessToken,
    Chapter,
    Clip,
    ClipAccessToken,
    ClipsPeriod,
    Data,
    Page,
    Video,
    VideoComments,
    VideosSort,
    VideosType,
)
from twitchdl.exceptions import ConsoleError, PlaylistAuthRequireError
from twitchdl.utils import format_size, remove_null_values


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
    logger.info(f"--> {request.method} {request.url}")
    if request.content:
        logger.debug(f"--> {request.content}")


def log_response(response: httpx.Response, duration_seconds: float):
    request = response.request
    duration = f"{int(1000 * duration_seconds)}ms"
    size = format_size(len(response.content))
    logger.info(f"<-- {request.method} {request.url} HTTP {response.status_code} {duration} {size}")
    if response.content:
        logger.debug(f"<-- {response.content}")


def gql_persisted_query(query: Data):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, json=query)
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
    recordedAt
    publishedAt
    updatedAt
    broadcastType
    lengthSeconds
    status
    viewCount
    game {
        id
        name
    }
    owner {
        id
        login
        displayName
    }
    creator {
        id
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
    query = {
        "operationName": "VideoAccessToken_Clip",
        "variables": {"slug": slug},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11",
            }
        },
    }

    response = gql_persisted_query(query)
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
        clips(
          first: {limit},
          after: "{after or ''}",
          criteria: {{
            period: {period.upper()},
            sort: VIEWS_DESC
          }}
        )
        {{
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


def channel_clips_page_generator(
    channel_id: str,
    period: ClipsPeriod,
    page_size: int = 40,
) -> Generator[Page[Clip], None, None]:
    cursor = None
    has_next = True
    page_no = 1

    while has_next:
        response = get_channel_clips(channel_id, period, page_size, cursor)
        has_next = response["pageInfo"]["hasNextPage"]
        clips = [edge["node"] for edge in response["edges"]]
        yield Page(page_no, has_next, clips)
        cursor = response["edges"][-1]["cursor"] if response["edges"] else None
        page_no += 1


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


UNAUTHORIZED_ERROR = (
    "Unauthorized. This video may be subscriber-only. See docs:\n" +
    "https://twitch-dl.bezdomni.net/commands/download.html#downloading-subscriber-only-vods"
)


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
                raise PlaylistAuthRequireError(UNAUTHORIZED_ERROR)

        raise


def get_playlists(video_id: str, access_token: AccessToken) -> str:
    """
    For a given video return a playlist which contains possible video qualities.
    """
    url = f"https://usher.ttvnw.net/vod/{video_id}"

    params = {
        "nauth": access_token["value"],
        "nauthsig": access_token["signature"],
        "allow_audio_only": "true",
        "allow_source": "true",
        "player": "twitchweb",
        "platform": "web",
        "supported_codecs": "av1,h265,h264",
        "p": random.randint(1000000, 10000000),
    }

    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        return response.content.decode("utf-8")
    except httpx.HTTPStatusError as ex:
        if ex.response.status_code == 403:
            raise PlaylistAuthRequireError(UNAUTHORIZED_ERROR)
        raise


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

    response = gql_persisted_query(query)
    return list(_chapter_nodes(response["data"]["video"]["moments"]))


def _chapter_nodes(moments: Data) -> Generator[Chapter, None, None]:
    for edge in moments["edges"]:
        node = edge["node"]
        node["game"] = node["details"]["game"]
        del node["details"]
        del node["moments"]
        yield node


def get_comments(
    video_id: str,
    *,
    cursor: Optional[str] = None,
    offset_seconds: Optional[int] = None,
):
    variables = remove_null_values(
        {
            "videoID": video_id,
            "cursor": cursor,
            "contentOffsetSeconds": offset_seconds,
        }
    )

    query = {
        "operationName": "VideoCommentsByOffsetOrCursor",
        "variables": variables,
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a",
            }
        },
    }

    response = gql_persisted_query(query)
    return response["data"]["video"]


def get_video_comments(video_id: str) -> VideoComments:
    query = {
        "operationName": "VideoComments",
        "variables": {
            "videoID": video_id,
            "hasVideoID": True,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "be06407e8d7cda72f2ee086ebb11abb6b062a7deb8985738e648090904d2f0eb",
            }
        },
    }

    response = gql_persisted_query(query)
    return response["data"]
