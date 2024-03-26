Twitch Downloader
=================

CLI tool for downloading videos from twitch.tv

Inspired by [youtube-dl](https://youtube-dl.org/) but improves upon it by using
multiple concurrent connections to make the download faster.

Resources
---------

* [Documentation](https://twitch-dl.bezdomni.net/)
* [Source code](https://github.com/ihabunek/twitch-dl)
* [Issues](https://github.com/ihabunek/twitch-dl/issues)
* [Python package](https://pypi.org/project/twitch-dl/)

Requirements
------------

* Python 3.8 or later
* [ffmpeg](https://ffmpeg.org/download.html), installed and on the system path

Quick start
-----------

See [installation instructions](https://twitch-dl.bezdomni.net/installation.html)
to set up twitch-dl.

List videos from a channel.

```
twitch-dl videos bananasaurus_rex
```

List clips from a channel.

```
twitch-dl clips bananasaurus_rex
```

Download a video by URL.

```
twitch-dl download https://www.twitch.tv/videos/1418494769
```

or by ID

```
twitch-dl download 1418494769
```

Download a clip by URL

```
twitch-dl download https://www.twitch.tv/bananasaurus_rex/clip/PlacidColdClipsdadDeIlluminati-hL2s_aLE4CHvVN4J
```

or by slug

```
twitch-dl download PlacidColdClipsdadDeIlluminati-hL2s_aLE4CHvVN4J
```

For more info see [the documentation](https://twitch-dl.bezdomni.net/usage.html).

License
-------

Copyright 2018-2022 Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html

Useful links for dev
--------------------

* https://supersonichub1.github.io/twitch-graphql-api/index.html
* https://github.com/SuperSonicHub1/twitch-graphql-api
