<!-- ------------------- generated docs start ------------------- -->
# twitch-dl videos

List videos for a channel.

### USAGE

```
twitch-dl videos <channel_name> [FLAGS] [OPTIONS]
```

### ARGUMENTS

<table>
<tbody>
<tr>
    <td class="code">&lt;channel_name&gt;</td>
    <td>Name of the channel to list videos for.</td>
</tr>
</tbody>
</table>

### FLAGS

<table>
<tbody>
<tr>
    <td class="code">-a, --all</td>
    <td>Fetch all videos, overrides --limit</td>
</tr>

<tr>
    <td class="code">-j, --json</td>
    <td>Show results as JSON. Ignores <code>--pager</code>.</td>
</tr>

<tr>
    <td class="code">-c, --compact</td>
    <td>Show videos in compact mode, one line per video</td>
</tr>
</tbody>
</table>

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-g, --game</td>
    <td>Show videos of given game (can be given multiple times)</td>
</tr>

<tr>
    <td class="code">-l, --limit</td>
    <td>Number of videos to fetch. Defaults to 10.</td>
</tr>

<tr>
    <td class="code">-s, --sort</td>
    <td>Sorting order of videos. Defaults to <code>time</code>. Possible values: <code>views</code>, <code>time</code>.</td>
</tr>

<tr>
    <td class="code">-t, --type</td>
    <td>Broadcast type. Defaults to <code>archive</code>. Possible values: <code>archive</code>, <code>highlight</code>, <code>upload</code>.</td>
</tr>

<tr>
    <td class="code">-p, --pager</td>
    <td>Print videos in pages. Ignores <code>--limit</code>. Defaults to 10.</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

### Examples

List recent channel videos (10 by default):

```
twitch-dl videos bananasaurus_rex
```

Limit to videos of one or more games:

```
twitch-dl videos --game "doom eternal" --game "cave story" bananasaurus_rex
```

List all channel videos at once:

```
twitch-dl videos bananasaurus_rex --all
```

List all channel videos in pages of 10:

```
twitch-dl videos bananasaurus_rex --pager
```

Page size can be adjusted by passing number of items per page:

```
twitch-dl videos bananasaurus_rex --pager 5
```

Returns all videos as a JSON list. Useful for scripting.

```
twitch-dl videos bananasaurus_rex --json --all
```