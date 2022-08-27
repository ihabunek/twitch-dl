"""
Twitch API access.
"""

import httpx

from twitchdl import CLIENT_ID
from twitchdl.exceptions import ConsoleError
from twitchdl.models import Clip, ClipsPage, ClipGenerator, Game, Video, VideoGenerator, VideosPage
from typing import Dict, Optional, Tuple


class GQLError(Exception):
    def __init__(self, errors):
        super().__init__("GraphQL query failed")
        self.errors = errors


def authenticated_post(url, data=None, json=None, headers={}):
    headers['Client-ID'] = CLIENT_ID

    response = httpx.post(url, data=data, json=json, headers=headers)
    if response.status_code == 400:
        data = response.json()
        raise ConsoleError(data["message"])

    response.raise_for_status()

    return response


def gql_post(query):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, data=query).json()

    if "errors" in response:
        raise GQLError(response["errors"])

    return response


def gql_query(query: str, headers: Dict[str, str] = {}):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, json={"query": query}, headers=headers).json()

    if "errors" in response:
        raise GQLError(response["errors"])

    return response


GAME_FIELDS = """
    id
    name
    description
"""

VIDEO_FIELDS = f"""
    id
    title
    publishedAt
    broadcastType
    lengthSeconds
    game {{
        {GAME_FIELDS}
    }}
    creator {{
        login
        displayName
    }}
"""


CLIP_FIELDS = f"""
    id
    slug
    title
    createdAt
    viewCount
    durationSeconds
    url
    videoQualities {{
        frameRate
        quality
        sourceURL
    }}
    game {{
        {GAME_FIELDS}
    }}
    broadcaster {{
        login
        displayName
    }}
"""


def get_video(video_id: str) -> Optional[Video]:
    query = """
    {{
        video(id: "{video_id}") {{
            {fields}
        }}
    }}
    """

    query = query.format(video_id=video_id, fields=VIDEO_FIELDS)

    response = gql_query(query)
    if response["data"]["video"]:
        return Video.from_json(response["data"]["video"])


def get_clip(slug: str) -> Clip:
    query = """
    {{
        clip(slug: "{}") {{
            {fields}
        }}
    }}
    """

    response = gql_query(query.format(slug, fields=CLIP_FIELDS))
    return Clip.from_json(response["data"]["clip"])


def get_clip_access_token(slug):
    query = """
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

    response = gql_post(query.format(slug=slug).strip())
    return response["data"]["clip"]


def get_channel_clips(channel_id, period, limit, after=None) -> ClipsPage:
    """
    List channel clips.

    At the time of writing this:
    * filtering by game name returns an error
    * sorting by anything but VIEWS_DESC or TRENDING returns an error
    * sorting by VIEWS_DESC and TRENDING returns the same results
    * there is no totalCount
    """
    query = """
    {{
      user(login: "{channel_id}") {{
        clips(first: {limit}, after: "{after}", criteria: {{ period: {period}, sort: VIEWS_DESC }}) {{
          pageInfo {{
            hasNextPage
            hasPreviousPage
          }}
          edges {{
            cursor
            node {{
              {fields}
            }}
          }}
        }}
      }}
    }}
    """

    query = query.format(
        channel_id=channel_id,
        after=after if after else "",
        limit=limit,
        period=period.upper(),
        fields=CLIP_FIELDS
    )

    response = gql_query(query)
    user = response["data"]["user"]
    if not user:
        raise ConsoleError("Channel {} not found".format(channel_id))

    return ClipsPage.from_json(response["data"]["user"]["clips"])


def channel_clips_generator(channel_id: str, period, limit: int) -> ClipGenerator:
    def _generator(page: ClipsPage, limit: int):
        for clip in page.clips:
            if limit < 1:
                return
            yield clip
            limit -= 1

        if limit < 1 or not page.has_next_page:
            return

        req_limit = min(limit, 100)
        next_page = get_channel_clips(channel_id, period, req_limit, page.cursor)
        yield from _generator(next_page, limit)

    req_limit = min(limit, 100)
    page = get_channel_clips(channel_id, period, req_limit)
    return _generator(page, limit)


def channel_clips_generator_old(channel_id, period, limit):
    cursor = ""
    while True:
        page = get_channel_clips(channel_id, period, limit, after=cursor)

        if not page.clips:
            break

        has_next = page.has_next_page
        cursor = page.cursor if has_next else None

        yield page.clips, has_next

        if not cursor:
            break


def get_channel_videos(channel_id, limit, sort, type="archive", game_ids=[], after=None) -> VideosPage:
    query = """
    {{
        user(login: "{channel_id}") {{
            videos(
                first: {limit},
                type: {type},
                sort: {sort},
                after: "{after}",
                options: {{
                    gameIDs: {game_ids}
                }}
            ) {{
                totalCount
                pageInfo {{
                    hasNextPage
                }}
                edges {{
                    cursor
                    node {{
                        {fields}
                    }}
                }}
            }}
        }}
    }}
    """

    query = query.format(
        channel_id=channel_id,
        game_ids=game_ids,
        after=after if after else "",
        limit=limit,
        sort=sort.upper(),
        type=type.upper(),
        fields=VIDEO_FIELDS
    )

    response = gql_query(query)

    if not response["data"]["user"]:
        raise ConsoleError("Channel {} not found".format(channel_id))

    return VideosPage.from_json(response["data"]["user"]["videos"])


def channel_videos_generator(channel_id, max_videos, sort, type, game_ids=None) -> Tuple[int, VideoGenerator]:
    def _generator(page, max_videos):
        for video in page.videos:
            if max_videos < 1:
                return
            yield video
            max_videos -= 1

        if max_videos < 1 or not page.has_next_page:
            return

        limit = min(max_videos, 100)
        videos = get_channel_videos(channel_id, limit, sort, type, game_ids, page.cursor)
        yield from _generator(videos, max_videos)

    limit = min(max_videos, 100)
    page = get_channel_videos(channel_id, limit, sort, type, game_ids)
    return page.total_count, _generator(page, max_videos)


def get_access_token(video_id, auth_token=None):
    query = """
    {{
        videoPlaybackAccessToken(
            id: {video_id},
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

    query = query.format(video_id=video_id)

    headers = {}
    if auth_token is not None:
        headers['authorization'] = f'OAuth {auth_token}'

    try:
        response = gql_query(query, headers=headers)
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


def get_playlists(video_id, access_token):
    """
    For a given video return a playlist which contains possible video qualities.
    """
    url = "http://usher.twitch.tv/vod/{}".format(video_id)

    response = httpx.get(url, params={
        "nauth": access_token['value'],
        "nauthsig": access_token['signature'],
        "allow_audio_only": "true",
        "allow_source": "true",
        "player": "twitchweb",
    })
    response.raise_for_status()
    return response.content.decode('utf-8')


def find_game(name: str) -> Optional[Game]:
    query = f"""
    {{
        game(name: "{name.strip()}") {{
            {GAME_FIELDS}
        }}
    }}
    """

    response = gql_query(query)
    if response["data"]["game"]:
        return Game.from_json(response["data"]["game"])
