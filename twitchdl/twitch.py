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


def kraken_get(url, params={}, headers={}):
    """
    Add accept header required by kraken API v5.
    see: https://discuss.dev.twitch.tv/t/change-in-access-to-deprecated-kraken-twitch-apis/22241
    """
    headers["Accept"] = "application/vnd.twitchtv.v5+json"
    return authenticated_get(url, params, headers)


def gql_query(query):
    url = "https://gql.twitch.tv/gql"
    response = authenticated_post(url, json={"query": query}).json()

    if "errors" in response:
        raise GQLError(response["errors"])

    return response


def get_video(video_id):
    """
    https://dev.twitch.tv/docs/v5/reference/videos#get-video
    """
    url = "https://api.twitch.tv/kraken/videos/{}".format(video_id)

    return kraken_get(url).json()


def get_clip(slug):
    query = """
    {{
        clip(slug: "{}") {{
            title
            durationSeconds
            game {{
                name
            }}
            broadcaster {{
                login
                displayName
            }}
            videoQualities {{
                frameRate
                quality
                sourceURL
            }}
        }}
    }}
    """

    response = gql_query(query.format(slug))
    return response["data"]["clip"]


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
                        id
                        title
                        publishedAt
                        broadcastType
                        lengthSeconds
                        game {{
                            name
                        }}
                        creator {{
                            channel {{
                                displayName
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """

    query = query.format(**{
        "channel_id": channel_id,
        "game_ids": game_ids,
        "after": after,
        "limit": limit,
        "sort": sort.upper(),
        "type": type.upper(),
    })

    response = gql_query(query)
    return response["data"]["user"]["videos"]


def channel_videos_generator(channel_id, limit, sort, type, game_ids=None):
    cursor = None
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
    url = "https://api.twitch.tv/api/vods/{}/access_token".format(video_id)

    return authenticated_get(url).json()


def get_playlists(video_id, access_token):
    """
    For a given video return a playlist which contains possible video qualities.
    """
    url = "http://usher.twitch.tv/vod/{}".format(video_id)

    response = requests.get(url, params={
        "nauth": access_token['token'],
        "nauthsig": access_token['sig'],
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
