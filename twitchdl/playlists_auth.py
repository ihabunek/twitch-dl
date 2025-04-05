from typing import List
import httpx
from datetime import datetime
from urllib.parse import urlparse
from twitchdl.exceptions import ConsoleError
from twitchdl.playlists import Playlist
from twitchdl.twitch import gql_query


def fetch_twitch_data_gql(vod_id):
    query = f'query {{ video(id: "{vod_id}") {{ broadcastType, createdAt, seekPreviewsURL, owner {{ login }} }} }}'
    return gql_query(query)


def is_valid_quality(url: str):
    with httpx.Client() as client:
        response = client.get(url)
        return response.is_success


def fetch_auth_playlist(vod_id) -> List[Playlist]:
    data = fetch_twitch_data_gql(vod_id)

    if not data:
        raise ConsoleError('Invalid vodId')

    vod_data = data['data']['video']
    channel_data = vod_data['owner']

    resolutions = [
        {"name": "1080p60", "group_id": "chunked", "resolution": "1920x1080", "is_source": True},
        {"name": "1080p60", "group_id": "1080p60", "resolution": "1920x1080", "is_source": True},
        {"name": "720p60", "group_id": "720p60", "resolution": "1280x720", "is_source": False},
        {"name": "480p", "group_id": "480p30", "resolution": "852x480", "is_source": False},
        {"name": "360p", "group_id": "360p30", "resolution": "640x360", "is_source": False},
        {"name": "160p", "group_id": "160p30", "resolution": "284x160", "is_source": False},
        {"name": "Audio Only", "group_id": "audio_only", "resolution": None, "is_source": False},
    ]

    current_url = urlparse(vod_data['seekPreviewsURL'])
    domain = current_url.hostname
    paths = current_url.path.split('/')
    vod_special_id = paths[paths.index(next(p for p in paths if "storyboards" in p)) - 1]

    now = datetime.strptime("2023-02-10", "%Y-%m-%d")
    created = datetime.strptime(vod_data['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
    time_difference = (now - created).total_seconds()
    days_difference = time_difference / (3600 * 24)

    broadcast_type = vod_data['broadcastType'].lower()

    playlists: List[Playlist] = []
    for resolution in resolutions:
        group_id = resolution["group_id"]
        url = None

        if broadcast_type == "highlight":
            url = f"https://{domain}/{vod_special_id}/{group_id}/highlight-{vod_id}.m3u8"
        elif broadcast_type == "upload" and days_difference > 7:
            url = f"https://{domain}/{channel_data['login']}/{vod_id}/{vod_special_id}/{group_id}/index-dvr.m3u8"
        else:
            url = f"https://{domain}/{vod_special_id}/{group_id}/index-dvr.m3u8"

        if not url:
            continue

        if is_valid_quality(url):
            playlist = Playlist(
                group_id=group_id,
                is_source=resolution["is_source"],
                name=resolution["name"],
                resolution=resolution["resolution"],
                url=url
            )
            playlists.append(playlist)

    return playlists
