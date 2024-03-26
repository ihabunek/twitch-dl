<!-- ------------------- generated docs start ------------------- -->
# twitch-dl videos

List or download clips for given CHANNEL_NAME.

### USAGE

```
twitch-dl videos [OPTIONS] CHANNEL_NAME
```

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-a, --all</td>
    <td>Fetch all clips, overrides --limit</td>
</tr>

<tr>
    <td class="code">-c, --compact</td>
    <td>Show videos in compact mode, one line per video</td>
</tr>

<tr>
    <td class="code">-l, --limit INTEGER</td>
    <td>Number of videos to fetch. Defaults to 40 in compact mode, 10 otherwise.</td>
</tr>

<tr>
    <td class="code">-p, --pager INTEGER</td>
    <td>Number of videos to show per page. Disabled by default.</td>
</tr>

<tr>
    <td class="code">-g, --game TEXT</td>
    <td>Show videos of given game (can be given multiple times)</td>
</tr>

<tr>
    <td class="code">-s, --sort TEXT</td>
    <td>Sorting order of videos Possible values: <code>views</code>, <code>time</code>. [default: <code>time</code>]</td>
</tr>

<tr>
    <td class="code">-t, --type TEXT</td>
    <td>Broadcast type Possible values: <code>archive</code>, <code>highlight</code>, <code>upload</code>. [default: <code>archive</code>]</td>
</tr>

<tr>
    <td class="code">--json</td>
    <td>Print data as JSON rather than human readable text</td>
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