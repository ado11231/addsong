<h3 align="center">addsong</h3>

<p align="center">
  <img src="assets/demo.gif" alt="addsong demo" width="600">
</p>

<p align="center"><b>Paste a link, and the song shows up in Apple Music automatically.</b></p>

`addsong` takes a song name or a YouTube link. It downloads the track, adds the
**title, artist, and cover art**, and drops it into Apple Music. No dragging
files around — making downloading unofficial music seamless.

```bash
addsong "songname"
addsong "https://www.youtube.com/watch?v=..."
```

## Installation

`addsong` is a Python package — install it with `pipx` (recommended) or `pip`.
You also need two external binaries, **`yt-dlp`** and **`ffmpeg`**, on your PATH.

### 1. Install addsong

```bash
pipx install addsong
```

If you don't have `pipx`, install it first: macOS `brew install pipx`,
Linux `pip install --user pipx` (or your distro's package), Windows
`pip install pipx`. No `pipx`? `pip install --user addsong` works too — just
make sure your user `bin` directory is on PATH.

### 2. Install yt-dlp and ffmpeg

These do the actual downloading and tagging. Pick one per OS:

&nbsp;<img src="assets/macos.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> **macOS**

```bash
brew install yt-dlp ffmpeg
```

&nbsp;<img src="assets/linux.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> **Linux / WSL**

```bash
sudo apt-get install -y ffmpeg && pipx install yt-dlp
# (or your distro's package manager; yt-dlp can also come from pipx/pip)
```

&nbsp;<img src="assets/windows.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> **Windows** (PowerShell)

```powershell
winget install yt-dlp.yt-dlp Gyan.FFmpeg
```

### 3. Check it

```bash
addsong --version
```

> **No wheels for your platform?** `addsong` is pure Python, so `pipx install
> addsong` works on any OS with Python 3.11+. The external binaries (`yt-dlp`,
> `ffmpeg`) are the only platform-specific bits.

## Updating

```bash
pipx upgrade addsong
# or, with pip:
python -m pip install --user --upgrade addsong
```

## Shell Completions

Generate tab-completion for your shell and source it (or save it to your shell's
completion directory):

```bash
source <(addsong --print-completion bash)      # bash
addsong --print-completion zsh  > ~/.zsh/completions/_addsong   # zsh
addsong --print-completion fish > ~/.config/fish/completions/addsong.fish  # fish
```

Run `addsong --help` to confirm the flag, and see your shell's docs for where to
drop completion files.

## Your First Song

```bash
addsong "songname"
```

`addsong` shows what it found so you can fix mistakes before it saves:

```
  Review track ♪
  Artist: Artist Name
  Title:  Song Title

  [Enter] Add  ·  [E] Edit  ·  [S] Skip
  ❯
```

Press **Enter** and the song lands in Apple Music a second later.

## Commands


| Command                        | What it does                                    |
| ------------------------------ | ----------------------------------------------- |
| `addsong "name"`               | Add the top search result                       |
| `addsong "<link>"`             | Add a specific video                            |
| `addsong --results 3 "name"`   | Add the top 3 search results                    |
| `addsong --playlist "<link>"`  | Add a whole playlist                            |
| `addsong --from list.txt`      | Add every link in a file                        |
| `addsong subscribe "<link>"`   | Follow a playlist                               |
| `addsong sync`                 | Add new songs from playlists you follow         |
| `addsong list`                 | Show playlists you follow                       |
| `addsong unsubscribe "<link>"` | Stop following a playlist                       |
| `addsong forget`               | Forget everything added (so it can be re-added) |



## Flags


| Flag                    | What it does                                           |
| ----------------------- | ------------------------------------------------------ |
| `-y`                    | Don't ask, just add it                                 |
| `--review`              | Always pause to fix the title/artist first             |
| `--reimport`            | Add a song again even if you already have it           |
| `--dry-run`             | Show what would happen, without downloading            |
| `--format FMT`          | Output format: `m4a` (default), `mp3`, `flac`, `opus`… |
| `--quality N`           | Audio quality `0`-`10` (`0` = best, the default)       |
| `--notify`              | Pop a desktop notification as each song imports        |
| `--quiet` / `--verbose` | Show less / more output                                |
| `--help`                | Full list of commands and options                      |


Set environment variables like `ADDSONG_WATCH_DIR` for permanent defaults.

Run `addsong --help` for the full list.

## Download Location

On macOS and Windows they go straight into Apple Music; on Linux they land in
`~/Music/addsong/`. Point them elsewhere with `ADDSONG_WATCH_DIR=/your/folder`.

## Common Errors

- `command not found` — reopen your terminal so your PATH picks up the new install; if it persists, run `pipx ensurepath` and reopen, or check the [Installation](#installation) step.
- **Nothing shows up** — open the Apple Music app and keep it open while adding (macOS/Windows).
- **A download failed** — update `yt-dlp`, then retry with `--verbose` to see why.