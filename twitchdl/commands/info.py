import m3u8

from twitchdl import utils, twitch
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_video, print_clip, print_json, print_out, print_log


def info(args):
    video_id = utils.parse_video_identifier(args.video)
    if video_id:
        print_log("Fetching video...")
        video = twitch.get_video(video_id)

        if not video:
            raise ConsoleError("Video {} not found".format(video_id))

        print_log("Fetching access token...")
        access_token = twitch.get_access_token(video_id)

        print_log("Fetching playlists...")
        playlists = twitch.get_playlists(video_id, access_token)

        if video:
            if args.json:
                return video_json(video, playlists)
            else:
                video_info(video, playlists)
            return

    clip_slug = utils.parse_clip_identifier(args.video)
    if clip_slug:
        print_log("Fetching clip...")
        clip = twitch.get_clip(clip_slug)
        if not clip:
            raise ConsoleError("Clip {} not found".format(clip_slug))

        if args.json:
            print_json(clip)
            return clip
        else:
            clip_info(clip)
        return

    raise ConsoleError("Invalid input: {}".format(args.video))


def video_info(video, playlists):
    print_out()
    print_video(video)

    print_out()
    print_out("Playlists:")
    for p in m3u8.loads(playlists).playlists:
        print_out("<b>{}</b> {}".format(p.stream_info.video, p.uri))


def video_json(video, playlists):
    playlists = m3u8.loads(playlists).playlists

    video["playlists"] = [
        {
            "bandwidth": p.stream_info.bandwidth,
            "resolution": p.stream_info.resolution,
            "codecs": p.stream_info.codecs,
            "video": p.stream_info.video,
            "uri": p.uri
        } for p in playlists
    ]

    print_json(video)
    return video


def clip_info(clip):
    print_out()
    print_clip(clip)
    print_out()
    print_out("Download links:")

    for q in clip["videoQualities"]:
        print_out("<b>{quality}p{frameRate}</b> {sourceURL}".format(**q))
