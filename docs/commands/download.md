<!-- ------------------- generated docs start ------------------- -->
# twitch-dl download

Download videos or clips.

### USAGE

```
twitch-dl download <videos> [FLAGS] [OPTIONS]
```

### ARGUMENTS

<table>
<tbody>
<tr>
    <td class="code">&lt;videos&gt;</td>
    <td>One or more video ID, clip slug or twitch URL to download.</td>
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
    <td class="code">--skipall</td>
    <td>Skip the current file if it already exists without prompting.</td>
</tr>

<tr>
    <td class="code">--overwrite</td>
    <td>Overwrite the target file if it already exists without prompting.</td>
</tr>

<tr>
    <td class="code">-x, --all</td>
    <td>Download all videos on the channel. Overrides all other arguments. Pass in the channel name as the &#x27;videos&#x27; argument.</td>
</tr>

<tr>
    <td class="code">-y, --skip-latest</td>
    <td>Skip downloading the latest video. Only makes sense with the --all flag.</td>
</tr>
</tbody>
</table>

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-w, --max-workers</td>
    <td>Number of workers for downloading vods concurrently (default 5)</td>
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
    <td>Video quality, e.g. 720p30 or 720p60. Set to &#x27;source&#x27; to get best quality.</td>
</tr>

<tr>
    <td class="code">-a, --auth-token</td>
    <td>Authentication token, passed to Twitch to access subscriber only VODs. Can be copied from the &#x27;auth_token&#x27; cookie in any browser logged in on Twitch.</td>
</tr>

<tr>
    <td class="code">-o, --output</td>
    <td>Output file name template. See docs for details.</td>
</tr>

<tr>
    <td class="code">-r, --rate-limit</td>
    <td>Limit the maximum download speed in bytes per second. Use &#x27;k&#x27; and &#x27;m&#x27; suffixes for kbps and mbps.</td>
</tr>

<tr>
    <td class="code">-c, --chapter</td>
    <td>Download a single chapter of the video. Specify the chapter number or use the flag without a number to display a chapter select prompt.</td>
</tr>

<tr>
    <td class="code">-t, --tempdir</td>
    <td>Override the temp dir path.</td>
</tr>

<tr>
    <td class="code">-d, --output-dir</td>
    <td>Customize location of the output directory. Defaults to the current directory.</td>
</tr>

<tr>
    <td class="code">-u, --execute-after</td>
    <td>Run a CLI command after each file is downloaded and processed. In your command, use ^p for the absolute path to the file that was downloaded, and ^f for just the file name.</td>
</tr>

<tr>
    <td class="code">-z, --execute-before</td>
    <td>Run a CLI command before each file is downloaded. Return an exit code of 0 to indicate you want to download the file, or nonzero to indicate you want to skip the file. In your command, use ^p for the absolute path to the file that was downloaded, and ^f for just the file name.</td>
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

Download multiple videos one after the other:

```
twitch-dl download 1559928295 1557034274 1555157293 -q source
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


### Downloading subscriber-only VODs

To download sub-only VODs, you need to find your auth token. It can be found
using your browser, in a cookie named `auth_token`.

1. Open twitch.tv in your browser and make sure you're logged in.
2. Open developer tools (F12 shortcut in Firefox and Chrome).
3. Open the `Storage` tab on Firefox, or `Application` tab in Chrome.
4. Click on `Cookies` → `https://www.twitch.tv/` in the sidebar.
5. Find the `auth-token` cookie in the list and copy it's value.

![How to find the auth token in dev tools](./auth_token.png)

The auth token will be a 30 character long string of random letters and numbers,
something like `iduetx4i107rn4b9wrgctf590aiktv`. Then you can pass this to the
download command:

```
twitch-dl download 221837124 --auth-token iduetx4i107rn4b9wrgctf590aiktv
```