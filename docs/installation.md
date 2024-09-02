# Installation

twitch-dl requires **Python 3.8** or later.

## Prerequisite: FFmpeg

FFmpeg is used to join vods into a single video file.

To check if FFmpeg is available, run:

```
ffmpeg -version
```

The version number and some info should be printed.

```
ffmpeg version 4.3.2-0+deb11u2 Copyright (c) 2000-2021 the FFmpeg developers
built with gcc 10 (Debian 10.2.1-6)
```

To install FFmpeg see [FFmpeg documentation](https://ffmpeg.org/download.html).

## Option 1: Download standalone archive

Go to the [latest release](https://github.com/ihabunek/twitch-dl/releases/latest)
and download the `twitch-dl.<version>.pyz` archive.

Run the archive by either:

a) passing it to python:

```
python3 twitch-dl.1.13.0.pyz --help
```

b) making it executable and invoking it directly (linux specific):

```
chmod +x twitch-dl.1.13.0.pyz
./twitch-dl.1.13.0.pyz --help
```

Feel free to rename the archive to something more managable, like `twitch-dl`.

To upgrade to a newer version, repeat the process with the newer release.

## Option 2: Install from PYPI using pipx

**pipx** is a tool which installs python apps into isolated environments, which
prevents all kinds of problems later so it's the suggested way to install
twitch-dl from PYPI.

Install pipx as described in
[pipx install docs](https://pipxproject.github.io/pipx/installation/).

Install twitch-dl:

```
pipx install twitch-dl
```

Install with the optional dependencies for rendering chat:

```
pipx install "twitch-dl[chat]"
```

Check installation worked:

```
twitch-dl --version
```

If twitch-dl executable is not found, check that the pipx binary location (by
default `~/.local/bin`) is in your PATH.

To upgrade twitch-dl to the latest version:

```
pipx upgrade twitch-dl
```
