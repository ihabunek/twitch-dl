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


def kraken_get(url, params={}, headers={}):
    """
    Add accept header required by kraken API v5.
    see: https://discuss.dev.twitch.tv/t/change-in-access-to-deprecated-kraken-twitch-apis/22241
    """
    headers["Accept"] = "application/vnd.twitchtv.v5+json"
    return authenticated_get(url, params, headers)


def get_user(login):
    """
    https://dev.twitch.tv/docs/api/reference/#get-users
    """
    response = authenticated_get("https://api.twitch.tv/helix/users", {
        "login": login
    })

    users = response.json()["data"]
    return users[0] if users else None


def get_video(video_id):
    """
    https://dev.twitch.tv/docs/v5/reference/videos#get-video
    """
    url = "https://api.twitch.tv/kraken/videos/%d" % video_id

    return kraken_get(url).json()


def get_channel_videos(channel_id, limit, offset, sort):
    """
    https://dev.twitch.tv/docs/v5/reference/channels#get-channel-videos
    """
    url = "https://api.twitch.tv/kraken/channels/{}/videos".format(channel_id)

    return kraken_get(url, {
        "broadcast_type": "archive",
        "limit": limit,
        "offset": offset,
        "sort": sort,
    }).json()


def get_access_token(video_id):
    url = "https://api.twitch.tv/api/vods/%d/access_token" % video_id

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
