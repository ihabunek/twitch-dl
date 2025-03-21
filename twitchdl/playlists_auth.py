import httpx
from datetime import datetime
import random
from urllib.parse import urlparse
from twitchdl.exceptions import ConsoleError
from twitchdl.twitch import gql_query

def fetch_twitch_data_gql(vod_id):
    query = f'query {{ video(id: "{vod_id}") {{ broadcastType, createdAt, seekPreviewsURL, owner {{ login }} }} }}'
    return gql_query(query)

def create_serving_id():
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    return ''.join(random.choice(chars) for _ in range(32))

def is_valid_quality(url):
    with httpx.Client() as client:
        response = client.get(url)
        if response.status_code == 200:
            data = response.text
            if ".ts" in data:
                return {"codec": "avc1.4D001E"}
            elif ".mp4" in data:
                mp4_url = url.replace("index-dvr.m3u8", "init-0.mp4")
                mp4_response = client.get(mp4_url)
                if mp4_response.status_code == 200:
                    content = mp4_response.text
                    return {"codec": "hev1.1.6.L93.B0" if "hev1" in content else "avc1.4D001E"}
                return {"codec": "hev1.1.6.L93.B0"}
    return None

def fetch_auth_playlist(vod_id):
    data = fetch_twitch_data_gql(vod_id)

    if not data:
        raise ConsoleError('Invalid vodId')

    vod_data = data['data']['video']
    channel_data = vod_data['owner']

    resolutions = {
        "audio_only": {"res": "audio_only"},
        "160p30": {"res": "284x160", "fps": 30},
        "360p30": {"res": "640x360", "fps": 30},
        "480p30": {"res": "854x480", "fps": 30},
        "720p60": {"res": "1280x720", "fps": 60},
        "1080p60": {"res": "1920x1080", "fps": 60},
        "chunked": {"res": "1920x1080", "fps": 60}
    }

    sorted_keys = sorted(resolutions.keys(), reverse=True)
    ordered_resolutions = {key: resolutions[key] for key in sorted_keys}

    current_url = urlparse(vod_data['seekPreviewsURL'])
    domain = current_url.hostname
    paths = current_url.path.split('/')
    vod_special_id = paths[paths.index(next(p for p in paths if "storyboards" in p)) - 1]

    fake_playlist = f'''#EXTM3U
#EXT-X-TWITCH-INFO:ORIGIN="s3",B="false",REGION="EU",USER-IP="127.0.0.1",SERVING-ID="{create_serving_id()}",CLUSTER="cloudfront_vod",USER-COUNTRY="BE",MANIFEST-CLUSTER="cloudfront_vod"'''

    now = datetime.strptime("2023-02-10", "%Y-%m-%d")
    created = datetime.strptime(vod_data['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
    time_difference = (now - created).total_seconds()
    days_difference = time_difference / (3600 * 24)

    broadcast_type = vod_data['broadcastType'].lower()
    start_quality = 8534030

    for res_key, res_value in ordered_resolutions.items():
        url = None

        if broadcast_type == "highlight":
            url = f"https://{domain}/{vod_special_id}/{res_key}/highlight-{vod_id}.m3u8"
        elif broadcast_type == "upload" and days_difference > 7:
            url = f"https://{domain}/{channel_data['login']}/{vod_id}/{vod_special_id}/{res_key}/index-dvr.m3u8"
        else:
            url = f"https://{domain}/{vod_special_id}/{res_key}/index-dvr.m3u8"

        if not url:
            continue

        result = is_valid_quality(url)
        if result:
            quality = res_value['res'].split('x')[1] + "p" if res_key == "chunked" else res_key
            enabled = "YES" if res_key == "chunked" else "NO"
            fps = res_value.get('fps', 0)

            if quality == 'audio_only':
                fake_playlist += f'''
#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="{quality}",NAME="{quality}",AUTOSELECT={enabled},DEFAULT={enabled}
#EXT-X-STREAM-INF:BANDWIDTH={start_quality},CODECS="{result['codec']},mp4a.40.2",VIDEO="{quality}"
{url}'''
            else:
                name = quality if fps != 30 else quality[:-2]
                fake_playlist += f'''
#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="{quality}",NAME="{name}",AUTOSELECT={enabled},DEFAULT={enabled}
#EXT-X-STREAM-INF:BANDWIDTH={start_quality},CODECS="{result['codec']},mp4a.40.2",RESOLUTION={res_value['res']},VIDEO="{quality}",FRAME-RATE={fps}
{url}'''

            start_quality -= 100

    return fake_playlist
