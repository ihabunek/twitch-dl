"""
Twitch API access.
"""

import requests

from twitchdl import CLIENT_ID
from twitchdl.exceptions import ConsoleError


class GQLError(Exception):
    def __init__(self, errors):
        super().__init__("GraphQL query failed")
        self.errors = errors


def authenticated_get(url, params={}, headers={}):
    headers['Client-ID'] = CLIENT_ID

    response = requests.get(url, params, headers=headers)
    if 400 <= response.status_code < 500:
        data = response.json()
        # TODO: this does not look nice in the console since data["message"]
        # can contain a JSON encoded object.
        raise ConsoleError(data["message"])

    response.raise_for_status()

    return response


def authenticated_post(url, data=None, json=None, headers={}):
    headers['Client-ID'] = CLIENT_ID

    response = requests.post(url, data=data, json=json, headers=headers)
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


def gql_query(query):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, json={"query": query}).json()

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


def channel_videos_generator(channel_id, limit, sort, type, game_ids=None):
    cursor = ""
    while True:
        videos = get_channel_videos(
            channel_id, limit, sort, type, game_ids=game_ids, after=cursor)

        if not videos["edges"]:
            break

        has_next = videos["pageInfo"]["hasNextPage"]
        cursor = videos["edges"][-1]["cursor"] if has_next else None

        yield videos, has_next

        if not cursor:
            break


def get_access_token(video_id):
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

    response = gql_query(query)
    return response["data"]["videoPlaybackAccessToken"]


def get_playlists(video_id, access_token):
    """
    For a given video return a playlist which contains possible video qualities.
    """
    url = "http://usher.twitch.tv/vod/{}".format(video_id)

    response = requests.get(url, params={
        "nauth": access_token['value'],
        "nauthsig": access_token['signature'],
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
