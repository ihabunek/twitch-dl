# Advanced

## Temporary files

By default, twitch-dl will download VODs to your systems temp dir (e.g. `/tmp/`
on Linux). To change the location where the files are downloaded you can set
the `TMP` environment variable, e.g.

```
TMP=/my/tmp/path/ twitch-dl download 221837124
```
