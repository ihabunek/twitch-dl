twitch-dl(1)

# NAME

twitch-dl - download twitch.tv videos quickly

# SYNOPSYS

twitch-dl videos   [options] [channel\_name]

twitch-dl download [options] [video\_id]

# DESCRIPTION

twitch-dl is a command-line tool for downloading videos from Twitch (twitch.tv).
It uses multiple workers to download VODs in paralel which makes it considerably
faster than tools which download them one at the time, such as youtube-dl.

# EXAMPLES

List recent videos from bananasaurus\_rex's channel:

```
twitch-dl videos bananasaurus_rex
```

Download video by URL:

```
twitch-dl download https://www.twitch.tv/videos/377220226
```

Download video by ID:

```
twitch-dl download 377220226
```

Specify output format:

```
twitch-dl download --format=avi 377220226
```

Partial download by setting start and end time (hh:mm or hh:mm:ss):

```
twitch-dl download --start=00:10 --end=02:15 377220226
```

Download clip by URL:

```
twitch-dl download https://www.twitch.tv/bananasaurus_rex/clip/VenomousTameWormHumbleLife
```

Download clip by slug:

```
twitch-dl download VenomousTameWormHumbleLife
```

Note that clips are a single download, and don't benefit from the paralelism
used when downloading videos.

# SEE ALSO

youtube-dl(1)

# COPYRIGHT

Copyright Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html
