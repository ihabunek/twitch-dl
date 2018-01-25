Twitch Downloader
=================

A simple CLI tool for downloading videos from Twitch.

Usage
-----

List recent streams for a given channel:

```
λ twitch-dl videos bananasaurus_rex
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

Download a stream by ID:

```
twitch-dl download 221837124
```

License
-------

Copyright 2018 Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html
