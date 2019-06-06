import requests

from twitchdl import CLIENT_ID
from twitchdl.parse import parse_playlists, parse_playlist


def authenticated_get(url, params={}):
    headers = {'Client-ID': CLIENT_ID}

    response = requests.get(url, params, headers=headers)
    response.raise_for_status()

    return response


def get_video(video_id):
    """
    https://dev.twitch.tv/docs/v5/reference/videos#get-video
    """
    url = "https://api.twitch.tv/kraken/videos/%d" % video_id

    return authenticated_get(url).json()


def get_channel_videos(channel_name, limit=20):
    """
    https://dev.twitch.tv/docs/v5/reference/channels#get-channel-videos
    """
    url = "https://api.twitch.tv/kraken/channels/%s/videos" % channel_name

    return authenticated_get(url, {
        "broadcast_type": "archive",
        "limit": limit,
    }).json()


def get_access_token(video_id):
    url = "https://api.twitch.tv/api/vods/%d/access_token" % video_id

    return authenticated_get(url).json()


def get_playlists(video_id, access_token):
    url = "http://usher.twitch.tv/vod/{}".format(video_id)

    response = requests.get(url, params={
        "nauth": access_token['token'],
        "nauthsig": access_token['sig'],
        "allow_source": "true",
        "player": "twitchweb",
    })
    response.raise_for_status()

    data = response.content.decode('utf-8')

    return parse_playlists(data)


def get_playlist_urls(url, start, end):
    response = requests.get(url)
    response.raise_for_status()

    data = response.content.decode('utf-8')
    return parse_playlist(url, data, start, end)
