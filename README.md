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
python3 twitch-dl.1.10.2.pyz --help
```

b) making it executable and invoking it directly (linux specific):

```
chmod +x twitch-dl.1.10.2.pyz
./twitch-dl.1.10.2.pyz --help
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

List recent streams for a given channel:

```
twitch-dl videos bananasaurus_rex
```

Yields (trimmed):

```
Found 33 videos

221837124
SUPER MARIO ODYSSSEY - Stream #2 / 600,000,000
Bananasaurus_Rex playing Super Mario Odyssey
Published 2018-01-24 @ 12:05:25  Length: 3h 40min

221418913
Dead Space and then SUPER MARIO ODYSSEY PogChamp
Bananasaurus_Rex playing Dead Space
Published 2018-01-23 @ 02:40:58  Length: 6h 2min

220783179
Dead Space | Got my new setup working! rexChamp
Bananasaurus_Rex playing Dead Space
Published 2018-01-21 @ 05:47:03  Length: 5h 7min
```

Use the `--game` option to specify one or more games to show:

```
twitch-dl videos --game "doom eternal" --game "cave story" bananasaurus_rex
```

Download a stream by ID or URL:

```
twitch-dl download 221837124
twitch-dl download https://www.twitch.tv/videos/221837124
```

Specify video quality to download:

```
twitch-dl download -q 720p 221837124
```

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
