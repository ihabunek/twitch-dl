from importlib import metadata

try:
    __version__ = metadata.version("twitch-dl")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
