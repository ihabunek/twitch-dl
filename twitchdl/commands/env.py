import platform
import sys
import twitchdl


def env(args):
    print("twitch-dl", twitchdl.__version__)
    print("Platform:", platform.platform())
    print("Python", sys.version)
