<!-- ------------------- generated docs start ------------------- -->
# twitch-dl chat video

Render twitch chat as video

### Additional dependencies

This command requires twitch-dl to be installed with optional "chat" dependencies:

    pipx install "twitch-dl[chat]"

It is not available if twitch-dl is used from the `pyz` archive.

### USAGE

```
twitch-dl chat video [OPTIONS] ID
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
    <td>Output file name template. See docs for details. [default: <code>chat_{id}_{title_slug}.{format}</code>]</td>
</tr>

<tr>
    <td class="code">-f, --format TEXT</td>
    <td>Video format to convert into, passed to ffmpeg as the target file extension. [default: <code>mp4</code>]</td>
</tr>

<tr>
    <td class="code">-i, --image-format TEXT</td>
    <td>Image format used to render individual frames, bmp (default) is fast but consumes a lot of space. You can switch to png to conserve space at cost of speed. [default: <code>bmp</code>]</td>
</tr>

<tr>
    <td class="code">--overwrite</td>
    <td>Overwrite the target file if it already exists without prompting.</td>
</tr>

<tr>
    <td class="code">-k, --keep</td>
    <td>Don&#x27;t delete the generated intermediate frame images.</td>
</tr>

<tr>
    <td class="code">--no-join</td>
    <td>Don&#x27;t run ffmpeg to join the generated frames, implies --keep.</td>
</tr>
</tbody>
</table>

<!-- ------------------- generated docs end ------------------- -->

## Example

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