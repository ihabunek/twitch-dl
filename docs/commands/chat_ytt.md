<!-- ------------------- generated docs start ------------------- -->
# twitch-dl chat ytt

Render twitch chat as youtube subtitles

If you upload your Twitch VOD to YouTube, you can use this command to
generate a ytt file which can be uploaded alongside the YouTube video to
show the chat in subtitles.

### USAGE

```
twitch-dl chat ytt [OPTIONS] ID
```

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-f, --foreground TEXT</td>
    <td>Foreground color in #RRGGBBAA format [default: <code>#FEFEFEFE</code>]</td>
</tr>

<tr>
    <td class="code">-b, --background TEXT</td>
    <td>Background color in #RRGGBBAA format [default: <code>#FEFEFE00</code>]</td>
</tr>

<tr>
    <td class="code">--text-edge-color TEXT</td>
    <td>Text edge color in #RRGGBB format [default: <code>#000000</code>]</td>
</tr>

<tr>
    <td class="code">--text-edge-type TEXT</td>
    <td>Text edge type Possible values: <code>HardShadow</code>, <code>Bevel</code>, <code>GlowOutline</code>, <code>SoftShadow</code>. [default: <code>SoftShadow</code>]</td>
</tr>

<tr>
    <td class="code">--text-align TEXT</td>
    <td>Text alignemnt Possible values: <code>Left</code>, <code>Right</code>, <code>Center</code>. [default: <code>Left</code>]</td>
</tr>

<tr>
    <td class="code">--font-style TEXT</td>
    <td>Font style Possible values: <code>Default</code>, <code>MonospacedSerif</code>, <code>ProportionalSerif</code>, <code>MonospacedSansSerif</code>, <code>ProportionalSansSerif</code>, <code>Casual</code>, <code>Cursive</code>, <code>SmallCapitals</code>. [default: <code>MonospacedSansSerif</code>]</td>
</tr>

<tr>
    <td class="code">--font-size INTEGER</td>
    <td>Font size, values 0 - 300 are equivalent to relative 75% - 150% font size</td>
</tr>

<tr>
    <td class="code">-x, --horizontal-offset INTEGER</td>
    <td>Position of subtitles, distance from left edge [default: <code>70</code>]</td>
</tr>

<tr>
    <td class="code">-y, --vertical-offset INTEGER</td>
    <td>Position of subtitles, distance from top edge</td>
</tr>

<tr>
    <td class="code">--line-count INTEGER</td>
    <td>Number of lines to render [default: <code>13</code>]</td>
</tr>

<tr>
    <td class="code">--line-chars INTEGER</td>
    <td>Max. number of characters per line [default: <code>25</code>]</td>
</tr>

<tr>
    <td class="code">-o, --output TEXT</td>
    <td>Output file name template. See docs for details. [default: <code>chat_{id}_{title_slug}.{format}</code>]</td>
</tr>

<tr>
    <td class="code">--overwrite</td>
    <td>Overwrite the target file if it already exists without prompting.</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

