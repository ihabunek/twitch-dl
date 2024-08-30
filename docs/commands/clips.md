<!-- ------------------- generated docs start ------------------- -->
# twitch-dl clips

List or download clips for given CHANNEL_NAME.

### USAGE

```
twitch-dl clips [OPTIONS] CHANNEL_NAME
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
    <td>Show clips in compact mode, one line per video</td>
</tr>

<tr>
    <td class="code">-d, --download</td>
    <td>Download clips in given period (in source quality)</td>
</tr>

<tr>
    <td class="code">-l, --limit INTEGER</td>
    <td>Number of clips to fetch. Defaults to 40 in compact mode, 10 otherwise.</td>
</tr>

<tr>
    <td class="code">-p, --pager INTEGER</td>
    <td>Number of clips to show per page. Disabled by default.</td>
</tr>

<tr>
    <td class="code">-P, --period TEXT</td>
    <td>Period from which to return clips Possible values: <code>last_day</code>, <code>last_week</code>, <code>last_month</code>, <code>all_time</code>. [default: <code>all_time</code>]</td>
</tr>

<tr>
    <td class="code">-t, --target-dir</td>
    <td>Target directory when downloading clips [default: <code>.</code>]</td>
</tr>

<tr>
    <td class="code">--json</td>
    <td>Print data as JSON rather than human readable text</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

## Listing clips

By default returns top 10 clips of all time.

```
twitch-dl clips bananasaurus_rex
```

Increase the number of clips returned.

```
twitch-dl clips bananasaurus_rex --limit 50
```

Return all clips, may require multiple requests, see notes.

```
twitch-dl clips bananasaurus_rex --all
```

Return clips from past day/week/month by changing the period:

```
twitch-dl clips bananasaurus_rex --period past_week
```

List all clips, 10 clips at the time:

```
twitch-dl clips bananasaurus_rex --pager
```

Print clips data in JSON. Useful for scripting.

```
twitch-dl clips bananasaurus_rex --json
```

Download all clips of the past week, won't overwrite exisitng ones:

```
twitch-dl clips bananasaurus_rex --download --period last_week
```

## Notes

Clips are fetched in batches no larger than 100. When requesting more than 100
clips, it takes more than one request so it can take a little time. You can see
individual requests by passing the `--debug` flag.

Currently it doesn't seem to be possible to get a list of clips ordered by time
of creation, only by view count. Clips with the same view count seem to be
returned in random order. This can break paging resulting in duplicate clips
listed or clips missed.