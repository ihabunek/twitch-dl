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
    <td>Chat height in pixels [default: <code>1080</code>]</td>
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

<tr>
    <td class="code">-o, --output TEXT</td>
    <td>Output file name template. See docs for details. [default: <code>chat_{id}.{format}</code>]</td>
</tr>

<tr>
    <td class="code">-f, --format TEXT</td>
    <td>Video format to convert into, passed to ffmpeg as the target file extension. [default: <code>mp4</code>]</td>
</tr>

<tr>
    <td class="code">--overwrite</td>
    <td>Overwrite the target file if it already exists without prompting.</td>
</tr>

<tr>
    <td class="code">--json</td>
    <td>Print data as JSON rather than human readable text</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

<h2>Experimental command</h2>

Chat command is still experimental and things may change.

This command requires twitch-dl to be installed with optional "chat" dependencies:

```sh
pipx install "twitch-dl[chat]"
```

It is not available if twitch-dl is used from the `pyz` archive.

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