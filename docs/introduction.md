twitch-dl
=========

Command-line tool for downloading videos from twitch.tv

Inspired by [youtube-dl](https://youtube-dl.org/). Adds twitch-specific features
and uses concurrent connections to make the download faster.

## Resources

* [Documentation](https://twitch-dl.bezdomni.net/)
* [Source code on Github](https://github.com/ihabunek/twitch-dl)
* [Issues on Github](https://github.com/ihabunek/twitch-dl/issues)
* [Python package](https://pypi.org/project/twitch-dl/)

## Quick start

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

For more info and examples see [usage](usage.html).

## License

twitch-dl is open source and licensed under the [GNU General Public License v3](/license.html).
