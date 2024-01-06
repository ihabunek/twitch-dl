"""
Twitch API access.
"""

import httpx
import json

from typing import Dict
from twitchdl import CLIENT_ID
from twitchdl.exceptions import ConsoleError


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


VIDEO_FIELDS = """
    id
    title
    publishedAt
    broadcastType
    lengthSeconds
    game {
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


def get_video(video_id):
    query = """
    {{
        video(id: "{video_id}") {{
            {fields}
        }}
    }}
    """

    query = query.format(video_id=video_id, fields=VIDEO_FIELDS)

    response = gql_query(query)
    return response["data"]["video"]


def get_clip(slug):
    query = """
    {{
        clip(slug: "{}") {{
            {fields}
        }}
    }}
    """

    response = gql_query(query.format(slug, fields=CLIP_FIELDS))
    return response["data"]["clip"]


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


def get_channel_clips(channel_id, period, limit, after=None):
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

    return response["data"]["user"]["clips"]


def channel_clips_generator(channel_id, period, limit):
    def _generator(clips, limit):
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


def channel_clips_generator_old(channel_id, period, limit):
    cursor = ""
    while True:
        clips = get_channel_clips(
            channel_id, period, limit, after=cursor)

        if not clips["edges"]:
            break

        has_next = clips["pageInfo"]["hasNextPage"]
        cursor = clips["edges"][-1]["cursor"] if has_next else None

        yield clips, has_next

        if not cursor:
            break


def get_channel_videos(channel_id, limit, sort, type="archive", game_ids=[], after=None):
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

    return response["data"]["user"]["videos"]


def channel_videos_generator(channel_id, max_videos, sort, type, game_ids=[]):
    def _generator(videos, max_videos):
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
    url = "https://usher.ttvnw.net/vod/{}".format(video_id)

    response = httpx.get(url, params={
        "nauth": access_token['value'],
        "nauthsig": access_token['signature'],
        "allow_audio_only": "true",
        "allow_source": "true",
        "player": "twitchweb",
    })
    response.raise_for_status()
    return response.content.decode('utf-8')


def get_game_id(name):
    query = """
    {{
        game(name: "{}") {{
            id
        }}
    }}
    """

    response = gql_query(query.format(name.strip()))
    game = response["data"]["game"]
    if game:
        return game["id"]


def get_video_chapters(video_id):
    query = {
        "operationName": "VideoPlayer_ChapterSelectButtonVideo",
        "variables":
        {
            "includePrivate": False,
            "videoID": video_id
        },
        "extensions":
        {
            "persistedQuery":
            {
                "version": 1,
                "sha256Hash": "8d2793384aac3773beab5e59bd5d6f585aedb923d292800119e03d40cd0f9b41"
            }
        }
    }

    response = gql_post(json.dumps(query))
    return list(_chapter_nodes(response["data"]["video"]["moments"]))


def _chapter_nodes(collection):
    for edge in collection["edges"]:
        node = edge["node"]
        del node["moments"]
        yield node
