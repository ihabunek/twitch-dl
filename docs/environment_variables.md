# Environment variables

> Introduced in twitch-dl 2.2.0

twitch-dl allows setting defaults for parameters via environment variables.

Environment variables should be named `TWITCH_DL_<COMMAND_NAME>_<OPTION_NAME>`.

For example, when invoking `twitch-dl download`, if you always set `--quality
source` you can set the following environment variable to make this the
default:

```
TWITCH_DL_DOWNLOAD_QUALITY="source"
```
