Twitch Downloader
=================

A simple CLI tool for downloading videos from Twitch.

Inspired by youtube-dl but improves upon it by using multiple concurrent
connections to make the download faster.

Resources
---------

* Homepage: https://github.com/ihabunek/twitch-dl
* Issues: https://github.com/ihabunek/twitch-dl/issues
* Python package: https://pypi.org/project/twitch-dl/

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

Download a stream by ID or URL:

```
twitch-dl download 221837124
twitch-dl download https://www.twitch.tv/videos/221837124
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

Copyright 2018 Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html
