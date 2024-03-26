<!-- ------------------- generated docs start ------------------- -->
# twitch-dl info

Print information for a given Twitch URL, video ID or clip slug.

### USAGE

```
twitch-dl info [OPTIONS] ID
```

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">--json</td>
    <td>Print data as JSON rather than human readable text</td>
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