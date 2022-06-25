<!-- ------------------- generated docs start ------------------- -->
# twitch-dl download

Download a video or clip.

### USAGE

```
twitch-dl download <video> [FLAGS] [OPTIONS]
```

### ARGUMENTS

<table>
<tbody>
<tr>
    <td class="code">&lt;video&gt;</td>
    <td>Video ID, clip slug, or URL</td>
</tr>
</tbody>
</table>

### FLAGS

<table>
<tbody>
<tr>
    <td class="code">-k, --keep</td>
    <td>Don&#x27;t delete downloaded VODs and playlists after merging.</td>
</tr>

<tr>
    <td class="code">--no-join</td>
    <td>Don&#x27;t run ffmpeg to join the downloaded vods, implies --keep.</td>
</tr>

<tr>
    <td class="code">--overwrite</td>
    <td>Overwrite the target file if it already exists without prompting.</td>
</tr>
</tbody>
</table>

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-w, --max-workers</td>
    <td>Maximal number of threads for downloading vods concurrently (default 20)</td>
</tr>

<tr>
    <td class="code">-s, --start</td>
    <td>Download video from this time (hh:mm or hh:mm:ss)</td>
</tr>

<tr>
    <td class="code">-e, --end</td>
    <td>Download video up to this time (hh:mm or hh:mm:ss)</td>
</tr>

<tr>
    <td class="code">-f, --format</td>
    <td>Video format to convert into, passed to ffmpeg as the target file extension. Defaults to <code>mkv</code>.</td>
</tr>

<tr>
    <td class="code">-q, --quality</td>
    <td>Video quality, e.g. 720p. Set to &#x27;source&#x27; to get best quality.</td>
</tr>

<tr>
    <td class="code">-a, --auth</td>
    <td>Twitch authentication token needed for subscriber-only VODs. Can be found in the 'auth_token' cookie.</td>
</tr>

<tr>
    <td class="code">-o, --output</td>
    <td>Output file name template. See docs for details.</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

### Examples

Download a video by ID or URL:

```
twitch-dl download 221837124
twitch-dl download https://www.twitch.tv/videos/221837124
```

Specify video quality to download to prevent a prompt:

```
twitch-dl download -q 720p 221837124
```

Setting quality to `source` will download the best available quality:

```
twitch-dl download -q source 221837124
```

Setting quality to `audio_only` will download only audio:

```
twitch-dl download -q audio_only 221837124
```

### Overriding the target file name

The target filename can be defined by passing the `--output` option followed by
the desired file name, e.g. `--output strim.mkv`.

The filename uses
[Python format string syntax](https://docs.python.org/3/library/string.html#format-string-syntax)
and may contain placeholders in curly braces which will be replaced with
relevant information tied to the downloaded video, e.g. `--output "{date}_{id}.{format}"`.

The supported placeholders are:

| Placeholder       | Description                    | Sample                        |
| ----------------- | ------------------------------ | ------------------------------ |
| `{id}`            | Video ID                       | 1255522958                     |
| `{title}`         | Video title                    | Dark Souls 3 First playthrough |
| `{title_slug}`    | Slugified video title          | dark_souls_3_first_playthrough |
| `{datetime}`      | Video date and time            | 2022-01-07T04:00:27Z           |
| `{date}`          | Video date                     | 2022-01-07                     |
| `{time}`          | Video time                     | 04:00:27Z                      |
| `{channel}`       | Channel name                   | KatLink                        |
| `{channel_login}` | Channel login                  | katlink                        |
| `{format}`        | File extension, see `--format` | mkv                            |
| `{game}`          | Game name                      | Dark Souls III                 |
| `{game_slug}`     | Slugified game name            | dark_souls_iii                 |
| `{slug}`          | Clip slug (clips only)         | AbrasivePlacidCatDxAbomb       |

A couple of examples:

|    |    |
| -- | -- |
| Pattern | `{date}_{id}_{channel_login}_{title_slug}.{format}` *(default)* |
| Expands to | `2022-01-07_1255522958_katlink_dark_souls_3_first_playthrough.mkv` |

<br />

|    |    |
| -- | -- |
| Pattern | `{channel} - {game} - {title}.{format}` |
| Expands to | `KatLink - Dark Souls III - Dark Souls 3 First playthrough.mkv` |