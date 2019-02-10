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

Download by URL:

```
twitch-dl download https://www.twitch.tv/videos/377220226
```

Download by ID:

```
twitch-dl download 377220226
```

# SEE ALSO

youtube-dl(1)

# COPYRIGHT

Copyright Ivan Habunek <ivan@habunek.com>

Licensed under the GPLv3: http://www.gnu.org/licenses/gpl-3.0.html
