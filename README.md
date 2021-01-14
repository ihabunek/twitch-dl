Twitch Downloader
=================

CLI tool for downloading videos from twitch.tv

Inspired by [youtube-dl](https://youtube-dl.org/) but improves upon it by using
multiple concurrent connections to make the download faster.

Resources
---------

* Homepage: https://github.com/ihabunek/twitch-dl
* Issues: https://github.com/ihabunek/twitch-dl/issues
* Python package: https://pypi.org/project/twitch-dl/

Requirements
------------

* Python 3.5+
* [ffmpeg](https://ffmpeg.org/download.html), installed and on the system path

Installation
------------

### Download standalone archive

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

### From PYPI using pipx

**pipx** is a tool which installs python apps into isolated environments, which
prevents all kinds of problems later so it's the suggested way to install
twitch-dl from PYPI.

Install pipx as described in
[pipx install docs](https://pipxproject.github.io/pipx/installation/).

Install twitch-dl:

```
pipx install twitch-dl
```

Check installation worked:

```
twitch-dl --help
```

If twitch-dl executable is not found, check that the pipx binary location (by
default `~/.local/bin`) is in your PATH.

To upgrade twitch-dl to the latest version:

```
pipx install twitch-dl
```

Usage
-----

This section does an overview of available features.

To see a list of available commands run:

```
twitch-dl --help
```

And to see description and all arguments for a given command run:

```
twitch-dl <command> --help
```

### Print clip or video info

Videos can be referenced by URL or ID:

```
twitch-dl info 863849735
twitch-dl info https://www.twitch.tv/videos/863849735
```

Clips by slug or ID:

```
twitch-dl info BusyBlushingCattleItsBoshyTime
twitch-dl info https://www.twitch.tv/bananasaurus_rex/clip/BusyBlushingCattleItsBoshyTime
```

Shows info about the video or clip as well as download URLs for clips and
playlist URLs for videos.

### Listing videos

List recent streams for a given channel:

```
twitch-dl videos bananasaurus_rex
```

Use the `--game` option to specify one or more games to show:

```
twitch-dl videos --game "doom eternal" --game "cave story" bananasaurus_rex
```

### Downloading videos

Download a video by ID or URL:

```
twitch-dl download 221837124
twitch-dl download https://www.twitch.tv/videos/221837124
```

Specify video quality to download:

```
twitch-dl download -q 720p 221837124
```

Setting quality to `source` will download the best available quality:

```
twitch-dl download -q source 221837124
```

### Listing clips

List clips for the given period:

```
twitch-dl clips bananasaurus_rex --period last_week
```

Supported periods are: `last_day`, `last_week`, `last_month`, `all_time`.

For listing a large number of clips, it's nice to page them:

```
twitch-dl clips bananasaurus_rex --period all_time --limit 10 --pager
```

This will show 10 clips at a time and ask to continue.

### Downloading clips

Download a clip by slug or URL:

```
twitch-dl download VenomousTameWormHumbleLife
twitch-dl download https://www.twitch.tv/bananasaurus_rex/clip/VenomousTameWormHumbleLife
```

Specify clip quality to download:

```
twitch-dl download -q 720 VenomousTameWormHumbleLife
```

Note that twitch names for clip qualities have no trailing "p".

### Batch downloading clips

It's possible to download all clips for a given period:

```
twitch-dl clips bananasaurus_rex --period last_week --download
```

Clips are downloaded in source quality.

A note about clips
------------------

Currently it doesn't seem to be possible to get a list of clips ordered by time
of creation, only by view count. Clips with the same view count seem to be
returned in random order. This can break paging resulting in duplicate clips
listed or clips missed.

When batch downloading a large number of clips (over 100), it's possible that
some will be missed.

Temporary files
---------------

By default, twitch-dl will download VODs to your systems temp dir (e.g. `/tmp/`
on Linux). To change the location where the files are downloaded you can set
the `TMP` environment variable, e.g.

```
TMP=/my/tmp/path/ twitch-dl download 221837124
```

Man page
--------

Building the man page for twitch-dl requires scdoc.

The source is in ``twitch-dl.1.scd``, and you can build it by running:

```
make man
```

License
-------

Copyright 2018-2020 Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html
