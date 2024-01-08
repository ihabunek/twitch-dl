# Advanced

## Temporary files

By default, twitch-dl will download VODs to your systems temp dir (e.g. `/tmp/`
on Linux). To change the location where the files are downloaded you can set
the `TMP` environment variable, e.g.

```
TMP=/my/tmp/path/ twitch-dl download 221837124
```

You can also specify the `--tempdir` argument to the `download` command without having to modify your environment variables. For example:

```
twitch-dl download 221837124 --tempdir /my/tmp/path/
```