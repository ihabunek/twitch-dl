<!-- ------------------- generated docs start ------------------- -->
# twitch-dl info

Print information for a given Twitch URL, video ID or clip slug.

### USAGE

```
twitch-dl info <video> [FLAGS]
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
    <td class="code">-j, --json</td>
    <td>Show results as JSON</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

### Examples


Print info about a video:

```
twitch-dl info 863849735
```

Print info about a clip:

```
twitch-dl info BusyBlushingCattleItsBoshyTime
```

Print JSON encoded info:

```
twitch-dl info BusyBlushingCattleItsBoshyTime --json
```