<!-- ------------------- generated docs start ------------------- -->
# twitch-dl chat

Render chat for a given video.

This command is experimental and may change in the future!

### USAGE

```
twitch-dl chat [OPTIONS] ID
```

### OPTIONS

<table>
<tbody>
<tr>
    <td class="code">-w, --width INTEGER</td>
    <td>Chat width in pixels [default: <code>400</code>]</td>
</tr>

<tr>
    <td class="code">-h, --height INTEGER</td>
    <td>Chat height in pixels [default: <code>1024</code>]</td>
</tr>

<tr>
    <td class="code">--font-size INTEGER</td>
    <td>Font size [default: <code>20</code>]</td>
</tr>

<tr>
    <td class="code">--dark</td>
    <td>Dark mode</td>
</tr>

<tr>
    <td class="code">--pad-x INTEGER</td>
    <td>Horizontal padding [default: <code>5</code>]</td>
</tr>

<tr>
    <td class="code">--pad-y INTEGER</td>
    <td>Vertical padding [default: <code>5</code>]</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

<h2>Rendering video with chat</h2>

Here's an example how you can join a twitch stream with its chat in a single video.

First download the video in the desired quality:

```sh
twitch-dl download -q 1080p 2237172069 -o video.mp4
```

Render the chat with the same height as the downloaded video:

```sh
twitch-dl chat --dark --width 500 --height 1080 2237172069 -o chat.mp4
```

Stitch them togheter using ffmpeg:

```
ffmpeg -i video.mp4 -i chat.mp4 -filter_complex hstack=inputs=2 chat_with_video.mp4
```