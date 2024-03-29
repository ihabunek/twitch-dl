# Shell completion

> Introduced in twitch-dl 2.2.0

twitch-dl uses [Click shell completion](https://click.palletsprojects.com/en/8.1.x/shell-completion/) which works on Bash, Fish and Zsh.

To enable completion, twitch-dl must be [installed](./installation.html) as a command and available by ivoking `twitch-dl`. Then follow the instructions for your shell.

**Bash**

Add to `~/.bashrc`:

```
eval "$(_TWITCH_DL_COMPLETE=bash_source twitch-dl)"
```

**Fish**

Add to `~/.config/fish/completions/twitch-dl.fish`:

```
_TWITCH_DL_COMPLETE=fish_source twitch-dl | source
```

**Zsh**

Add to `~/.zshrc`:

```
eval "$(_TWITCH_DL_COMPLETE=zsh_source twitch-dl)"
```
