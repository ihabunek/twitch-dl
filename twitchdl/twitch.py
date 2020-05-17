"""
Twitch API access.
"""

import requests

from twitchdl import CLIENT_ID
from twitchdl.exceptions import ConsoleError


def authenticated_get(url, params={}, headers={}):
    headers['Client-ID'] = CLIENT_ID

    response = requests.get(url, params, headers=headers)
    if response.status_code == 400:
        data = response.json()
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


def get_video(video_id):
    """
    https://dev.twitch.tv/docs/v5/reference/videos#get-video
    """
    url = "https://api.twitch.tv/kraken/videos/{}".format(video_id)

    return kraken_get(url).json()


def get_clip(slug):
    url = "https://gql.twitch.tv/gql"

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

    payload = {"query": query.format(slug)}
    data = authenticated_post(url, json=payload).json()
    return data["data"]["clip"]


def get_channel_videos(channel_id, limit, sort, type="archive"):
    url = "https://gql.twitch.tv/gql"

    query = """
    {{
      user(login: "{channel_id}") {{
        videos(options: {{ }}, first: {limit}, type: {type}, sort: {sort}, after: "opaqueCursor") {{
          totalCount
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
        "limit": limit,
        "type": type.upper(),
        "sort": sort.upper(),
    })

    response = authenticated_post(url, json={"query": query}).json()
    return response["data"]["user"]["videos"]


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
